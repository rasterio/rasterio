"""Tests for :py:class:`rasterio.warp.WarpedVRT`."""


from __future__ import division
import logging

import affine
import boto3
import numpy
import pytest

from .conftest import requires_gdal21, requires_gdal2
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling, MaskFlags, ColorInterp
from rasterio.errors import RasterioDeprecationWarning
from rasterio import shutil as rio_shutil
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from rasterio.windows import Window


# Custom markers.
credentials = pytest.mark.skipif(
    not (boto3.Session()._session.get_credentials()),
    reason="S3 raster access requires credentials",
)

DST_CRS = "EPSG:3857"


def _copy_update_profile(path_in, path_out, **kwargs):
    """Create a copy of path_in in path_out updating profile with **kwargs"""
    with rasterio.open(str(path_in)) as src:
        profile = src.profile.copy()
        profile.update(kwargs)
        with rasterio.open(str(path_out), "w", **profile) as dst:
            dst.write(src.read())
    return str(path_out)


def test_deprecated_param(path_rgb_byte_tif):
    """dst_crs is deprecated"""
    with rasterio.open(path_rgb_byte_tif) as src:
        with pytest.warns(RasterioDeprecationWarning):
            vrt = WarpedVRT(src, dst_crs=DST_CRS)
            assert vrt.dst_crs == CRS.from_string(DST_CRS)


def test_warped_vrt(path_rgb_byte_tif):
    """A VirtualVRT has the expected VRT properties."""
    with rasterio.open(path_rgb_byte_tif) as src:
        vrt = WarpedVRT(src, crs=DST_CRS)
        assert vrt.dst_crs == CRS.from_string(DST_CRS)
        assert vrt.src_nodata == 0.0
        assert vrt.dst_nodata == 0.0
        assert vrt.tolerance == 0.125
        assert vrt.resampling == Resampling.nearest
        assert vrt.warp_extras == {"init_dest": "NO_DATA"}
        assert vrt.mask_flag_enums == ([MaskFlags.nodata],) * 3


@requires_gdal21(reason="Nodata deletion requires GDAL 2.1+")
def test_warped_vrt_dst_alpha(path_rgb_byte_tif):
    """A VirtualVRT has the expected VRT properties."""
    with rasterio.open(path_rgb_byte_tif) as src:
        vrt = WarpedVRT(src, crs=DST_CRS, add_alpha=True)
        assert vrt.dst_crs == CRS.from_string(DST_CRS)
        assert vrt.src_nodata == 0.0
        assert vrt.dst_nodata is None
        assert vrt.tolerance == 0.125
        assert vrt.resampling == Resampling.nearest
        assert vrt.warp_extras == {"init_dest": "NO_DATA"}
        assert vrt.count == 4
        assert vrt.mask_flag_enums == (
            [MaskFlags.per_dataset, MaskFlags.alpha],
        ) * 3 + (
            [MaskFlags.all_valid],
        )


@requires_gdal21(reason="Nodata deletion requires GDAL 2.1+")
def test_warped_vrt_msk_default(path_rgb_msk_byte_tif):
    """Add an alpha band to the VRT to access per-dataset mask of a source"""
    with rasterio.open(path_rgb_msk_byte_tif) as src:
        vrt = WarpedVRT(src, crs=DST_CRS, add_alpha=True)
        assert vrt.src_nodata is None
        assert vrt.dst_nodata is None
        assert vrt.count == 4
        assert vrt.mask_flag_enums == (
            [MaskFlags.per_dataset, MaskFlags.alpha],
        ) * 3 + (
            [MaskFlags.all_valid],
        )


@requires_gdal21(reason="Nodata deletion requires GDAL 2.1+")
def test_warped_vrt_msk_nodata(path_rgb_msk_byte_tif):
    """Specifying dst nodata also works for source with .msk"""
    with rasterio.open(path_rgb_msk_byte_tif) as src:
        vrt = WarpedVRT(src, crs=DST_CRS, nodata=0.0)
        assert vrt.dst_crs == CRS.from_string(DST_CRS)
        assert vrt.src_nodata is None
        assert vrt.dst_nodata == 0.0
        assert vrt.count == 3
        assert vrt.mask_flag_enums == ([MaskFlags.nodata],) * 3


def test_warped_vrt_source(path_rgb_byte_tif):
    """A VirtualVRT has the expected source dataset."""
    with rasterio.open(path_rgb_byte_tif) as src:
        vrt = WarpedVRT(src, crs=DST_CRS)
        assert vrt.src_dataset == src


def test_warped_vrt_set_src_crs(path_rgb_byte_tif, tmpdir):
    """A VirtualVRT without CRS works only with parameter src_crs"""
    path_crs_unset = str(tmpdir.join("rgb_byte_crs_unset.tif"))
    _copy_update_profile(path_rgb_byte_tif, path_crs_unset, crs=None)
    with rasterio.open(path_rgb_byte_tif) as src:
        original_crs = src.crs
    with rasterio.open(path_crs_unset) as src:
        with pytest.raises(Exception):
            with WarpedVRT(src, crs=DST_CRS) as vrt:
                pass
        with WarpedVRT(src, src_crs=original_crs, crs=DST_CRS) as vrt:
            assert vrt.src_crs == original_crs


def test_wrap_file(path_rgb_byte_tif):
    """A VirtualVRT has the expected dataset properties."""
    with rasterio.open(path_rgb_byte_tif) as src:
        vrt = WarpedVRT(src, crs=DST_CRS)
        assert vrt.crs == CRS.from_string(DST_CRS)
        assert tuple(round(x, 1) for x in vrt.bounds) == (
            -8789636.7, 2700460.0, -8524406.4, 2943560.2
        )
        assert vrt.name.startswith("WarpedVRT(")
        assert vrt.name.endswith("tests/data/RGB.byte.tif)")
        assert vrt.indexes == (1, 2, 3)
        assert vrt.nodatavals == (0, 0, 0)
        assert vrt.dtypes == ("uint8", "uint8", "uint8")
        assert vrt.read().shape == (3, 736, 803)


def test_warped_vrt_dimensions(path_rgb_byte_tif):
    """
    A WarpedVRT with target dimensions has the expected dataset
    properties.
    """
    with rasterio.open(path_rgb_byte_tif) as src:
        extent = (-20037508.34, 20037508.34)
        size = (2 ** 16) * 256
        resolution = (extent[1] - extent[0]) / size
        dst_transform = affine.Affine(
            resolution, 0.0, extent[0], 0.0, -resolution, extent[1]
        )
        vrt = WarpedVRT(
            src, crs=DST_CRS, width=size, height=size, transform=dst_transform
        )
        assert vrt.dst_crs == CRS.from_string(DST_CRS)
        assert vrt.src_nodata == 0.0
        assert vrt.dst_nodata == 0.0
        assert vrt.resampling == Resampling.nearest
        assert vrt.width == size
        assert vrt.height == size
        assert vrt.transform == dst_transform
        assert vrt.warp_extras == {"init_dest": "NO_DATA"}


def test_warp_extras(path_rgb_byte_tif):
    """INIT_DEST warp extra is passed through."""
    with rasterio.open(path_rgb_byte_tif) as src:
        with WarpedVRT(src, crs=DST_CRS, init_dest=255) as vrt:
            rgb = vrt.read()
            assert (rgb[:, 0, 0] == 255).all()


@requires_gdal21(reason="S3 raster access requires GDAL 2.1+")
@credentials
@pytest.mark.network
def test_wrap_s3():
    """A warp wrapper's dataset has the expected properties"""
    L8TIF = "s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF"
    with rasterio.open(L8TIF) as src:
        with WarpedVRT(src, crs=DST_CRS, src_nodata=0, nodata=0) as vrt:
            assert vrt.crs == DST_CRS
            assert tuple(round(x, 1) for x in vrt.bounds) == (
                9556764.6, 2345109.3, 9804595.9, 2598509.1
            )
            assert vrt.name == "WarpedVRT(s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF)"
            assert vrt.indexes == (1,)
            assert vrt.nodatavals == (0,)
            assert vrt.dtypes == ("uint16",)
            assert vrt.shape == (7827, 7655)


def test_warped_vrt_nodata_read(path_rgb_byte_tif):
    """A read from a VirtualVRT respects dst_nodata."""
    with rasterio.open(path_rgb_byte_tif) as src:
        with WarpedVRT(src, crs=DST_CRS, src_nodata=0) as vrt:
            data = vrt.read(1, masked=True)
            assert data.mask.any()
            mask = vrt.dataset_mask()
            assert not mask.all()


@pytest.mark.parametrize("complex", (True, False))
def test_crs_should_be_set(path_rgb_byte_tif, tmpdir, complex):

    """When ``dst_height``, ``dst_width``, and ``dst_transform`` are set
    :py:class:`rasterio.warp.WarpedVRT` calls ``GDALCreateWarpedVRT()``,
    which requires the caller to then set a projection with
    ``GDALSetProjection()``.

    Permalink to ``GDALCreateWarpedVRT()`` call:

        https://github.com/mapbox/rasterio/blob/1f759e5f67628f163ea2550d8926b91545245712/rasterio/_warp.pyx#L753

    """

    vrt_path = str(tmpdir.join("test_crs_should_be_set.vrt"))

    with rasterio.open(path_rgb_byte_tif) as src:

        dst_crs = "EPSG:4326"
        dst_height = dst_width = 10
        dst_bounds = transform_bounds(src.crs, dst_crs, *src.bounds)

        # Destination transform
        left, bottom, right, top = dst_bounds
        xres = (right - left) / dst_width
        yres = (top - bottom) / dst_height
        dst_transform = affine.Affine(xres, 0.0, left, 0.0, -yres, top)

        # The 'complex' test case hits the affected code path
        vrt_options = {"dst_crs": dst_crs}
        if complex:
            vrt_options.update(
                dst_crs=dst_crs,
                dst_height=dst_height,
                dst_width=dst_width,
                dst_transform=dst_transform,
                resampling=Resampling.nearest,
            )

        with WarpedVRT(src, **vrt_options) as vrt:
            rio_shutil.copy(vrt, vrt_path, driver="VRT")
        with rasterio.open(vrt_path) as src:
            assert src.crs


def test_boundless_read_prohibited(path_rgb_byte_tif):
    """Boundless read of a VRT is prohibited"""
    with rasterio.open(path_rgb_byte_tif) as src, WarpedVRT(src) as vrt:
        with pytest.raises(ValueError):
            vrt.read(
                boundless=True,
                window=Window(-200, -200, 1000, 1000),
                out_shape=((3, 600, 600)),
            )


def test_boundless_masks_read_prohibited(path_rgb_byte_tif):
    """Boundless masks read of a VRT is prohibited"""
    with rasterio.open(path_rgb_byte_tif) as src, WarpedVRT(src) as vrt:
        with pytest.raises(ValueError):
            vrt.read_masks(
                boundless=True,
                window=Window(-200, -200, 1000, 1000),
                out_shape=((3, 600, 600)),
            )


def test_no_add_alpha_read(path_rgb_msk_byte_tif):
    """An alpha band is not added if add_alpha=False"""
    with rasterio.open(path_rgb_msk_byte_tif) as src, WarpedVRT(
        src, add_alpha=False
    ) as vrt:
        assert vrt.count == 3


def test_image(red_green):
    """Read a red image with black background"""
    with rasterio.Env():
        with rasterio.open(str(red_green.join("red.tif"))) as src, WarpedVRT(
            src,
            transform=affine.Affine.translation(-src.width / 4, src.height / 4) * src.transform,
            width=2 * src.width,
            height=2 * src.height
        ) as vrt:
            data = vrt.read()
            image = numpy.moveaxis(data, 0, -1)
            assert image[31, 31, 0] == 0
            assert image[32, 32, 0] == 204
            assert image[32, 32, 1] == 17


def test_image_nodata_mask(red_green):
    """Nodata of 0 masks out the black background"""
    with rasterio.Env():
        with rasterio.open(str(red_green.join("red.tif"))) as src, WarpedVRT(
            src,
            nodata=0,
            transform=affine.Affine.translation(-src.width / 2, src.height / 2) * src.transform,
            width=3 * src.width,
            height=3 * src.height
        ) as vrt:
            masks = vrt.read_masks()
            image = numpy.moveaxis(masks, 0, -1)
            assert image[63, 63, 0] == 0
            assert image[64, 64, 0] == 255


@requires_gdal2(reason="Warped VRT overviews require GDAL 2")
def test_hit_ovr(red_green):
    """Zoomed out read hits the overviews"""
    # GDAL doesn't log overview hits for local files , so we copy the
    # overviews of green.tif over the red overviews and expect to find
    # green pixels below.
    green_ovr = red_green.join("green.tif.ovr")
    green_ovr.rename(red_green.join("red.tif.ovr"))
    assert not green_ovr.exists()
    with rasterio.open(str(red_green.join("red.tif.ovr"))) as ovr:
        data = ovr.read()
        assert (data[1] == 204).all()

    with rasterio.open(str(red_green.join("red.tif"))) as src, WarpedVRT(src) as vrt:
        data = vrt.read(out_shape=(vrt.count, vrt.height // 2, vrt.width // 2))
        image = numpy.moveaxis(data, 0, -1)
        assert image[0, 0, 0] == 17
        assert image[0, 0, 1] == 204

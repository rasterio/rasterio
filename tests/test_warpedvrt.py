"""Tests for :py:class:`rasterio.warp.WarpedVRT`."""


from __future__ import division

import boto3
import pytest

import rasterio
from rasterio.enums import Resampling
from rasterio import shutil as rio_shutil
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds

from .conftest import requires_gdal21


# Custom markers.
credentials = pytest.mark.skipif(
    not(boto3.Session()._session.get_credentials()),
    reason="S3 raster access requires credentials")


def test_warped_vrt(path_rgb_byte_tif):
    """A VirtualVRT has the expected VRT properties."""
    with rasterio.open(path_rgb_byte_tif) as src:
        vrt = WarpedVRT(src, dst_crs='EPSG:3857')
        assert vrt.dst_crs == 'EPSG:3857'
        assert vrt.src_nodata == 0.0
        assert vrt.dst_nodata == 0.0
        assert vrt.tolerance == 0.125
        assert vrt.resampling == Resampling.nearest
        assert vrt.warp_extras == {'init_dest': 'NO_DATA'}


def test_warped_vrt_source(path_rgb_byte_tif):
    """A VirtualVRT has the expected source dataset."""
    with rasterio.open(path_rgb_byte_tif) as src:
        vrt = WarpedVRT(src, dst_crs='EPSG:3857')
        assert vrt.src_dataset == src


def test_wrap_file(path_rgb_byte_tif):
    """A VirtualVRT has the expected dataset properties."""
    with rasterio.open(path_rgb_byte_tif) as src:
        vrt = WarpedVRT(src, dst_crs='EPSG:3857')
        assert vrt.crs == 'EPSG:3857'
        assert tuple(round(x, 1) for x in vrt.bounds) == (
            -8789636.7, 2700460.0, -8524406.4, 2943560.2)
        assert vrt.name.startswith('WarpedVRT(')
        assert vrt.name.endswith('tests/data/RGB.byte.tif)')
        assert vrt.indexes == (1, 2, 3)
        assert vrt.nodatavals == (0, 0, 0)
        assert vrt.dtypes == ('uint8', 'uint8', 'uint8')
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
        dst_transform = Affine(resolution, 0.0, extent[0],
                               0.0, -resolution, extent[1])
        vrt = WarpedVRT(src, dst_crs='EPSG:3857',
                        dst_width=size, dst_height=size,
                        dst_transform=dst_transform)
        assert vrt.dst_crs == 'EPSG:3857'
        assert vrt.src_nodata == 0.0
        assert vrt.dst_nodata == 0.0
        assert vrt.resampling == Resampling.nearest
        assert vrt.width == size
        assert vrt.height == size
        assert vrt.transform == dst_transform
        assert vrt.warp_extras == {'init_dest': 'NO_DATA'}


def test_warp_extras(path_rgb_byte_tif):
    """INIT_DEST warp extra is passed through."""
    with rasterio.open(path_rgb_byte_tif) as src:
        with WarpedVRT(src, dst_crs='EPSG:3857', init_dest=255) as vrt:
            rgb = vrt.read()
            assert (rgb[:, 0, 0] == 255).all()


@requires_gdal21(reason="S3 raster access requires GDAL 2.1+")
@credentials
@pytest.mark.network
def test_wrap_s3():
    """A warp wrapper's dataset has the expected properties"""
    L8TIF = "s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF"
    with rasterio.open(L8TIF) as src:
        with WarpedVRT(src, dst_crs='EPSG:3857', src_nodata=0, dst_nodata=0) as vrt:
            assert vrt.crs == 'EPSG:3857'
            assert tuple(round(x, 1) for x in vrt.bounds) == (
                9556764.6, 2345109.3, 9804595.9, 2598509.1)
            assert vrt.name == 'WarpedVRT(s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF)'
            assert vrt.indexes == (1,)
            assert vrt.nodatavals == (0,)
            assert vrt.dtypes == ('uint16',)
            assert vrt.shape == (7827, 7655)


def test_warped_vrt_nodata_read(path_rgb_byte_tif):
    """A read from a VirtualVRT respects dst_nodata."""
    with rasterio.open(path_rgb_byte_tif) as src:
        with WarpedVRT(src, dst_crs='EPSG:3857', src_nodata=0) as vrt:
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

    vrt_path = str(tmpdir.join('test_crs_should_be_set.vrt'))

    with rasterio.open(path_rgb_byte_tif) as src:

        dst_crs = 'EPSG:4326'
        dst_height = dst_width = 10
        dst_bounds = transform_bounds(src.crs, dst_crs, *src.bounds)

        # Destination transform
        left, bottom, right, top = dst_bounds
        xres = (right - left) / dst_width
        yres = (top - bottom) / dst_height
        dst_transform = Affine(xres, 0.0, left,
                               0.0, -yres, top)

        # The 'complex' test case hits the affected code path
        vrt_options = {'dst_crs': dst_crs}
        if complex:
            vrt_options.update(
                dst_crs=dst_crs,
                dst_height=dst_height,
                dst_width=dst_width,
                dst_transform=dst_transform,
                resampling=Resampling.nearest)

        with WarpedVRT(src, **vrt_options) as vrt:
            rio_shutil.copy(vrt, vrt_path, driver='VRT')
        with rasterio.open(vrt_path) as src:
            assert src.crs

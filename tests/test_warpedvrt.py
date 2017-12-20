import boto3
import pytest
import numpy as np

import rasterio
from rasterio.enums import Resampling
from rasterio.transform import Affine
from rasterio.vrt import WarpedVRT

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


def test_warped_vrt_resampling(path_rgb_byte_tif):
    """
    Read from a WarpedVRT using different resampling methods.
    """
    # window in EPSG 3857 partly overlapping with example TIFF
    window_bounds = (
        -8766409.899970274, 2817774.610704731, -8609866.866042234,
        2974317.6446327716)

    with rasterio.open(path_rgb_byte_tif) as src:
        # simple read using default nearest interpolation
        with WarpedVRT(src, dst_crs='EPSG:3857') as vrt:
            nearest = vrt.read(window=vrt.window(*window_bounds))
        # initialize VRT with bilinear interpolation
        with WarpedVRT(
            src, dst_crs='EPSG:3857', resampling=Resampling.bilinear
        ) as vrt:
            bilinear1 = vrt.read(window=vrt.window(*window_bounds))
        # make sure interpolation was applied
        assert not np.array_equal(nearest, bilinear1)

        # again but with boundles=True
        # simple read using default nearest interpolation
        with WarpedVRT(src, dst_crs='EPSG:3857') as vrt:
            nearest = vrt.read(
                window=vrt.window(*window_bounds), boundless=True)
        # initialize VRT with bilinear interpolation
        with WarpedVRT(
            src, dst_crs='EPSG:3857', resampling=Resampling.bilinear
        ) as vrt:
            bilinear1 = vrt.read(
                window=vrt.window(*window_bounds), boundless=True)
        # make sure interpolation was applied
        assert not np.array_equal(nearest, bilinear1)

        # # initialize with default but read with bilinear interpolation
        # with WarpedVRT(src, dst_crs='EPSG:3857') as vrt:
        #     bilinear2 = vrt.read(
        #         window=vrt.window(*window_bounds), boundless=True,
        #         resampling=Resampling.bilinear)
        # assert np.array_equal(bilinear1, bilinear2)


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

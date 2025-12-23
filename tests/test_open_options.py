"""Tests of dataset opening options and driver choice"""
from contextlib import nullcontext
import concurrent.futures

import pytest

import rasterio
from rasterio.env import _GDAL_AT_LEAST_3_10, _GDAL_AT_LEAST_3_11
from rasterio.transform import Affine

def test_fail_with_missing_driver():
    """Fail to open a GeoTIFF without the GTiff driver"""
    with pytest.raises(rasterio.errors.RasterioIOError):
        rasterio.open('tests/data/RGB.byte.tif', driver='BMP')


def test_open_specific_driver():
    """Open a GeoTIFF with the GTiff driver"""
    with rasterio.open('tests/data/RGB.byte.tif', driver='GTiff') as src:
        assert src.count == 3


def test_open_specific_driver_with_options():
    """Open a GeoTIFF with the GTiff driver and GEOREF_SOURCES option"""
    with rasterio.open(
            'tests/data/RGB.byte.tif', driver='GTiff', GEOREF_SOURCES='NONE') as src:
        assert src.transform == Affine.identity()


def test_open_thread_safe(path_rgb_byte_tif, tmp_path):
    with (
        pytest.raises(rasterio.errors.GDALOptionNotImplementedError) if not _GDAL_AT_LEAST_3_10 else nullcontext(),
        rasterio.Env(GDAL_NUM_THREADS=2),
        rasterio.open(path_rgb_byte_tif, thread_safe=True, driver="LIBERTIFF" if _GDAL_AT_LEAST_3_11 else "GTiff") as src,
    ):
        def process(window):
            src.read(window=window).sum()

        windows = [window for ij, window in src.block_windows()]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(process, windows)

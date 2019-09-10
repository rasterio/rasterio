"""Tests for correct behavior of Rasterio's GDALEnv in concurrent programs"""

from concurrent.futures import ThreadPoolExecutor

import rasterio


def get_data(path):
    """Return all raster bands as an ndarray"""
    with rasterio.open(path, sharing=False) as src:
        return src.read()


def test_threads_main_env():
    """Get raster data using ThreadPoolExecutor with main thread Env"""
    with rasterio.Env(), ThreadPoolExecutor(4) as pool:
        for res in pool.map(get_data, ['tests/data/RGB.byte.tif'] * 10):
            assert res.any()


def test_threads_no_main_env():
    """Get raster data using ThreadPoolExecutor with no main thread Env"""
    with ThreadPoolExecutor(4) as pool:
        for res in pool.map(get_data, ['tests/data/RGB.byte.tif'] * 10):
            assert res.any()

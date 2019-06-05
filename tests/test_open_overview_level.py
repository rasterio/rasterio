"""Tests for fix of #1504"""

import rasterio

from .conftest import requires_gdal2


@requires_gdal2
def test_overview_levels(path_cogeo_tif):
    """With sharing turned off, problem noted in #1504 vanishes"""
    olevel = 0
    with rasterio.open(path_cogeo_tif, overview_level=olevel) as src:
        assert src.shape == (512, 512)

        olevel = 1
        with rasterio.open(path_cogeo_tif, sharing=False, overview_level=olevel) as src:
            assert src.shape == (256, 256)

            olevel = 2
            with rasterio.open(path_cogeo_tif, sharing=False, overview_level=olevel) as src:
                assert src.shape == (128, 128)

"""Tests of dataset opening options and driver choice"""

from packaging.version import parse
import pytest

import rasterio
from rasterio.transform import Affine


@pytest.mark.xfail(parse(rasterio.__gdal_version__) < parse('2.0'),
                   reason="Requires a GDAL 2.0 feature")
def test_fail_with_missing_driver():
    """Fail to open a GeoTIFF without the GTiff driver"""
    with pytest.raises(rasterio.errors.RasterioIOError):
        rasterio.open('tests/data/RGB.byte.tif', driver='BMP')


@pytest.mark.xfail(parse(rasterio.__gdal_version__) < parse('2.0'),
                   reason="Requires a GDAL 2.0 feature")
def test_open_specific_driver():
    """Open a GeoTIFF with the GTiff driver"""
    with rasterio.open('tests/data/RGB.byte.tif', driver='GTiff') as src:
        assert src.count == 3


@pytest.mark.skipif(parse(rasterio.__gdal_version__) < parse('2.2'),
                    reason="Requires a GDAL 2.2 feature")
def test_open_specific_driver_with_options():
    """Open a GeoTIFF with the GTiff driver and GEOREF_SOURCES option"""
    with rasterio.open(
            'tests/data/RGB.byte.tif', driver='GTiff', GEOREF_SOURCES='NONE') as src:
        assert src.transform == Affine.identity()

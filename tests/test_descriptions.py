import pytest

import rasterio
from rasterio.errors import RasterioDeprecationWarning
from rasterio.profiles import default_gtiff_profile


def test_set_band_descriptions(tmpdir):
    """Descriptions can be set when dataset is open"""
    tmptiff = str(tmpdir.join('test.tif'))
    with rasterio.open(
            tmptiff, 'w', count=3, height=256, width=256,
            **default_gtiff_profile) as dst:
        assert dst.descriptions == (None, None, None)
        dst.descriptions = ["this is a test band", "this is another test band", None]
        assert dst.descriptions == (
            "this is a test band", "this is another test band", None)


@pytest.mark.parametrize('value', [[], ['x'], ['x', 'y', 'z']])
def test_set_band_descriptions_error(tmpdir, value):
    """Number of descriptions must match band count"""
    tmptiff = str(tmpdir.join('test.tif'))
    with rasterio.open(
            tmptiff, 'w', count=2, height=256, width=256,
            **default_gtiff_profile) as dst:
        with pytest.raises(ValueError):
            dst.descriptions = value


def test_set_band_descriptions_deprecated(tmpdir):
    """Warn about deprecation"""
    tmptiff = str(tmpdir.join('test.tif'))
    with rasterio.open(
            tmptiff, 'w', count=2, height=256, width=256,
            **default_gtiff_profile) as dst:
        assert dst.descriptions == (None, None)
        with pytest.warns(RasterioDeprecationWarning):
            dst.set_description(1, "this is a test band")
            dst.set_description(2, "this is another test band")
            assert dst.descriptions == (
                "this is a test band", "this is another test band")

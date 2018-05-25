import pytest

import rasterio
from rasterio.errors import RasterioDeprecationWarning
from rasterio.profiles import default_gtiff_profile


def test_set_units(tmpdir):
    """Units can be set when dataset is open"""
    tmptiff = str(tmpdir.join('test.tif'))
    with rasterio.open(
            tmptiff, 'w', count=3, height=256, width=256,
            **default_gtiff_profile) as dst:
        assert dst.units == [None, None, None]
        dst.units = ['meters', 'degC', None]
        assert dst.units == ['meters', 'degC', None]


@pytest.mark.parametrize('value', [['m'], ['m', 'ft', 'sec'], []])
def test_set_units_error(tmpdir, value):
    """Number of values must match band count"""
    tmptiff = str(tmpdir.join('test.tif'))
    with rasterio.open(
            tmptiff, 'w', count=2, height=256, width=256,
            **default_gtiff_profile) as dst:
        with pytest.raises(ValueError):
            dst.units = value


def test_set_units_deprecated(tmpdir):
    """Deprecation is warned"""
    tmptiff = str(tmpdir.join('test.tif'))
    with rasterio.open(
            tmptiff, 'w', count=2, height=256, width=256,
            **default_gtiff_profile) as dst:
        assert dst.units == [None, None]
        with pytest.warns(RasterioDeprecationWarning):
            dst.set_units(1, 'meters')
            dst.set_units(2, 'degC')
            assert dst.units == ['meters', 'degC']

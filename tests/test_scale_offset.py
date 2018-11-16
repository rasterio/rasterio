import pytest

import rasterio
from rasterio.profiles import default_gtiff_profile


def test_set_scales(tmpdir):
    """Scales can be set when dataset is open"""
    tmptiff = str(tmpdir.join('test.tif'))
    with rasterio.open(
            tmptiff, 'w', count=3, height=256, width=256,
            **default_gtiff_profile) as dst:
        assert dst.scales == (1.0,) * 3
        dst.scales = [0.1] * 3
        assert dst.scales == (0.1,) * 3


@pytest.mark.parametrize('value', [[0.1], [2.0] * 3, []])
def test_set_scales_error(tmpdir, value):
    """Number of values must match band count"""
    tmptiff = str(tmpdir.join('test.tif'))
    with rasterio.open(
            tmptiff, 'w', count=2, height=256, width=256,
            **default_gtiff_profile) as dst:
        with pytest.raises(ValueError):
            dst.scales = value


def test_set_offsets(tmpdir):
    """Scales can be set when dataset is open"""
    tmptiff = str(tmpdir.join('test.tif'))
    with rasterio.open(
            tmptiff, 'w', count=3, height=256, width=256,
            **default_gtiff_profile) as dst:
        assert dst.offsets == (0.0,) * 3
        dst.offsets = [0.1] * 3
        assert dst.offsets == (0.1,) * 3


@pytest.mark.parametrize('value', [[0.1], [2.0] * 3, []])
def test_set_offsets_error(tmpdir, value):
    """Number of values must match band count"""
    tmptiff = str(tmpdir.join('test.tif'))
    with rasterio.open(
            tmptiff, 'w', count=2, height=256, width=256,
            **default_gtiff_profile) as dst:
        with pytest.raises(ValueError):
            dst.offsets = value

"""Enum tests"""

import pytest

from rasterio import enums


def test_grey_gray():
    """Name of ColorInterp.grey is 'gray'"""
    assert enums.ColorInterp.grey.name == "gray"


def test_gray_gray():
    """Name of ColorInterp.gray is 'gray'"""
    assert enums.ColorInterp.gray.name == "gray"


@pytest.mark.parametrize("resamp", enums.OverviewResampling)
def test_resampling(resamp):
    """Make sure that resampling value are the same."""
    assert resamp.value == enums.Resampling[resamp.name].value

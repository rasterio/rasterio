"""Enum tests"""

from rasterio import enums


def test_grey_gray():
    """Name of ColorInterp.grey is 'gray'"""
    assert enums.ColorInterp.grey.name == "gray"


def test_gray_gray():
    """Name of ColorInterp.gray is 'gray'"""
    assert enums.ColorInterp.gray.name == "gray"


def test_resampling():
    """Make sure that resampling value are the same."""
    for v in enums.OverviewResampling:
        assert v.value == enums.Resampling[v.name].value

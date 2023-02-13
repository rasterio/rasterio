"""Test of a dataset's statistics method."""

from numpy.testing import assert_almost_equal
import pytest

import rasterio
from rasterio.errors import RasterioError


def test_statistics(path_rgb_byte_tif):
    """Compute, store, and return basic statistics."""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        stats = dataset.statistics(1)
        assert stats.min == 0
        assert stats.max == 255
        assert_almost_equal(stats.mean, 29.947726688477)
        assert_almost_equal(stats.std, 52.340921626611)


def test_statistics_all_invalid(capsys):
    """Raise an exception for stats of an invalid dataset."""
    with rasterio.open("tests/data/all-nodata.tif") as dataset:
        with pytest.raises(RasterioError):
            _ = dataset.statistics(1)

    captured = capsys.readouterr()
    assert "ERROR 1" not in captured.err

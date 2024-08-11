"""Test of a dataset's statistics method."""

from numpy.testing import assert_almost_equal
import pytest

import rasterio
from rasterio import Statistics
from rasterio.errors import RasterioError, RasterioDeprecationWarning


def test_statistics(path_rgb_byte_tif):
    """Compute, store, and return basic statistics."""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        with pytest.warns(RasterioDeprecationWarning):
            stats = dataset.statistics(1)
        assert stats.min == 1.0
        assert stats.max == 255.0
        assert_almost_equal(stats.mean, 44.4344786)
        assert_almost_equal(stats.std, 58.4900559)


def test_statistics_all_invalid(capsys):
    """Raise an exception for stats of an invalid dataset."""
    with rasterio.open("tests/data/all-nodata.tif") as dataset:
        with pytest.warns(RasterioDeprecationWarning):
            with pytest.raises(RasterioError):
                _ = dataset.statistics(1)

    captured = capsys.readouterr()
    assert "ERROR 1" not in captured.err


def test_stats_one_band(path_rgb_byte_tif):
    """Get basic statistics for one band."""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        stats, *rem = dataset.stats(indexes=1)
        assert stats.min == 1.0
        assert stats.max == 255.0
        assert_almost_equal(stats.mean, 44.4344786)
        assert_almost_equal(stats.std, 58.4900559)


def test_stats_one_band_approx(path_rgb_byte_tif):
    """Get approximate statistics for one band."""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        stats, *rem = dataset.stats(indexes=1, approx=True)
        assert stats.min == 1.0
        assert stats.max == 255.0
        assert_almost_equal(stats.mean, 44, decimal=0)
        assert_almost_equal(stats.std, 58, decimal=0)


def test_stats_two_band(path_rgb_byte_tif):
    """Get basic statistics for two bands."""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        *rem, stats = dataset.stats(indexes=[1, 1])
        assert stats.min == 1.0
        assert stats.max == 255.0
        assert_almost_equal(stats.mean, 44.4344786)
        assert_almost_equal(stats.std, 58.4900559)


def test_stats_all_bands(path_rgb_byte_tif):
    """Get basic statistics for all bands."""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        stats, *rem = dataset.stats()
        assert len(rem) == 2
        assert stats.min == 1.0
        assert stats.max == 255.0
        assert_almost_equal(stats.mean, 44.4344786)
        assert_almost_equal(stats.std, 58.4900559)


def test_update_clear(data):
    """Update and clear stats."""
    with rasterio.open(str(data.join("RGB.byte.tif")), "r+") as dataset:
        dataset.update_stats(stats=[Statistics(0, 0, 0, 0)], indexes=[1])
        stats, *rem = dataset.stats(indexes=1)
        assert stats.min == 0
        assert stats.max == 0
        assert stats.mean == 0
        assert stats.std == 0
        dataset.clear_stats()
        # The next call triggers recomputation of stats.
        stats, *rem = dataset.stats(indexes=1, approx=True)
        assert stats.min == 1.0
        assert stats.max == 255.0
        assert_almost_equal(stats.mean, 44, decimal=0)
        assert_almost_equal(stats.std, 56, decimal=0)

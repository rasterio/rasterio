"""Tests of GDAL VSI cache invalidation."""

from rasterio import cache


def test_invalidate_all():
    """Cache is entirely invalidated."""
    cache.invalidate_all()


def test_invalidate_pattern():
    """Cache is partially invalidated."""
    cache.invalidate("https://example.com")

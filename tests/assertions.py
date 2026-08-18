"""Pytest assertions for rasterio tests."""

from rasterio.coords import BoundingBox


def assert_bounding_box_equal(expected, actual, tolerance=1e-4):
    if isinstance(expected, tuple):
        expected = BoundingBox(*expected)
    if isinstance(actual, tuple):
        actual = BoundingBox(*actual)

    left = abs(expected.left - actual.left)
    bottom = abs(expected.bottom - actual.bottom)
    right = abs(expected.right - actual.right)
    top = abs(expected.top - actual.top)

    assert all(diff < tolerance for diff in [left, bottom, right, top]), (
        f"{expected} differs from {actual}"
    )

from affine import Affine
import pytest

import rasterio
from rasterio.io import WindowMethodsMixin

EPS = 1.0e-8


def assert_window_almost_equals(a, b, precision=6):
    for pair_outer in zip(a, b):
        for x, y in zip(*pair_outer):
            assert round(x, precision) == round(y, precision)


class MockDatasetBase(object):
    def __init__(self):
        # from tests/data/RGB.byte.tif
        self.affine = Affine(300.0379266750948, 0.0, 101985.0,
                             0.0, -300.041782729805, 2826915.0)
        self.bounds = (101985.0, 2611485.0, 339315.0, 2826915.0)
        self.transform = self.affine
        self.height = 718
        self.width = 791


def test_windows_mixin():

    class MockDataset(MockDatasetBase, WindowMethodsMixin):
        pass

    src = MockDataset()

    assert_window_almost_equals(
        src.window(*src.bounds),
        ((0, src.height), (0, src.width)))

    assert src.window_bounds(
        ((0, src.height),
         (0, src.width))) == src.bounds

    assert src.window_transform(
        ((0, src.height),
         (0, src.width))) == src.transform


def test_windows_mixin_fail():

    class MockDataset(WindowMethodsMixin):
        # doesn't inherit transform, height and width
        pass

    src = MockDataset()
    with pytest.raises(AttributeError):
        assert src.window(0, 0, 1, 1, boundless=True)
    with pytest.raises(AttributeError):
        assert src.window_bounds(((0, 1), (0, 1)))
    with pytest.raises(AttributeError):
        assert src.window_transform(((0, 1), (0, 1)))


def test_window_transform_method():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.window_transform(((0, None), (0, None))) == src.transform
        assert src.window_transform(((None, None), (None, None))) == src.transform
        assert src.window_transform(
                ((1, None), (1, None))).c == src.bounds.left + src.res[0]
        assert src.window_transform(
                ((1, None), (1, None))).f == src.bounds.top - src.res[1]
        assert src.window_transform(
                ((-1, None), (-1, None))).c == src.bounds.left - src.res[0]
        assert src.window_transform(
                ((-1, None), (-1, None))).f == src.bounds.top + src.res[1]


def test_window_method():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        dx, dy = src.res

        assert_window_almost_equals(
            src.window(left + EPS, bottom + EPS, right - EPS, top - EPS),
            ((0, src.height), (0, src.width)))

        assert_window_almost_equals(
            src.window(left, top - 400, left + 400, top),
            ((0, 400 / src.res[1]), (0, 400 / src.res[0])))

        assert_window_almost_equals(
            src.window(left, top - 2 * dy - EPS, left + 2 * dx - EPS, top),
            ((0, 2), (0, 2)))

        # bounds cropped
        assert_window_almost_equals(
            src.window(left - 2 * dx, top - 2 * dy, left + 2 * dx, top + 2 * dy),
            ((0, 2), (0, 2)))

        # boundless
        assert_window_almost_equals(
            src.window(left - 2 * dx, top - 2 * dy, left + 2 * dx, top + 2 * dy, boundless=True),
            ((-2, 2), (-2, 2)))


def test_window_bounds_function():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        rows = src.height
        cols = src.width
        assert src.window_bounds(((0, rows), (0, cols))) == src.bounds

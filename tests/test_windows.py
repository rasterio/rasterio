import rasterio

import numpy as np
import pytest

from rasterio.windows import (
    window, window_bounds, window_transform, eval_window, window_index, window_shape)

def test_window_method():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        dx, dy = src.res
        eps = 1.0e-8
        assert src.window(
            left+eps, bottom+eps, right-eps, top-eps) == ((0, src.height),
                                                          (0, src.width))
        assert src.window(left, top-400, left+400, top) == ((0, 2), (0, 2))
        assert src.window(left, top-2*dy-eps, left+2*dx-eps, top) == ((0, 2), (0, 2))
        # bounds cropped
        assert src.window(left-2*dx, top-2*dy, left+2*dx, top+2*dy) == ((0, 2), (0, 2))
        # boundless
        assert src.window(left-2*dx, top-2*dy,
                          left+2*dx, top+2*dy, boundless=True) == ((-2, 2), (-2, 2))

def test_window_function():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        dx, dy = src.res
        height = src.height
        width = src.width
        transform = src.affine  # TODO deprecate
        eps = 1.0e-8
        assert window(
            transform, left+eps, bottom+eps,
            right-eps, top-eps, height, width) == ((0, height), (0, width))
        assert window(transform, left, top-400,
                      left+400, top, height, width) == ((0, 2), (0, 2))
        assert window(transform, left, top-2*dy-eps,
                      left+2*dx-eps, top, height, width) == ((0, 2), (0, 2))
        # bounds cropped
        assert window(transform, left-2*dx, top-2*dy,
                      left+2*dx, top+2*dy, height, width) == ((0, 2), (0, 2))
        # boundless
        assert window(transform, left-2*dx, top-2*dy,
                      left+2*dx, top+2*dy, boundless=True) == ((-2, 2), (-2, 2))


def test_window_function_valuerror():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        transform = src.affine  # TODO deprecate
        eps = 1.0e-8

    with pytest.raises(ValueError):
        # No height or width
        assert window(
            transform, left+eps, bottom+eps,
            right-eps, top-eps) == ((0, height), (0, width))


def test_window_transform_method():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.window_transform(((0, None), (0, None))) == src.affine
        assert src.window_transform(((None, None), (None, None))) == src.affine
        assert src.window_transform(
                ((1, None), (1, None))).c == src.bounds.left + src.res[0]
        assert src.window_transform(
                ((1, None), (1, None))).f == src.bounds.top - src.res[1]
        assert src.window_transform(
                ((-1, None), (-1, None))).c == src.bounds.left - src.res[0]
        assert src.window_transform(
                ((-1, None), (-1, None))).f == src.bounds.top + src.res[1]


def test_window_transform_function():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        transform = src.affine  # TODO transform
        assert window_transform(transform, ((0, None), (0, None))) == src.affine
        assert window_transform(transform, ((None, None), (None, None))) == src.affine
        assert window_transform(
                transform, ((1, None), (1, None))).c == src.bounds.left + src.res[0]
        assert window_transform(
                transform, ((1, None), (1, None))).f == src.bounds.top - src.res[1]
        assert window_transform(
                transform, ((-1, None), (-1, None))).c == src.bounds.left - src.res[0]
        assert window_transform(
                transform, ((-1, None), (-1, None))).f == src.bounds.top + src.res[1]



def test_window_bounds_method():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        rows = src.height
        cols = src.width
        assert src.window_bounds(((0, rows), (0, cols))) == src.bounds


def test_window_bounds_function():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        rows = src.height
        cols = src.width
        transform = src.affine  # todo deprecate
        assert window_bounds(transform, ((0, rows), (0, cols))) == src.bounds


def test_eval_window_bad_structure():
    with pytest.raises(ValueError):
        eval_window((1, 2, 3), 10, 10)
    with pytest.raises(ValueError):
        eval_window((1, 2), 10, 10)
    with pytest.raises(ValueError):
        eval_window(((1, 0), 2), 10, 10)


def test_eval_window_invalid_dims():
    with pytest.raises(ValueError):
        eval_window(((-1, 10), (0, 10)), -1, 10)
    with pytest.raises(ValueError):
        eval_window(((1, -1), (0, 10)), -1, 10)
    with pytest.raises(ValueError):
        eval_window(((0, 10), (-1, 10)), 10, -1)
    with pytest.raises(ValueError):
        eval_window(((0, 10), (1, -1)), 10, -1)
    with pytest.raises(ValueError):
        eval_window(((10, 5), (0, 5)), 10, 10)
    with pytest.raises(ValueError):
        eval_window(((0, 5), (10, 5)), 10, 10)


def test_eval_window():
    eval_window(((2, 4), (2, 4)), 10, 10) == ((2, 4), (2, 4))
    # TODO check logic of eval_window


def test_window_index():
    idx = window_index(((0, 4), (1, 12)))
    assert len(idx) == 2
    r, c = idx
    assert r.start == 0
    assert r.stop == 4
    assert c.start == 1
    assert c.stop == 12
    arr = np.ones((20, 20))
    assert arr[idx].shape == (4, 11)


# TODO remove redundant tests from test_blocks, test_indexing, test_transform
# TODO remove window_index, window_shape and eval_window from top level

def test_window_shape_errors():
    # Positive height and width are needed when stop is None.
    with pytest.raises(ValueError):
        window_shape(((10, 20), (10, None)))

def test_window_shape_errors2():
    with pytest.raises(ValueError):
        window_shape(((-1, 10), (10, 20)))

def test_window_shape_None_start():
    assert window_shape(((None, 4), (None, 102))) == (4, 102)

def test_window_shape_None_stop():
    assert window_shape(((10, None), (10, None)), 100, 90) == (90, 80)

def test_window_shape_positive():
    assert window_shape(((0, 4), (1, 102))) == (4, 101)

def test_window_shape_negative():
    assert window_shape(((-10, None), (-10, None)), 100, 90) == (10, 10)
    assert window_shape(((~0, None), (~0, None)), 100, 90) == (1, 1)
    assert window_shape(((None, ~0), (None, ~0)), 100, 90) == (99, 89)

def test_eval():
    assert eval_window(((-10, None), (-10, None)), 100, 90) == ((90, 100), (80, 90))
    assert eval_window(((None, -10), (None, -10)), 100, 90) == ((0, 90), (0, 80))

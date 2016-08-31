import math

from affine import Affine
from hypothesis import assume, given, strategies as st
import numpy as np
import pytest

import rasterio
from rasterio.windows import (
    from_bounds, bounds, transform, evaluate, window_index, shape)


EPS = 0.0


@given(pxsz=st.floats(min_value=1.0, max_value=1000.0),
       xoff=st.floats(min_value=-1000000.0, max_value=1000000.0),
       yoff=st.floats(min_value=-1000000.0, max_value=1000000.0),
       height=st.integers(min_value=1, max_value=1000),
       width=st.integers(min_value=1, max_value=1000),
       denominator_exponent=st.integers(min_value=1, max_value=32))
def test_window_inner_snap(pxsz, xoff, yoff, height, width,
                           denominator_exponent):
    """When bounds are slightly smaller than the raster's extent the entire
    raster is selected."""
    aff = Affine(pxsz, 0.0, xoff, 0.0, -pxsz, yoff)
    left, top = xoff, yoff
    right, bottom = xoff + width * pxsz, yoff - height * pxsz
    fraction = 10.0 ** -denominator_exponent
    delta = pxsz * fraction

    # Avoid cases of lost significance.
    assume(left + delta != left and
           bottom + delta != bottom and
           right - delta != right and
           top - delta != top)

    assert from_bounds(left + delta, bottom + delta, right - delta,
            top - delta, aff, height=height, width=width) \
        == ((0, height), (0, width))


@given(pxsz=st.floats(min_value=1.0, max_value=1000.0),
       xoff=st.floats(min_value=-1000000.0, max_value=1000000.0),
       yoff=st.floats(min_value=-1000000.0, max_value=1000000.0),
       height=st.integers(min_value=1, max_value=1000),
       width=st.integers(min_value=1, max_value=1000),
       denominator_exponent=st.integers(min_value=1, max_value=11))
def test_window_outer_boundless(pxsz, xoff, yoff, height, width,
                                denominator_exponent):
    """When bounds are slightly larger than the raster's extent the entire
    raster is selected plus one pixel all around."""
    aff = Affine(pxsz, 0.0, xoff, 0.0, -pxsz, yoff)
    left, top = xoff, yoff
    right, bottom = xoff + width * pxsz, yoff - height * pxsz
    fraction = 10.0 ** -denominator_exponent
    delta = pxsz * fraction

    # Avoid cases of lost significance.
    assume(left - delta != left and
           bottom - delta != bottom and
           right + delta != right and
           top + delta != top)

    assert from_bounds(left - delta, bottom - delta, right + delta,
                       top + delta, aff, height=height, width=width,
                       boundless=True) \
        == ((-1, height + 1), (-1, width + 1))


def test_window_function():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        dx, dy = src.res
        height = src.height
        width = src.width
        assert from_bounds(
            left+EPS, bottom+EPS, right-EPS, top-EPS, src.transform,
            height, width) == ((0, height), (0, width))
        assert from_bounds(
            left, top-400, left+400, top, src.transform,
            height, width) == ((0, 2), (0, 2))
        assert from_bounds(
            left, top-2*dy-EPS, left+2*dx-EPS, top, src.transform,
            height, width) == ((0, 2), (0, 2))

        # bounds cropped
        assert from_bounds(
            left-2*dx, top-2*dy, left+2*dx, top+2*dy, src.transform,
            height, width) == ((0, 2), (0, 2))

        # boundless
        assert from_bounds(
            left-2*dx, top-2*dy, left+2*dx, top+2*dy, src.transform,
            boundless=True) == ((-2, 2), (-2, 2))


def test_window_function_valuerror():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds

        with pytest.raises(ValueError):
            # No height or width
            from_bounds(left+EPS, bottom+EPS, right-EPS, top-EPS, src.transform)


def test_window_transform_function():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert transform(((0, None), (0, None)), src.transform) == src.transform
        assert transform(((None, None), (None, None)), src.transform) == src.transform
        assert transform(
            ((1, None), (1, None)), src.transform).c == src.bounds.left + src.res[0]
        assert transform(
            ((1, None), (1, None)), src.transform).f == src.bounds.top - src.res[1]
        assert transform(
            ((-1, None), (-1, None)), src.transform).c == src.bounds.left - src.res[0]
        assert transform(
            ((-1, None), (-1, None)), src.transform).f == src.bounds.top + src.res[1]


def test_window_bounds_function():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        rows = src.height
        cols = src.width
        assert bounds(((0, rows), (0, cols)), src.transform) == src.bounds


bad_windows = (
    (1, 2, 3),
    (1, 2),
    ((1, 0), 2))

@pytest.mark.parametrize("window", bad_windows)
def test_eval_window_bad_structure(window):
    with pytest.raises(ValueError):
        evaluate(window, 10, 10)


bad_params = (
    (((-1, 10), (0, 10)), -1, 10),
    (((1, -1), (0, 10)), -1, 10),
    (((0, 10), (-1, 10)), 10, -1),
    (((0, 10), (1, -1)), 10, -1),
    (((10, 5), (0, 5)), 10, 10),
    (((0, 5), (10, 5)), 10, 10))

@pytest.mark.parametrize("params", bad_params)
def test_eval_window_invalid_dims(params):
    with pytest.raises(ValueError):
        evaluate(*params)


def test_windows_evaluate():
    assert evaluate(((2, 4), (2, 4)), 10, 10) == ((2, 4), (2, 4))
    assert evaluate(((-10, None), (-10, None)), 100, 90) == ((90, 100), (80, 90))
    assert evaluate(((None, -10), (None, -10)), 100, 90) == ((0, 90), (0, 80))


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


def test_window_shape_errors():
    # Positive height and width are needed when stop is None.
    with pytest.raises(ValueError):
        assert shape(((10, 20), (10, None)))

    with pytest.raises(ValueError):
        assert shape(((-1, 10), (10, 20)))


def test_window_shape_None_start():
    assert shape(((None, 4), (None, 102))) == (4, 102)


def test_shape_None_stop():
    assert shape(((10, None), (10, None)), 100, 90) == (90, 80)


def test_shape_positive():
    assert shape(((0, 4), (1, 102))) == (4, 101)


def test_shape_negative():
    assert shape(((-10, None), (-10, None)), 100, 90) == (10, 10)
    assert shape(((~0, None), (~0, None)), 100, 90) == (1, 1)
    assert shape(((None, ~0), (None, ~0)), 100, 90) == (99, 89)

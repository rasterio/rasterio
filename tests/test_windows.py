from copy import copy
import logging
import sys

from affine import Affine
from hypothesis import given
from hypothesis.strategies import floats
import numpy as np
import pytest

import rasterio
from rasterio.windows import (
    from_bounds, bounds, transform, evaluate, window_index, shape, Window,
    intersect, intersection, get_data_window, union, round_window_to_full_blocks)


EPS = 1.0e-8

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def assert_window_almost_equals(a, b, precision=6):
    for pair_outer in zip(a, b):
        for x, y in zip(*pair_outer):
            assert round(x, precision) == round(y, precision)


@given(col_off=floats(min_value=-1.0e+7, max_value=1.0e+7),
       row_off=floats(min_value=-1.0e+7, max_value=1.0e+7),
       num_cols=floats(min_value=0.0, max_value=1.0e+7),
       num_rows=floats(min_value=0.0, max_value=1.0e+7)) 
def test_window_ctor(col_off, row_off, num_cols, num_rows):
    window = Window(col_off, row_off, num_cols, num_rows)
    assert window.col_off == col_off
    assert window.row_off == row_off
    assert window.num_cols == num_cols
    assert window.num_rows == num_rows


def test_window_function():
    # TODO: break this test up.
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        dx, dy = src.res
        height = src.height
        width = src.width

        assert_window_almost_equals(from_bounds(
            left + EPS, bottom + EPS, right - EPS, top - EPS, src.transform,
            height, width), ((0, height), (0, width)))

        assert_window_almost_equals(from_bounds(
            left, top - 2 * dy - EPS, left + 2 * dx - EPS, top, src.transform,
            height, width), ((0, 2), (0, 2)))

        # bounds cropped
        assert_window_almost_equals(from_bounds(
            left - 2 * dx, top - 2 * dy, left + 2 * dx, top + 2 * dy,
            src.transform, height, width), ((0, 2), (0, 2)))

        # boundless
        assert_window_almost_equals(from_bounds(
            left - 2 * dx, top - 2 * dy, left + 2 * dx, top + 2 * dy,
            src.transform, boundless=True), ((-2, 2), (-2, 2)))


def test_window_float():
    """Test window float values"""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        dx, dy = src.res
        height = src.height
        width = src.width

        assert_window_almost_equals(from_bounds(
            left, top - 400, left + 400, top, src.transform,
            height, width), ((0, 400 / src.res[1]), (0, 400 / src.res[0])))


def test_window_bounds_south_up():
    identity = Affine.identity()
    assert_window_almost_equals(
        from_bounds(0, 10, 10, 0, identity, 10, 10),
        Window(0, 0, 10, 10),
        precision=5)

def test_toranges():
    assert Window(0, 0, 1, 1).toranges() == ((0, 1), (0, 1))


def test_window_function():
    # TODO: break this test up.
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        dx, dy = src.res
        height = src.height
        width = src.width

        assert_window_almost_equals(from_bounds(
            left + EPS, bottom + EPS, right - EPS, top - EPS, src.transform,
            height, width), ((0, height), (0, width)))

        assert_window_almost_equals(from_bounds(
            left, top - 2 * dy - EPS, left + 2 * dx - EPS, top, src.transform,
            height, width), ((0, 2), (0, 2)))

        # bounds cropped
        assert_window_almost_equals(from_bounds(
            left - 2 * dx, top - 2 * dy, left + 2 * dx, top + 2 * dy,
            src.transform, height, width), ((0, 2), (0, 2)))

        # boundless
        assert_window_almost_equals(from_bounds(
            left - 2 * dx, top - 2 * dy, left + 2 * dx, top + 2 * dy,
            src.transform, boundless=True), ((-2, 2), (-2, 2)))


def test_window_float():
    """Test window float values"""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        dx, dy = src.res
        height = src.height
        width = src.width

        assert_window_almost_equals(from_bounds(
            left, top - 400, left + 400, top, src.transform,
            height, width), ((0, 400 / src.res[1]), (0, 400 / src.res[0])))


def test_window_bounds_south_up():
    identity = Affine.identity()
    assert_window_almost_equals(
        from_bounds(0, 10, 10, 0, identity, 10, 10),
        Window(0, 0, 10, 10),
        precision=5)

def test_toranges():
    assert Window(0, 0, 1, 1).toranges() == ((0, 1), (0, 1))

@given(col_off=floats(min_value=-1.0e+7, max_value=1.0e+7),
       row_off=floats(min_value=-1.0e+7, max_value=1.0e+7),
       num_cols=floats(min_value=0.0, max_value=1.0e+7),
       num_rows=floats(min_value=0.0, max_value=1.0e+7)) 
def test_array_interface(col_off, row_off, num_cols, num_rows):
    arr = np.array(Window(col_off, row_off, num_cols, num_rows))
    assert arr.shape == (2, 2)


def test_window_bounds_north_up():
    transform = Affine.translation(0.0, 10.0) * Affine.scale(1.0, -1.0) * Affine.identity()
    assert_window_almost_equals(
        from_bounds(0, 0, 10, 10, transform, 10, 10),
        Window(0, 0, 10, 10),
        precision=5)


def test_window_function_valuerror():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds

        with pytest.raises(ValueError):
            # No height or width
            from_bounds(left + EPS, bottom + EPS, right - EPS, top - EPS,
                        src.transform)


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


@pytest.mark.parametrize("params,expected", [
    ([((2, 4), (2, 4)), 10, 10], ((2, 4), (2, 4))),
    ([((-10, None), (-10, None)), 100, 90], ((90, 100), (80, 90))),
    ([((None, -10), (None, -10)), 100, 90], ((0, 90), (0, 80))),
    ([((0, 256), (0, 256)), 7791, 7621], ((0, 256), (0, 256)))])
def test_windows_evaluate(params, expected):
    assert evaluate(*params) == Window.from_ranges(*expected)


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


def test_window_class_constructor():
    """Construct a Window from offsets, height, and width"""
    window = Window(row_off=0, col_off=1, num_rows=100, num_cols=200)
    assert window == Window.from_ranges((0, 100), (1, 201))


def test_window_class_constructor_positional():
    """Construct a Window using positional parameters"""
    window = Window(1, 0, 200, 100)
    assert window == Window.from_ranges((0, 100), (1, 201))


def test_window_class_attrs():
    """Test Window attributes"""
    window = Window(row_off=0, col_off=1, num_rows=100, num_cols=200)
    assert window.col_off == 1
    assert window.row_off == 0
    assert window.num_cols == 200
    assert window.num_rows == 100


def test_window_class_repr():
    """Test Window respresentation"""
    window = Window(row_off=0, col_off=1, num_rows=100, num_cols=200)
    assert repr(window) == 'Window(col_off=1, row_off=0, num_cols=200, num_rows=100)'
    assert eval(repr(window)) == Window.from_ranges((0, 100), (1, 201))


def test_window_class_copy():
    """Test Window copying"""
    window = Window(row_off=0, col_off=1, num_rows=100, num_cols=200)
    assert copy(window) == Window.from_ranges((0, 100), (1, 201))


def test_window_class_todict():
    """Test Window.todict"""
    window = Window(row_off=0, col_off=1, num_rows=100, num_cols=200)
    assert window.todict() == {
        'col_off': 1, 'num_cols': 200, 'num_rows': 100, 'row_off': 0}


def test_window_class_toslices():
    """Test Window.toslices"""
    window = Window(row_off=0, col_off=1, num_rows=100, num_cols=200)
    yslice, xslice = window.toslices()
    assert yslice.start == 0
    assert yslice.stop == 100
    assert xslice.start == 1
    assert xslice.stop == 201


def test_window_class_intersects():
    """Windows intersect"""
    assert intersect(Window(0, 0, 10, 10), Window(8, 8, 10, 10))


def test_window_class_intersects_list():
    """A list of Windows intersect"""
    assert intersect([Window(0, 0, 10, 10), Window(8, 8, 10, 10)])


def test_window_class_nonintersects():
    """Windows do not intersect"""
    assert not intersect(Window(0, 0, 10, 10), Window(10, 10, 10, 10))


def test_window_from_ranges():
    """from_ranges classmethod works."""
    assert Window.from_ranges((0, 1), (2, 3)) == Window.from_ranges((0, 1), (2, 3))


def test_window_from_offlen():
    """from_offlen classmethod works."""
    assert Window.from_offlen(2, 0, 1, 1) == Window.from_ranges((0, 1), (2, 3))


def test_read_with_window_class():
    """Reading subset with Window class works"""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        subset = src.read(1, window=Window(0, 0, 10, 10))
        assert subset.shape == (10, 10)


def test_data_window_invalid_arr_dims():
    """An array of more than 3 dimensions is invalid."""
    arr = np.ones((3, 3, 3, 3))
    with pytest.raises(ValueError):
        get_data_window(arr)


def test_data_window_full():
    """Get window of entirely valid data array."""
    arr = np.ones((3, 3))
    window = get_data_window(arr)
    assert window == Window.from_ranges((0, 3), (0, 3))


def test_data_window_nodata():
    """Get window of arr with nodata."""
    arr = np.ones((3, 3))
    arr[0, :] = 0
    window = get_data_window(arr, nodata=0)
    assert window == Window.from_ranges((1, 3), (0, 3))


def test_data_window_novalid():
    """Get window of arr with nodata."""
    arr = np.ones((3, 3))
    arr[:, :] = 0
    window = get_data_window(arr, nodata=0)
    assert window == Window.from_ranges((0, 0), (0, 0))


def test_data_window_maskedarray():
    """Get window of masked arr."""
    arr = np.ones((3, 3))
    arr[0, :] = 0
    arr = np.ma.masked_array(arr, arr == 0)
    window = get_data_window(arr)
    assert window == Window.from_ranges((1, 3), (0, 3))


def test_data_window_nodata_3d():
    """Get window of 3d arr with nodata."""
    arr = np.ones((3, 3, 3))
    arr[:, 0, :] = 0
    window = get_data_window(arr, nodata=0)
    assert window == Window.from_ranges((1, 3), (0, 3))


def test_window_union():
    """Window union works."""
    window = union(Window(0, 0, 1, 1), Window(1, 1, 2, 2))
    assert window == Window.from_ranges((0, 3), (0, 3))


def test_no_intersection():
    """Non intersecting windows raises error."""
    with pytest.raises(ValueError):
        intersection(Window(0, 0, 1, 1), Window(1, 1, 2, 2))


def test_intersection():
    """Window intersection works."""
    window = intersection(Window(0, 0, 10, 10), Window(8, 8, 12, 12))
    assert window == Window.from_ranges((8, 10), (8, 10))


def test_round_window_to_full_blocks():
    with rasterio.open('tests/data/alpha.tif') as src:
        block_shapes = src.block_shapes
        test_window = ((321, 548), (432, 765))
        rounded_window = round_window_to_full_blocks(test_window, block_shapes)
        block_shape = block_shapes[0]
        height_shape = block_shape[0]
        width_shape = block_shape[1]
        assert rounded_window[0][0] % height_shape == 0
        assert rounded_window[0][1] % height_shape == 0
        assert rounded_window[1][0] % width_shape == 0
        assert rounded_window[1][1] % width_shape == 0

def test_round_window_already_at_edge():
    with rasterio.open('tests/data/alpha.tif') as src:
        block_shapes = src.block_shapes
        test_window = ((256, 512), (512, 768))
        rounded_window = round_window_to_full_blocks(test_window, block_shapes)
        assert rounded_window == Window.from_ranges(*test_window)

def test_round_window_boundless():
    with rasterio.open('tests/data/alpha.tif') as src:
        block_shapes = src.block_shapes
        test_window = ((256, 512), (1000, 1500))
        rounded_window = round_window_to_full_blocks(test_window, block_shapes)
        block_shape = block_shapes[0]
        height_shape = block_shape[0]
        width_shape = block_shape[1]
        assert rounded_window[0][0] % height_shape == 0
        assert rounded_window[0][1] % height_shape == 0
        assert rounded_window[1][0] % width_shape == 0
        assert rounded_window[1][1] % width_shape == 0

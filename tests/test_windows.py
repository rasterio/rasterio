import logging
import sys

import numpy as np
import pytest
from affine import Affine
from hypothesis import given
from hypothesis.strategies import floats, integers

import rasterio
from rasterio.errors import RasterioDeprecationWarning, WindowError
from rasterio.windows import (
    crop, from_bounds, bounds, transform, evaluate, window_index, shape,
    Window, intersect, intersection, get_data_window, union,
    round_window_to_full_blocks)

EPS = 1.0e-8

# hypothesis inputs: col_off, row_off
F_OFF = floats(min_value=-1.0e+7, max_value=1.0e+7)
I_OFF = floats(min_value=-10000000, max_value=10000000)

# hypothesis inputs: width, height
F_LEN = floats(min_value=0, max_value=1.0e+7)
I_LEN = integers(min_value=0, max_value=1.0e+7)



logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def assert_window_almost_equals(a, b):
    assert np.allclose(a.flatten(), b.flatten(), rtol=1e-3, atol=1e-4)



def test_window_repr():
    assert str(Window(0, 1, 4, 2)) == ('Window(col_off=0, row_off=1, width=4, '
                                       'height=2)')


@given(col_off=F_OFF, row_off=F_OFF, width=F_LEN, height=F_LEN)
def test_window_class(col_off, row_off, width, height):
    """Floating point inputs should not be rounded, and 0 values should not 
    raise errors"""

    window = Window(col_off, row_off, width, height)

    assert np.allclose(window.col_off, col_off)
    assert np.allclose(window.row_off, row_off)
    assert np.allclose(window.width, width)
    assert np.allclose(window.height, height)


@given(col_off=F_OFF, row_off=F_OFF, width=F_LEN, height=F_LEN)
def test_window_flatten(col_off, row_off, width, height):
    """Flattened window should match inputs"""

    assert np.allclose(
        Window(col_off, row_off, width, height).flatten(),
        (col_off, row_off, width, height))


@given(col_off=F_OFF, row_off=F_OFF, width=F_LEN, height=F_LEN)
def test_window_todict(col_off, row_off, width, height):
    """Dictionary of window should match inputs"""

    d = Window(col_off, row_off, width, height).todict()

    assert np.allclose(
        (d['col_off'], d['row_off'], d['width'], d['height']),
        (col_off, row_off, width, height))


@given(col_off=F_OFF, row_off=F_OFF, width=F_LEN, height=F_LEN)
def test_window_toranges(col_off, row_off, width, height):
    """window.toranges() should match inputs"""

    assert np.allclose(
        Window(col_off, row_off, width, height).toranges(),
        ((row_off, row_off + height), (col_off, col_off + width)))


@given(col_off=F_OFF, row_off=F_OFF, width=F_LEN, height=F_LEN)
def test_window_toslices(col_off, row_off, width, height):
    """window.toslices() should match inputs"""

    expected_slices = (slice(row_off, row_off + height),
                       slice(col_off, col_off + width))

    slices = Window(col_off, row_off, width, height).toslices()

    assert np.allclose(
        [(s.start, s.stop) for s in slices],
        [(s.start, s.stop) for s in expected_slices]
    )


@given(col_off=F_OFF, row_off=F_OFF, num_cols=F_LEN, num_rows=F_LEN,
       height=I_LEN, width=I_LEN)
def test_crop(col_off, row_off, num_cols, num_rows, height, width):

    window = Window(col_off, row_off, num_cols, num_rows)
    cropped_window = crop(window, height, width)

    assert 0.0 <= round(cropped_window.col_off, 3) <= width
    assert 0.0 <= round(cropped_window.row_off, 3) <= height
    assert round(cropped_window.width, 3) <= round(width - cropped_window.col_off, 3)
    assert round(cropped_window.height, 3) <= round(height - cropped_window.row_off, 3)


def test_window_from_bounds(path_rgb_byte_tif):
    # TODO: break this test up.
    with rasterio.open(path_rgb_byte_tif) as src:
        left, bottom, right, top = src.bounds
        dx, dy = src.res
        height = src.height
        width = src.width

        assert_window_almost_equals(from_bounds(
            left + EPS, bottom + EPS, right - EPS, top - EPS, src.transform,
            height, width), Window.from_slices((0, height), (0, width)))

        assert_window_almost_equals(from_bounds(
            left, top - 2 * dy - EPS, left + 2 * dx - EPS, top, src.transform,
            height, width), Window.from_slices((0, 2), (0, 2)))

        # boundless
        assert_window_almost_equals(
            from_bounds(left - 2 * dx, top - 2 * dy, left + 2 * dx,
                        top + 2 * dy, src.transform, height=height,
                        width=width),
            Window.from_slices((-2, 2), (-2, 2), boundless=True, height=height,
                               width=width))


def test_window_float(path_rgb_byte_tif):
    """Test window float values"""
    with rasterio.open(path_rgb_byte_tif) as src:
        left, bottom, right, top = src.bounds
        dx, dy = src.res
        height = src.height
        width = src.width

        assert_window_almost_equals(from_bounds(
            left, top - 400, left + 400, top, src.transform,
            height, width), Window.from_slices((0, 400 / src.res[1]), (0, 400 / src.res[0])))


def test_window_bounds_south_up():
    identity = Affine.identity()
    assert_window_almost_equals(
        from_bounds(0, 10, 10, 0, identity, 10, 10),
        Window(0, 0, 10, 10))


def test_window_bounds_north_up():
    transform = Affine.translation(0.0, 10.0) * Affine.scale(1.0, -1.0) * Affine.identity()
    assert_window_almost_equals(
        from_bounds(0, 0, 10, 10, transform, 10, 10),
        Window(0, 0, 10, 10))


def test_window_transform_function(path_rgb_byte_tif):
    with rasterio.open(path_rgb_byte_tif) as src:
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
        assert transform(
            Window(-1, -1, src.width + 1, src.height + 1),
            src.transform).f == src.bounds.top + src.res[1]


def test_window_bounds_function(path_rgb_byte_tif):
    with rasterio.open(path_rgb_byte_tif) as src:
        rows = src.height
        cols = src.width
        assert bounds(((0, rows), (0, cols)), src.transform) == src.bounds


bad_type_windows = [
    (1, 2),
    ((1, 0), 2)]


@pytest.mark.parametrize("window", bad_type_windows)
def test_eval_window_bad_type(window):
    with pytest.raises(WindowError):
        evaluate(window, 10, 10)


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
    with pytest.raises(WindowError):
        assert shape(((10, 20), (10, None)))


def test_window_shape_None_start():
    assert shape(((None, 4), (None, 102))) == (4, 102)


def test_shape_None_stop():
    assert shape(((10, None), (10, None)), 100, 90) == (90, 80)


def test_shape_positive():
    assert shape(((0, 4), (1, 102))) == (4, 101)


def test_shape_negative():
    assert shape(((-10, None), (-10, None)), 100, 90) == (10, 10)
    assert shape(((~0, None), (~0, None)), 100, 90) == (1, 1)


def test_shape_negative_start():
    assert shape(((None, ~0), (None, ~0)), 100, 90) == (99, 89)


def test_window_class_intersects():
    """Windows intersect"""
    assert intersect(Window(0, 0, 10, 10), Window(8, 8, 10, 10))


def test_window_class_intersects_list():
    """A list of Windows intersect"""
    assert intersect([Window(0, 0, 10, 10), Window(8, 8, 10, 10)])


def test_window_class_nonintersects():
    """Windows do not intersect"""
    assert not intersect(Window(0, 0, 10, 10), Window(10, 10, 10, 10))


def test_window_from_slices():
    """from_slices classmethod works."""
    assert Window.from_slices((0, 1), (2, 3)) == Window.from_slices((0, 1), (2, 3))


def test_window_from_offlen():
    """from_offlen classmethod works."""
    with pytest.warns(RasterioDeprecationWarning):
        assert Window.from_offlen(2, 0, 1, 1) == Window.from_slices((0, 1), (2, 3))


def test_read_with_window_class(path_rgb_byte_tif):
    """Reading subset with Window class works"""
    with rasterio.open(path_rgb_byte_tif) as src:
        subset = src.read(1, window=Window(0, 0, 10, 10))
        assert subset.shape == (10, 10)


def test_data_window_invalid_arr_dims():
    """An array of more than 3 dimensions is invalid."""
    arr = np.ones((3, 3, 3, 3))
    with pytest.raises(WindowError):
        get_data_window(arr)


def test_data_window_full():
    """Get window of entirely valid data array."""
    arr = np.ones((3, 3))
    window = get_data_window(arr)
    assert window == Window.from_slices((0, 3), (0, 3))


def test_data_window_nodata():
    """Get window of arr with nodata."""
    arr = np.ones((3, 3))
    arr[0, :] = 0
    window = get_data_window(arr, nodata=0)
    assert window == Window.from_slices((1, 3), (0, 3))


def test_data_window_novalid():
    """Get window of arr with nodata."""
    arr = np.ones((3, 3))
    arr[:, :] = 0
    window = get_data_window(arr, nodata=0)
    assert window == Window.from_slices((0, 0), (0, 0))


def test_data_window_maskedarray():
    """Get window of masked arr."""
    arr = np.ones((3, 3))
    arr[0, :] = 0
    arr = np.ma.masked_array(arr, arr == 0)
    window = get_data_window(arr)
    assert window == Window.from_slices((1, 3), (0, 3))


def test_data_window_nodata_3d():
    """Get window of 3d arr with nodata."""
    arr = np.ones((3, 3, 3))
    arr[:, 0, :] = 0
    window = get_data_window(arr, nodata=0)
    assert window == Window.from_slices((1, 3), (0, 3))


def test_window_union():
    """Window union works."""
    window = union(Window(0, 0, 1, 1), Window(1, 1, 2, 2))
    assert window == Window.from_slices((0, 3), (0, 3))


def test_no_intersection():
    """Non intersecting windows raises error."""
    with pytest.raises(WindowError):
        intersection(Window(0, 0, 1, 1), Window(1, 1, 2, 2))


def test_intersection():
    """Window intersection works."""
    window = intersection(Window(0, 0, 10, 10), Window(8, 8, 12, 12))
    assert window == Window.from_slices((8, 10), (8, 10))


def test_round_window_to_full_blocks(path_alpha_tif):
    with rasterio.open(path_alpha_tif) as src:
        block_shapes = src.block_shapes
        test_window = ((321, 548), (432, 765))
        rounded_window = round_window_to_full_blocks(test_window, block_shapes)
        block_shape = block_shapes[0]
        height_shape = block_shape[0]
        width_shape = block_shape[1]
        assert rounded_window.row_off % height_shape == 0
        assert rounded_window.height % height_shape == 0
        assert rounded_window.col_off % width_shape == 0
        assert rounded_window.width % width_shape == 0


def test_round_window_to_full_blocks_error():
    with pytest.raises(WindowError):
        round_window_to_full_blocks(
            Window(0, 0, 10, 10), block_shapes=[(1, 1), (2, 2)])


def test_round_window_already_at_edge(path_alpha_tif):
    with rasterio.open(path_alpha_tif) as src:
        block_shapes = src.block_shapes
        test_window = ((256, 512), (512, 768))
        rounded_window = round_window_to_full_blocks(test_window, block_shapes)
        assert rounded_window == Window.from_slices(*test_window)


def test_round_window_boundless(path_alpha_tif):
    with rasterio.open(path_alpha_tif) as src:
        block_shapes = src.block_shapes
        test_window = ((256, 512), (1000, 1500))
        rounded_window = round_window_to_full_blocks(test_window, block_shapes)
        block_shape = block_shapes[0]
        height_shape = block_shape[0]
        width_shape = block_shape[1]
        assert rounded_window.row_off % height_shape == 0
        assert rounded_window.height % height_shape == 0
        assert rounded_window.col_off % width_shape == 0
        assert rounded_window.width % width_shape == 0

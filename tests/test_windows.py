import logging
import sys

from collections import namedtuple
import numpy as np
import pytest
from affine import Affine
from hypothesis import given, assume
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


def test_window_class_invalid_inputs():
    """width or height < 0 should raise error"""

    with pytest.raises(ValueError):
        Window(0, 0, -2, 10)

    with pytest.raises(ValueError):
        Window(0, 0, 10, -2)


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


@given(col_off=F_LEN, row_off=F_LEN, col_stop=F_LEN, row_stop=F_LEN)
def test_window_fromslices(col_off, row_off, col_stop, row_stop):
    """Empty and non-empty absolute windows from slices, tuples, or lists
    are valid"""

    # Constrain windows to >= 0 in each dimension
    assume(col_stop >= col_off)
    assume(row_stop >= row_off)

    rows = (row_off, row_stop)
    cols = (col_off, col_stop)
    expected = (col_off, row_off, col_stop - col_off, row_stop - row_off)


    assert np.allclose(
        Window.from_slices(rows=slice(*rows), cols=slice(*cols)).flatten(),
        expected
    )

    assert np.allclose(
        Window.from_slices(rows=rows, cols=cols).flatten(),
        expected
    )

    assert np.allclose(
        Window.from_slices(rows=list(rows), cols=list(cols)).flatten(),
        expected
    )


def test_window_fromslices_invalid_rows_cols():
    """Should raise error if rows or cols  are not slices, lists, or tuples
    of length 2"""

    invalids = (
        np.array([0, 4]),  # wrong type, but close
        '04',  # clearly the wrong type but right length
        (1, 2, 3)  # wrong length
    )

    for invalid in invalids:
        with pytest.raises(WindowError):
            Window.from_slices(rows=invalid, cols=(0, 4))

        with pytest.raises(WindowError):
            Window.from_slices(rows=(0, 4), cols=invalid)


def test_window_fromslices_stops_lt_starts():
    """Should produce empty windows if stop indexes are less than start
    indexes"""

    assert np.allclose(
        Window.from_slices(rows=(4, 2), cols=(0, 4)).flatten(),
        (0, 4, 4, 0)
    )

    assert np.allclose(
        Window.from_slices(rows=(0, 4), cols=(4, 2)).flatten(),
        (4, 0, 0, 4)
    )


@given(abs_off=F_LEN, imp_off=F_LEN, stop=F_LEN, dim=F_LEN)
def test_window_fromslices_implicit(abs_off, imp_off, stop, dim):
    """ providing None for start index will default to 0
    and providing None for stop index will default to width or height """

    assume(stop >= abs_off)
    assume(dim >= imp_off)

    absolute = (abs_off, stop)
    implicit_start = (None, stop)  # => (0, stop)
    implicit_stop = (imp_off, None)  # => (implicit_offset, dim)
    implicit_both = (None, None)  # => (implicit_offset, dim)

    # Implicit start indexes resolve to 0
    assert np.allclose(
        Window.from_slices(rows=implicit_start, cols=absolute).flatten(),
        (abs_off, 0, stop - abs_off, stop)
    )

    assert np.allclose(
        Window.from_slices(rows=absolute, cols=implicit_start).flatten(),
        (0, abs_off, stop, stop - abs_off)
    )

    # Implicit stop indexes resolve to dim (height or width)
    assert np.allclose(
        Window.from_slices(
            rows=implicit_stop, cols=absolute, height=dim).flatten(),
        (abs_off, imp_off, stop - abs_off, dim - imp_off)
    )

    assert np.allclose(
        Window.from_slices(
            rows=absolute, cols=implicit_stop, width=dim).flatten(),
        (imp_off, abs_off, dim - imp_off, stop - abs_off)
    )

    # Both can be implicit
    assert np.allclose(
        Window.from_slices(
            rows=implicit_both, cols=implicit_both,
            width=dim, height=dim).flatten(),
        (0, 0, dim, dim)
    )


def test_window_fromslices_implicit_err():
    """ height and width are required if stop index is None; failing to
    provide them will result in error"""

    with pytest.raises(WindowError):
        Window.from_slices(rows=(1, None), cols=(1, 4))

    with pytest.raises(WindowError):
        Window.from_slices(rows=(1, 4), cols=(1, None))


def test_window_fromslices_negative_start():
    # TODO: if passing negative start, what are valid values for stop?
    assert np.allclose(
        Window.from_slices(rows=(-4, None), cols=(0, 4), height=10).flatten(),
        (0, 6, 4, 4)
    )

    assert np.allclose(
        Window.from_slices(rows=(0, 4), cols=(-4, None), width=10).flatten(),
        (6, 0, 4, 4)
    )

    assert np.allclose(
        Window.from_slices(rows=(-6, None), cols=(-4, None),
                           height=8, width=10).flatten(),
        (6, 2, 4, 6)
    )


def test_window_fromslices_negative_start_missing_dim_err():
    """Should raise error if width or height are not provided"""

    with pytest.raises(WindowError):
        Window.from_slices(rows=(-10, 4), cols=(0, 4))

    with pytest.raises(WindowError):
        Window.from_slices(rows=(0, 4), cols=(-10, 4))


def test_window_fromslices_negative_stop():
    # TODO: Should negative stops even allowed??  Limited to boundless case?
    assert np.allclose(
        Window.from_slices(rows=(-4, -1), cols=(0, 4), height=10).flatten(),
        (0, 6, 4, 3)
    )

    assert np.allclose(
        Window.from_slices(rows=(0, 4), cols=(-4, -1), width=10).flatten(),
        (6, 0, 3, 4)
    )


@given(col_off=F_LEN, row_off=F_LEN, col_stop=F_LEN, row_stop=F_LEN)
def test_window_fromslices_boundless(col_off, row_off, col_stop, row_stop):

    # Constrain windows to >= 0 in each dimension
    assume(col_stop >= col_off)
    assume(row_stop >= row_off)

    assert np.allclose(
        Window.from_slices(
            rows=(-row_off, row_stop), cols=(col_off, col_stop),
            boundless=True).flatten(),
        (col_off, -row_off, col_stop - col_off, row_stop + row_off)
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


def test_shape_negative_start():
    assert shape(((-10, None), (-10, None)), 100, 90) == (10, 10)
    assert shape(((-1, None), (-1, None)), 100, 90) == (1, 1)


def test_shape_negative_stop():
    assert shape(((None, -1), (None, -1)), 100, 90) == (99, 89)


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

"""Window utilities and related functions.

A window is a 2D ndarray indexer in the form of a tuple:

    ((row_start, row_stop), (col_start, col_stop))
"""

import collections
import functools
import math

from affine import Affine
import numpy as np


def iter_args(function):
    """Decorator to allow function to take either *args or
    a single iterable which gets expanded to *args.
    """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        if len(args) == 1 and isinstance(args[0], collections.Iterable):
            return function(*args[0])
        else:
            return function(*args)
    return wrapper


def get_data_window(arr, nodata=None):
    """
    Returns a window for the non-nodata pixels within the input array.

    Parameters
    ----------
    arr: numpy ndarray, <= 3 dimensions
    nodata: number
        If None, will either return a full window if arr is not a masked
        array, or will use the mask to determine non-nodata pixels.
        If provided, it must be a number within the valid range of the dtype
        of the input array.

    Returns
    -------
    ((row_start, row_stop), (col_start, col_stop))

    """

    num_dims = len(arr.shape)
    if num_dims > 3:
        raise ValueError('get_data_window input array must have no more than '
                         '3 dimensions')

    if nodata is None:
        if not hasattr(arr, 'mask'):
            return ((0, arr.shape[-2]), (0, arr.shape[-1]))
    else:
        arr = np.ma.masked_array(arr, arr == nodata)

    if num_dims == 2:
        data_rows, data_cols = np.where(arr.mask == False)
    else:
        data_rows, data_cols = np.where(
            np.any(np.rollaxis(arr.mask, 0, 3) == False, axis=2)
        )

    if data_rows.size:
        row_range = (data_rows.min(), data_rows.max() + 1)
    else:
        row_range = (0, 0)

    if data_cols.size:
        col_range = (data_cols.min(), data_cols.max() + 1)
    else:
        col_range = (0, 0)

    return (row_range, col_range)


@iter_args
def union(*windows):
    """
    Union windows and return the outermost extent they cover.

    Parameters
    ----------
    windows: list-like of window objects
        ((row_start, row_stop), (col_start, col_stop))

    Returns
    -------
    ((row_start, row_stop), (col_start, col_stop))
    """

    stacked = np.dstack(windows)
    return (
        (stacked[0, 0].min(), stacked[0, 1].max()),
        (stacked[1, 0].min(), stacked[1, 1]. max())
    )


@iter_args
def intersection(*windows):
    """
    Intersect windows and return the innermost extent they cover.

    Will raise ValueError if windows do not intersect.

    Parameters
    ----------
    windows: list-like of window objects
        ((row_start, row_stop), (col_start, col_stop))

    Returns
    -------
    ((row_start, row_stop), (col_start, col_stop))
    """

    if not intersect(windows):
        raise ValueError('windows do not intersect')

    stacked = np.dstack(windows)
    return (
        (stacked[0, 0].max(), stacked[0, 1].min()),
        (stacked[1, 0].max(), stacked[1, 1]. min())
    )


@iter_args
def intersect(*windows):
    """
    Test if windows intersect.

    Parameters
    ----------
    windows: list-like of window objects
        ((row_start, row_stop), (col_start, col_stop))

    Returns
    -------
    boolean:
        True if all windows intersect.
    """

    from itertools import combinations

    def intersects(range1, range2):
        return not (
            range1[0] >= range2[1] or range1[1] <= range2[0]
        )

    windows = np.array(windows)

    for i in (0, 1):
        for c in combinations(windows[:, i], 2):
            if not intersects(*c):
                return False

    return True


def window(transform, left, bottom, right, top,
           height=None, width=None, boundless=False):
    """Returns the window corresponding to the world bounding box.
    If boundless is False, window is limited to extent of this dataset."""

    window = get_window(left, bottom, right, top, transform)
    if boundless:
        return window
    else:
        if None in (height, width):
            raise ValueError("Must supply height and width unless boundless")
        return crop_window(window, height, width)


def window_transform(transform, window):
    """Returns the affine transform for a dataset window."""
    (r, _), (c, _) = window
    return transform * Affine.translation(c or 0, r or 0)


def window_bounds(transform, window):
    """Returns the bounds of a window as x_min, y_min, x_max, y_max."""
    ((row_min, row_max), (col_min, col_max)) = window
    x_min, y_min = transform * (col_min, row_max)
    x_max, y_max = transform * (col_max, row_min)
    return x_min, y_min, x_max, y_max


def crop_window(window, height, width):
    """Returns a window cropped to fall within height and width."""
    (r_start, r_stop), (c_start, c_stop) = window
    return (
        (min(max(r_start, 0), height), max(0, min(r_stop, height))),
        (min(max(c_start, 0), width), max(0, min(c_stop, width))))


def eval_window(window, height, width):
    """Evaluates a window tuple that might contain negative values
    in the context of a raster height and width."""
    try:
        r, c = window
        assert len(r) == 2
        assert len(c) == 2
    except (ValueError, TypeError, AssertionError):
        raise ValueError("invalid window structure; expecting ints"
                         "((row_start, row_stop), (col_start, col_stop))")
    r_start = r[0] or 0
    if r_start < 0:
        if height < 0:
            raise ValueError("invalid height: %d" % height)
        r_start += height
    r_stop = r[1] or height
    if r_stop < 0:
        if height < 0:
            raise ValueError("invalid height: %d" % height)
        r_stop += height
    if not r_stop >= r_start:
        raise ValueError(
            "invalid window: row range (%d, %d)" % (r_start, r_stop))
    c_start = c[0] or 0
    if c_start < 0:
        if width < 0:
            raise ValueError("invalid width: %d" % width)
        c_start += width
    c_stop = c[1] or width
    if c_stop < 0:
        if width < 0:
            raise ValueError("invalid width: %d" % width)
        c_stop += width
    if not c_stop >= c_start:
        raise ValueError(
            "invalid window: col range (%d, %d)" % (c_start, c_stop))
    return (r_start, r_stop), (c_start, c_stop)


def get_index(x, y, affine, op=math.floor, precision=6):
    """
    Returns the (row, col) index of the pixel containing (x, y) given a
    coordinate reference system.

    Parameters
    ----------
    x : float
        x value in coordinate reference system
    y : float
        y value in coordinate reference system
    affine : tuple
        Coefficients mapping pixel coordinates to coordinate reference system.
    op : function
        Function to convert fractional pixels to whole numbers (floor, ceiling,
        round)
    precision : int
        Decimal places of precision in indexing, as in `round()`.

    Returns
    -------
    row : int
        row index
    col : int
        col index
    """
    # Use an epsilon, magnitude determined by the precision parameter
    # and sign determined by the op function: positive for floor, negative
    # for ceil.
    eps = 10.0**-precision * (1.0 - 2.0*op(0.1))
    row = int(op((y - eps - affine[5]) / affine[4]))
    col = int(op((x + eps - affine[2]) / affine[0]))
    return row, col


def get_window(left, bottom, right, top, affine, precision=6):
    """
    Returns a window tuple given coordinate bounds and the coordinate reference
    system.

    Parameters
    ----------
    left : float
        Left edge of window
    bottom : float
        Bottom edge of window
    right : float
        Right edge of window
    top : float
        top edge of window
    affine : tuple
        Coefficients mapping pixel coordinates to coordinate reference system.
    precision : int
        Decimal places of precision in indexing, as in `round()`.
    """
    window_start = get_index(
        left, top, affine, op=math.floor, precision=precision)
    window_stop = get_index(
        right, bottom, affine, op=math.ceil, precision=precision)
    window = tuple(zip(window_start, window_stop))
    return window


def window_shape(window, height=-1, width=-1):
    """Returns shape of a window.

    height and width arguments are optional if there are no negative
    values in the window.
    """
    (a, b), (c, d) = eval_window(window, height, width)
    return b-a, d-c


def window_index(window):
    return tuple(slice(*w) for w in window)

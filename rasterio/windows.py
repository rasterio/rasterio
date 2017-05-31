"""Window utilities and related functions.

A window is an instance of Window or a 2D ndarray indexer in the form
of a tuple:

    ((row_start, row_stop), (col_start, col_stop))
"""
from __future__ import division
import collections
import functools
import math
from operator import itemgetter

from affine import Affine
import numpy as np

from rasterio.transform import rowcol


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
    """Window covering the input array's valid data pixels.

    Parameters
    ----------
    arr: numpy ndarray, <= 3 dimensions
    nodata: number
        If None, will either return a full window if arr is not a masked
        array, or will use the mask to determine non-nodata pixels.
        If provided, it must be a number within the valid range of the
        dtype of the input array.

    Returns
    -------
    Window
    """

    num_dims = len(arr.shape)
    if num_dims > 3:
        raise ValueError('get_data_window input array must have no more than '
                         '3 dimensions')

    if nodata is None:
        if not hasattr(arr, 'mask'):
            return Window.from_ranges((0, arr.shape[-2]), (0, arr.shape[-1]))
    else:
        arr = np.ma.masked_array(arr, arr == nodata)

    if num_dims == 2:
        data_rows, data_cols = np.where(arr.mask == False)
    else:
        data_rows, data_cols = np.where(
            np.any(np.rollaxis(arr.mask, 0, 3) == False, axis=2))

    if data_rows.size:
        row_range = (data_rows.min(), data_rows.max() + 1)
    else:
        row_range = (0, 0)

    if data_cols.size:
        col_range = (data_cols.min(), data_cols.max() + 1)
    else:
        col_range = (0, 0)

    return Window.from_ranges(row_range, col_range)


@iter_args
def union(*windows):
    """
    Union windows and return the outermost extent they cover.

    Parameters
    ----------
    windows: sequence
        One or more Windows or window tuples.

    Returns
    -------
    Window
    """

    stacked = np.dstack(windows)
    return Window.from_ranges(
        (stacked[0, 0].min(), stacked[0, 1].max()),
        (stacked[1, 0].min(), stacked[1, 1]. max()))


@iter_args
def intersection(*windows):
    """Innermost extent of window intersections.

    Will raise ValueError if windows do not intersect.

    Parameters
    ----------
    windows: sequence
        One or more Windows or window tuples.

    Returns
    -------
    Window
    """
    if not intersect(windows):
        raise ValueError('windows do not intersect')

    stacked = np.dstack(windows)
    return Window.from_ranges(
        (stacked[0, 0].max(), stacked[0, 1].min()),
        (stacked[1, 0].max(), stacked[1, 1]. min()))


@iter_args
def intersect(*windows):
    """Test if all given windows intersect.

    Parameters
    ----------
    windows: sequence
        One or more Windows or window tuples.

    Returns
    -------
    bool
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


def from_bounds(left, bottom, right, top, transform,
                height=None, width=None, boundless=False, precision=6):
    """Get the window corresponding to the bounding coordinates.

    Parameters
    ----------
    left, bottom, right, top : float
        Left (west), bottom (south), right (east), and top (north)
        bounding coordinates.
    transform : Affine
        Affine transform matrix.
    height, width : int
        Number of rows and columns of the window.
    boundless : boolean, optional
        If True, the output window's size may exceed the given height
        and width.
    precision : int, optional
        Number of decimal points of precision when computing inverse
        transform.

    Returns
    -------
    Window
        A new Window
    """
    window_start = rowcol(
        # transform, left, top, op=math.floor, precision=precision)
        transform, left, top, op=float, precision=precision)

    window_stop = rowcol(
        # transform, right, bottom, op=math.ceil, precision=precision)
        transform, right, bottom, op=float, precision=precision)

    window = Window.from_ranges(*tuple(zip(window_start, window_stop)))

    if boundless:
        return window
    else:
        if None in (height, width):
            raise ValueError("Must supply height and width unless boundless")
        return crop(window, height, width)


def transform(window, transform):
    """Construct an affine transform matrix relative to a window.

    Parameters
    ----------
    window : a Window or window tuple
        The input window.
    transform: Affine
        an affine transform matrix.

    Returns
    -------
    Affine
        The affine transform matrix for the given window
    """
    (r, _), (c, _) = window
    return transform * Affine.translation(c or 0, r or 0)


def bounds(window, transform):
    """Get the spatial bounds of a window.

    Parameters
    ----------
    window : a Window or window tuple
        The input window.
    transform: Affine
        an affine transform matrix.

    Returns
    -------
    x_min, y_min, x_max, y_max : float
        A tuple of spatial coordinate bounding values.
    """
    (row_min, row_max), (col_min, col_max) = window
    x_min, y_min = transform * (col_min, row_max)
    x_max, y_max = transform * (col_max, row_min)
    return x_min, y_min, x_max, y_max


def crop(window, height, width):
    """Crops a window to given height and width.

    Parameters
    ----------
    window : a Window or window tuple
        The input window.
    height, width : int
        The number of rows and cols in the cropped window.

    Returns
    -------
    Window
        A new Window object.
    """
    (r_start, r_stop), (c_start, c_stop) = window
    return Window.from_ranges(
        (min(max(r_start, 0), height), max(0, min(r_stop, height))),
        (min(max(c_start, 0), width), max(0, min(c_stop, width))))


def evaluate(window, height, width):
    """Evaluates a window tuple that may contain relative index values.

    The height and width of the array the window targets is the context
    for evaluation.

    Parameters
    ----------
    window : a Window or window tuple
        The input window.
    height, width : int
        The number of rows or columns in the array that the window
        targets.

    Returns
    -------
    Window
        A new Window object with absolute index values.
    """
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
    return Window.from_ranges((r_start, r_stop), (c_start, c_stop))


def shape(window, height=-1, width=-1):
    """The shape of a window.

    height and width arguments are optional if there are no negative
    values in the window.

    Parameters
    ----------
    window : a Window or window tuple
        The input window.
    height, width : int, optional
        The number of rows or columns in the array that the window
        targets.

    Returns
    -------
    num_rows, num_cols
        The number of rows and columns of the window.
    """
    (a, b), (c, d) = evaluate(window, height, width)
    return (b - a, d - c)


def window_index(window):
    """Construct a pair of slice objects for ndarray indexing

    Parameters
    ----------
    window : a Window or window tuple
        The input window.

    Returns
    -------
    row_slice, col_slice: slice
        A pair of slices in row, column order
    """
    return tuple(slice(*w) for w in window)


def round_window_to_full_blocks(window, block_shapes):
    """
    Round window to include full expanse of intersecting tiles.

    Parameters
    ----------
    window : a Window or window tuple
        The input window.

    block_shapes : tuple of block shapes
        The input raster's block shape. All bands must have the same block/stripe structure

    Returns
    -------
    Window
    """
    if len(set(block_shapes)) != 1:
        raise ValueError('All bands must have the same block/stripe structure')

    height_shape = block_shapes[0][0]
    width_shape = block_shapes[0][1]

    row_range = window[0]
    col_range = window[1]

    row_min = int(row_range[0] // height_shape) * height_shape
    row_max = int(row_range[1] // height_shape) * height_shape + \
        (height_shape if row_range[1] % height_shape != 0 else 0)

    col_min = int(col_range[0] // width_shape) * width_shape
    col_max = int(col_range[1] // width_shape) * width_shape + \
        (width_shape if col_range[1] % width_shape != 0 else 0)

    return Window.from_ranges((row_min, row_max), (col_min, col_max))


class Window(tuple):
    """Windows are rectangular subsets of rasters.
    
    This class abstracts the 2-tuples mentioned in the module docstring
    and adds methods and new constructors.

    Attributes
    ----------
    col_off
    num_cols
    row_off
    num_rows
    """

    __slots__ = ()
    _fields = ('col_off', 'row_off', 'num_cols', 'num_rows')

    def __new__(cls, col_off=0, row_off=0, num_cols=0, num_rows=0):
        """Create new instance of Window."""
        return tuple.__new__(
            cls,
            ((row_off, row_off + num_rows), (col_off, col_off + num_cols)))

    def __repr__(self):
        """Return a nicely formatted representation string"""
        return (
            "Window(col_off={self.col_off}, row_off={self.row_off}, "
            "num_cols={self.num_cols}, num_rows={self.num_rows})").format(
                self=self)

    def __getnewargs__(self):
        'Return self as a plain tuple.  Used by copy and pickle.'
        return self.flatten()

    def flatten(self):
        """A flattened form of the window.

        Returns
        -------
        col_off, row_off, num_cols, num_rows: int
            Window offsets and lengths.
        """
        return (self[1][0], self[0][0],
                self[1][1] - self[1][0], self[0][1] - self[0][0])

    def todict(self):
        """A mapping of field names and values.

        Returns
        -------
        dict
        """
        return collections.OrderedDict(zip(self._fields, self.flatten()))

    def toslices(self):
        """Slice objects for use as an ndarray indexer.

        Returns
        -------
        row_slice, col_slice: slice
            A pair of slices in row, column order
        """
        return tuple(slice(*rng) for rng in self)

    @classmethod
    def from_ranges(cls, row_range, col_range):
        """Construct a Window from row and column range tuples.

        Parameters
        ----------
        row_range, col_range: tuple
            2-tuples containing start, stop indexes.

        Returns
        -------
        Window
        """
        return cls(col_range[0], row_range[0],
                   col_range[1] - col_range[0],
                   row_range[1] - row_range[0])

    @classmethod
    def from_offlen(cls, col_off, row_off, num_cols, num_rows):
        """Contruct a Window from offsets and lengths.

        Parameters
        ----------
        col_off, row_off: int
            Column and row offsets.
        num_cols, num_rows : int
            Lengths (width and height) of the window.

        Returns
        -------
        Window
        """
        return cls(col_off, row_off, num_cols, num_rows)

    @property
    def col_off(self):
        """Column (x) offset of the window.

        Returns
        -------
        int
        """
        return self[1][0]

    @property
    def num_cols(self):
        """Number of cols in the window.

        Returns
        -------
        int
        """
        return self[1][1] - self[1][0]

    @property
    def row_off(self):
        """Row (y) offset of the window.

        Returns
        -------
        int
        """
        return self[0][0]

    @property
    def num_rows(self):
        """Number of rows in the window.

        Returns
        -------
        int
        """
        return self[0][1] - self[0][0]

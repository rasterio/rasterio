"""Window utilities and related functions.

A window is an instance of Window

    Window(column_offset, row_offset, width, height)

or a 2D N-D array indexer in the form of a tuple.

    ((row_start, row_stop), (col_start, col_stop))

The latter can be evaluated within the context of a given height and
width and a boolean flag specifying whether the evaluation is boundless
or not. If boundless=True, negative index values do not mean index from
the end of the array dimension as they do in the boundless=False case.

The newer float precision read-write window capabilities of Rasterio
require instances of Window to be used.
"""

from __future__ import division
import collections
import functools
import math
from operator import itemgetter
import warnings

import attr
from affine import Affine
import numpy as np

from rasterio.errors import RasterioDeprecationWarning, WindowError
from rasterio.transform import rowcol


PIXEL_PRECISION = 6


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


def toranges(window):
    """Normalize Windows to range tuples"""
    if isinstance(window, Window):
        return window.toranges()
    else:
        return window


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
        raise WindowError(
            "get_data_window input array must have no more than "
            "3 dimensions")

    if nodata is None:
        if not hasattr(arr, 'mask'):
            return Window.from_slices((0, arr.shape[-2]), (0, arr.shape[-1]))
    else:
        arr = np.ma.masked_array(arr, arr == nodata)

    if num_dims == 2:
        data_rows, data_cols = np.where(np.equal(arr.mask, False))
    else:
        data_rows, data_cols = np.where(
            np.any(np.equal(np.rollaxis(arr.mask, 0, 3), False), axis=2))

    if data_rows.size:
        row_range = (data_rows.min(), data_rows.max() + 1)
    else:
        row_range = (0, 0)

    if data_cols.size:
        col_range = (data_cols.min(), data_cols.max() + 1)
    else:
        col_range = (0, 0)

    return Window.from_slices(row_range, col_range)


@iter_args
def union(*windows):
    """
    Union windows and return the outermost extent they cover.

    Parameters
    ----------
    windows: sequence
        One or more Windows.

    Returns
    -------
    Window
    """
    stacked = np.dstack([toranges(w) for w in windows])
    return Window.from_slices(
        (stacked[0, 0].min(), stacked[0, 1].max()),
        (stacked[1, 0].min(), stacked[1, 1]. max()))


@iter_args
def intersection(*windows):
    """Innermost extent of window intersections.

    Will raise WindowError if windows do not intersect.

    Parameters
    ----------
    windows: sequence
        One or more Windows.

    Returns
    -------
    Window
    """
    if not intersect(windows):
        raise WindowError("windows do not intersect")

    stacked = np.dstack([toranges(w) for w in windows])
    return Window.from_slices(
        (stacked[0, 0].max(), stacked[0, 1].min()),
        (stacked[1, 0].max(), stacked[1, 1]. min()))


@iter_args
def intersect(*windows):
    """Test if all given windows intersect.

    Parameters
    ----------
    windows: sequence
        One or more Windows.

    Returns
    -------
    bool
        True if all windows intersect.
    """
    from itertools import combinations

    def intersects(range1, range2):
        return not (
            range1[0] >= range2[1] or range1[1] <= range2[0])

    windows = np.array([toranges(w) for w in windows])

    for i in (0, 1):
        for c in combinations(windows[:, i], 2):
            if not intersects(*c):
                return False

    return True


def from_bounds(left, bottom, right, top, transform=None,
                height=None, width=None, precision=6, **kwargs):
    """Get the window corresponding to the bounding coordinates.

    Parameters
    ----------
    left, bottom, right, top: float
        Left (west), bottom (south), right (east), and top (north)
        bounding coordinates.
    transform: Affine
        Affine transform matrix.
    height, width: int
        Number of rows and columns of the window.
    precision: int, optional
        Number of decimal points of precision when computing inverse
        transform.
    kwargs: mapping
        Absorbs deprecated keyword args

    Returns
    -------
    Window
        A new Window
    """
    if 'boundless' in kwargs:
        warnings.warn("boundless keyword should not be used",
                      RasterioDeprecationWarning)

    row_start, col_start = rowcol(
        transform, left, top, op=float, precision=precision)

    row_stop, col_stop = rowcol(
        transform, right, bottom, op=float, precision=precision)

    return Window.from_slices(
        (row_start, row_stop), (col_start, col_stop), height=height,
        width=width, boundless=True)


def transform(window, transform):
    """Construct an affine transform matrix relative to a window.

    Parameters
    ----------
    window: Window
        The input window.
    transform: Affine
        an affine transform matrix.

    Returns
    -------
    Affine
        The affine transform matrix for the given window
    """
    window = evaluate(window, height=0, width=0)

    x, y = transform * (window.col_off or 0.0, window.row_off or 0.0)
    return Affine.translation(
        x - transform.c, y - transform.f) * transform


def bounds(window, transform, height=0, width=0):
    """Get the spatial bounds of a window.

    Parameters
    ----------
    window: Window
        The input window.
    transform: Affine
        an affine transform matrix.

    Returns
    -------
    left, bottom, right, top: float
        A tuple of spatial coordinate bounding values.
    """
    window = evaluate(window, height=height, width=width)

    row_min = window.row_off
    row_max = row_min + window.height
    col_min = window.col_off
    col_max = col_min + window.width

    left, bottom = transform * (col_min, row_max)
    right, top = transform * (col_max, row_min)
    return left, bottom, right, top


def crop(window, height, width):
    """Crops a window to given height and width.

    Parameters
    ----------
    window : Window.
        The input window.
    height, width : int
        The number of rows and cols in the cropped window.

    Returns
    -------
    Window
        A new Window object.
    """
    window = evaluate(window, height=height, width=width)

    row_start = min(max(window.row_off, 0), height)
    col_start = min(max(window.col_off, 0), width)
    row_stop = max(0, min(window.row_off + window.height, height))
    col_stop = max(0, min(window.col_off + window.width, width))

    return Window(col_start, row_start, col_stop - col_start,
                  row_stop - row_start)


def evaluate(window, height, width, boundless=False):
    """Evaluates a window tuple that may contain relative index values.

    The height and width of the array the window targets is the context
    for evaluation.

    Parameters
    ----------
    window: Window.
        The input window.
    height, width: int
        The number of rows or columns in the array that the window
        targets.

    Returns
    -------
    Window
        A new Window object with absolute index values.
    """
    if isinstance(window, Window):
        return window
    else:
        return Window.from_slices(window[0], window[1], height=height, width=width,
                                  boundless=boundless)


def shape(window, height=-1, width=-1):
    """The shape of a window.

    height and width arguments are optional if there are no negative
    values in the window.

    Parameters
    ----------
    window: Window
        The input window.
    height, width : int, optional
        The number of rows or columns in the array that the window
        targets.

    Returns
    -------
    num_rows, num_cols
        The number of rows and columns of the window.
    """
    evaluated = evaluate(window, height, width)
    return evaluated.height, evaluated.width


def window_index(window, height=0, width=0):
    """Construct a pair of slice objects for ndarray indexing

    Starting indexes are rounded down, Stopping indexes are rounded up.

    Parameters
    ----------
    window: Window
        The input window.

    Returns
    -------
    row_slice, col_slice: slice
        A pair of slices in row, column order
    """
    window = evaluate(window, height=height, width=width)

    (row_start, row_stop), (col_start, col_stop) = window.toranges()
    return (
        slice(int(math.floor(row_start)), int(math.ceil(row_stop))),
        slice(int(math.floor(col_start)), int(math.ceil(col_stop))))


def round_window_to_full_blocks(window, block_shapes, height=0, width=0):
    """Round window to include full expanse of intersecting tiles.

    Parameters
    ----------
    window: Window
        The input window.

    block_shapes : tuple of block shapes
        The input raster's block shape. All bands must have the same
        block/stripe structure

    Returns
    -------
    Window
    """
    if len(set(block_shapes)) != 1:  # pragma: no cover
        raise WindowError(
            "All bands must have the same block/stripe structure")

    window = evaluate(window, height=height, width=width)

    height_shape = block_shapes[0][0]
    width_shape = block_shapes[0][1]

    (row_start, row_stop), (col_start, col_stop) = window.toranges()

    row_min = int(row_start // height_shape) * height_shape
    row_max = int(row_stop // height_shape) * height_shape + \
        (height_shape if row_stop % height_shape != 0 else 0)

    col_min = int(col_start // width_shape) * width_shape
    col_max = int(col_stop // width_shape) * width_shape + \
        (width_shape if col_stop % width_shape != 0 else 0)

    return Window(col_min, row_min, col_max - col_min, row_max - row_min)


def validate_length_value(instance, attribute, value):
    if value and value < 0:
        raise ValueError("Number of columns or rows must be non-negative")


_default = attr.Factory(lambda x: 0.0 if x is None else float(x))


@attr.s(slots=True)
class Window(object):
    """Windows are rectangular subsets of rasters.

    This class abstracts the 2-tuples mentioned in the module docstring
    and adds methods and new constructors.

    Attributes
    ----------
    col_off, row_off: float
        The offset for the window.
    width, height: float
        Lengths of the window.

    Previously the lengths were called 'num_cols' and 'num_rows' but
    this is a bit confusing in the new float precision world and the
    attributes have been changed. The originals are deprecated.
    """
    col_off = attr.ib(default=_default)
    row_off = attr.ib(default=_default)
    width = attr.ib(default=_default, validator=validate_length_value)
    height = attr.ib(default=_default, validator=validate_length_value)

    def __repr__(self):
        """Return a nicely formatted representation string"""
        return (
            "Window(col_off={self.col_off}, row_off={self.row_off}, "
            "width={self.width}, height={self.height})").format(
                self=self)

    def flatten(self):
        """A flattened form of the window.

        Returns
        -------
        col_off, row_off, width, height: float
            Window offsets and lengths.
        """
        return (self.col_off, self.row_off, self.width, self.height)

    def todict(self):
        """A mapping of attribute names and values.

        Returns
        -------
        dict
        """
        return collections.OrderedDict(
            col_off=self.col_off, row_off=self.row_off, width=self.width,
            height=self.height)

    def toranges(self):
        """Makes an equivalent pair of range tuples"""
        return (
            (self.row_off, self.row_off + self.height),
            (self.col_off, self.col_off + self.width))

    def toslices(self):
        """Slice objects for use as an ndarray indexer.

        Returns
        -------
        row_slice, col_slice: slice
            A pair of slices in row, column order
        """
        return tuple(slice(*rng) for rng in self.toranges())

    @property
    def num_cols(self):
        warnings.warn("use 'width' attribute instead",
                      RasterioDeprecationWarning)
        return self.width

    @property
    def num_rows(self):
        warnings.warn("use 'height' attribute instead",
                      RasterioDeprecationWarning, stacklevel=2)
        return self.height

    def __getitem__(self, index):
        """Provides backwards compatibility for clients using tuples"""
        warnings.warn("This usage is deprecated", RasterioDeprecationWarning)
        return self.toranges()[index]

    @classmethod
    def from_offlen(cls, col_off, row_off, num_cols, num_rows):
        """For backwards compatibility only"""
        warnings.warn("Use the class constructor instead of this method",
                      RasterioDeprecationWarning)
        return cls(col_off=col_off, row_off=row_off, width=num_cols,
                   height=num_rows)

    @classmethod
    def from_slices(cls, rows, cols, height=-1, width=-1, boundless=False):
        """Construct a Window from row and column slices or tuples.

        Parameters
        ----------
        rows, cols: slice or tuple
            Slices or 2-tuples containing start, stop indexes.
        height, width: float
            A shape to resolve relative values against.
        boundless: bool, optional
            Whether the inputs are bounded or bot.

        Returns
        -------
        Window
        """
        # Convert the rows indexing obj to offset and height.
        # Normalize to slices
        if not isinstance(rows, (tuple, slice)):
            raise WindowError("rows must be a tuple or slice")
        else:
            rows = slice(*rows) if isinstance(rows, tuple) else rows

        # Resolve the window height.
        # Fail if the stop value is relative or implicit and there
        # is no height context.
        if not boundless and (
                (rows.start is not None and rows.start < 0) or
                rows.stop is None or rows.stop < 0) and height < 0:
            raise WindowError(
                "A non-negative height is required")

        row_off = rows.start or 0.0
        if not boundless and row_off < 0:
            row_off += height

        row_stop = height if rows.stop is None else rows.stop
        if not boundless and row_stop < 0:
            row_stop += height

        num_rows = row_stop - row_off

        # Number of rows is never less than 0.
        num_rows = max(num_rows, 0.0)

        # Do the same for the cols indexing object.
        if not isinstance(cols, (tuple, slice)):
            raise WindowError("cols must be a tuple or slice")
        else:
            cols = slice(*cols) if isinstance(cols, tuple) else cols

        if not boundless and (
                (cols.start is not None and cols.start < 0) or
                cols.stop is None or cols.stop < 0) and width < 0:
            raise WindowError("A non-negative width is required")

        col_off = cols.start or 0.0
        if not boundless and col_off < 0:
            col_off += width

        col_stop = width if cols.stop is None else cols.stop
        if not boundless and col_stop < 0:
            col_stop += width

        num_cols = col_stop - col_off
        num_cols = max(num_cols, 0.0)

        return cls(col_off=col_off, row_off=row_off, width=num_cols,
                   height=num_rows)

    @classmethod
    def from_ranges(cls, rows, cols):
        """For backwards compatibility only"""
        warnings.warn("Use the from_slices class method instead",
                      RasterioDeprecationWarning)
        return cls.from_slices(rows, cols)

    def round_lengths(self, op='floor', pixel_precision=3):
        """Return a copy with width and height rounded.

        Lengths are rounded to the nearest whole number. The offsets
        are not changed.

        Parameters
        ----------
        op: str
            'ceil' or 'floor'
        pixel_precision: int
            Number of places of rounding precision.

        Returns
        -------
        Window
        """
        operator = getattr(math, op, None)
        if not operator:
            raise WindowError("operator must be 'ceil' or 'floor'")
        else:
            return Window(self.col_off, self.row_off,
                          operator(round(self.width, pixel_precision)),
                          operator(round(self.height, pixel_precision)))

    round_shape = round_lengths

    def round_offsets(self, op='floor', pixel_precision=3):
        """Return a copy with column and row offsets rounded.

        Offsets are rounded to the nearest whole number. The lengths
        are not changed.

        Parameters
        ----------
        op: str
            'ceil' or 'floor'
        pixel_precision: int
            Number of places of rounding precision.

        Returns
        -------
        Window
        """
        operator = getattr(math, op, None)
        if not operator:
            raise WindowError("operator must be 'ceil' or 'floor'")
        else:
            return Window(operator(round(self.col_off, pixel_precision)),
                          operator(round(self.row_off, pixel_precision)),
                          self.width, self.height)

    def crop(self, height, width):
        """Return a copy cropped to height and width"""
        return crop(self, height, width)

    def intersection(self, other):
        """Return the intersection of this window and another

        Parameters
        ----------

        other: Window
            Another window

        Returns
        -------
        Window
        """
        return intersection([self, other])

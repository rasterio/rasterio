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
import warnings

import attr
from affine import Affine
import numpy as np

from rasterio.compat import Iterable
from rasterio.errors import WindowError
from rasterio.transform import rowcol, guard_transform


PIXEL_PRECISION = 6


class WindowMethodsMixin(object):
    """Mixin providing methods for window-related calculations.
    These methods are wrappers for the functionality in
    `rasterio.windows` module.

    A subclass with this mixin MUST provide the following
    properties: `transform`, `height` and `width`
    """

    def window(self, left, bottom, right, top, precision=None):
        """Get the window corresponding to the bounding coordinates.

        The resulting window is not cropped to the row and column
        limits of the dataset.

        Parameters
        ----------
        left: float
            Left (west) bounding coordinate
        bottom: float
            Bottom (south) bounding coordinate
        right: float
            Right (east) bounding coordinate
        top: float
            Top (north) bounding coordinate
        precision: int, optional
            Number of decimal points of precision when computing inverse
            transform.

        Returns
        -------
        window: Window
        """
        transform = guard_transform(self.transform)

        return from_bounds(
            left, bottom, right, top, transform=transform,
            height=self.height, width=self.width, precision=precision)

    def window_transform(self, window):
        """Get the affine transform for a dataset window.

        Parameters
        ----------
        window: rasterio.windows.Window
            Dataset window

        Returns
        -------
        transform: Affine
            The affine transform matrix for the given window
        """

        gtransform = guard_transform(self.transform)
        return transform(window, gtransform)

    def window_bounds(self, window):
        """Get the bounds of a window

        Parameters
        ----------
        window: rasterio.windows.Window
            Dataset window

        Returns
        -------
        bounds : tuple
            x_min, y_min, x_max, y_max for the given window
        """

        transform = guard_transform(self.transform)
        return bounds(window, transform)


def iter_args(function):
    """Decorator to allow function to take either *args or
    a single iterable which gets expanded to *args.
    """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        if len(args) == 1 and isinstance(args[0], Iterable):
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
                height=None, width=None, precision=None):
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

    Returns
    -------
    Window
        A new Window
    """
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
    window: Window or tuple of (rows, cols).
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
        rows, cols = window
        return Window.from_slices(rows=rows, cols=cols, height=height,
                                  width=width, boundless=boundless)


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


@attr.s(slots=True,
        frozen=True)
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
    col_off = attr.ib()
    row_off = attr.ib()
    width = attr.ib(validator=validate_length_value)
    height = attr.ib(validator=validate_length_value)

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

    @classmethod
    def from_slices(cls, rows, cols, height=-1, width=-1, boundless=False):
        """Construct a Window from row and column slices or tuples / lists of
        start and stop indexes. Converts the rows and cols to offsets, height,
        and width.

        In general, indexes are defined relative to the upper left corner of
        the dataset: rows=(0, 10), cols=(0, 4) defines a window that is 4
        columns wide and 10 rows high starting from the upper left.

        Start indexes may be `None` and will default to 0.
        Stop indexes may be `None` and will default to width or height, which
        must be provided in this case.

        Negative start indexes are evaluated relative to the lower right of the
        dataset: rows=(-2, None), cols=(-2, None) defines a window that is 2
        rows high and 2 columns wide starting from the bottom right.

        Parameters
        ----------
        rows, cols: slice, tuple, or list
            Slices or 2 element tuples/lists containing start, stop indexes.
        height, width: float
            A shape to resolve relative values against. Only used when a start
            or stop index is negative or a stop index is None.
        boundless: bool, optional
            Whether the inputs are bounded (default) or not.

        Returns
        -------
        Window
        """

        # Normalize to slices
        if isinstance(rows, (tuple, list)):
            if len(rows) != 2:
                raise WindowError("rows must have a start and stop index")
            rows = slice(*rows)

        elif not isinstance(rows, slice):
            raise WindowError("rows must be a slice, tuple, or list")

        if isinstance(cols, (tuple, list)):
            if len(cols) != 2:
                raise WindowError("cols must have a start and stop index")
            cols = slice(*cols)

        elif not isinstance(cols, slice):
            raise WindowError("cols must be a slice, tuple, or list")

        # Height and width are required if stop indices are implicit
        if rows.stop is None and height < 0:
            raise WindowError("height is required if row stop index is None")

        if cols.stop is None and width < 0:
            raise WindowError("width is required if col stop index is None")

        # Convert implicit indices to offsets, height, and width
        row_off = 0.0 if rows.start is None else rows.start
        row_stop = height if rows.stop is None else rows.stop

        col_off = 0.0 if cols.start is None else cols.start
        col_stop = width if cols.stop is None else cols.stop

        if not boundless:
            if (row_off < 0 or row_stop < 0):
                if height < 0:
                    raise WindowError("height is required when providing "
                                      "negative indexes")

                if row_off < 0:
                    row_off += height

                if row_stop < 0:
                    row_stop += height

            if (col_off < 0 or col_stop < 0):
                if width < 0:
                    raise WindowError("width is required when providing "
                                      "negative indexes")

                if col_off < 0:
                    col_off += width

                if col_stop < 0:
                    col_stop += width

        num_cols = max(col_stop - col_off, 0.0)
        num_rows = max(row_stop - row_off, 0.0)

        return cls(col_off=col_off, row_off=row_off, width=num_cols,
                   height=num_rows)

    def round_lengths(self, op='floor', pixel_precision=None):
        """Return a copy with width and height rounded.

        Lengths are rounded to the preceding (floor) or succeeding (ceil)
        whole number. The offsets are not changed.

        Parameters
        ----------
        op: str
            'ceil' or 'floor'
        pixel_precision: int, optional (default: None)
            Number of places of rounding precision.

        Returns
        -------
        Window
        """
        operator = getattr(math, op, None)
        if not operator:
            raise WindowError("operator must be 'ceil' or 'floor'")
        else:
            return Window(
                self.col_off, self.row_off,
                operator(round(self.width, pixel_precision) if
                         pixel_precision is not None else self.width),
                operator(round(self.height, pixel_precision) if
                         pixel_precision is not None else self.height))

    round_shape = round_lengths

    def round_offsets(self, op='floor', pixel_precision=None):
        """Return a copy with column and row offsets rounded.

        Offsets are rounded to the preceding (floor) or succeeding (ceil)
        whole number. The lengths are not changed.

        Parameters
        ----------
        op : str
            'ceil' or 'floor'
        pixel_precision : int, optional (default: None)
            Number of places of rounding precision.

        Returns
        -------
        Window
        """
        operator = getattr(math, op, None)
        if not operator:
            raise WindowError("operator must be 'ceil' or 'floor'")
        else:
            return Window(
                operator(round(self.col_off, pixel_precision) if
                         pixel_precision is not None else self.col_off),
                operator(round(self.row_off, pixel_precision) if
                         pixel_precision is not None else self.row_off),
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

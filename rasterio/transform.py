"""Geospatial transforms"""

from collections.abc import Iterable
import math
import sys

from affine import Affine
import numpy as np

from rasterio._transform import _transform_from_gcps

IDENTITY = Affine.identity()
GDAL_IDENTITY = IDENTITY.to_gdal()


class TransformMethodsMixin(object):
    """Mixin providing methods for calculations related
    to transforming between rows and columns of the raster
    array and the coordinates.

    These methods are wrappers for the functionality in
    `rasterio.transform` module.

    A subclass with this mixin MUST provide a `transform`
    property.
    """

    def xy(self, row, col, offset="center"):
        """Returns the coordinates ``(x, y)`` of a pixel at `row` and `col`.
        The pixel's center is returned by default, but a corner can be returned
        by setting `offset` to one of `ul, ur, ll, lr`.

        Parameters
        ----------
        row : int
            Pixel row.
        col : int
            Pixel column.
        offset : str, optional
            Determines if the returned coordinates are for the center of the
            pixel or for a corner.

        Returns
        -------
        tuple
            ``(x, y)``
        """
        return xy(self.transform, row, col, offset=offset)

    def index(self, x, y, op=math.floor, precision=None):
        """
        Returns the (row, col) index of the pixel containing (x, y) given a
        coordinate reference system.

        Use an epsilon, magnitude determined by the precision parameter
        and sign determined by the op function:
            positive for floor, negative for ceil.

        Parameters
        ----------
        x : float
            x value in coordinate reference system
        y : float
            y value in coordinate reference system
        op : function, optional (default: math.floor)
            Function to convert fractional pixels to whole numbers (floor,
            ceiling, round)
        precision : int, optional (default: None)
            Decimal places of precision in indexing, as in `round()`.

        Returns
        -------
        tuple
            (row index, col index)
        """
        return rowcol(self.transform, x, y, op=op, precision=precision)


def tastes_like_gdal(seq):
    """Return True if `seq` matches the GDAL geotransform pattern."""
    return tuple(seq) == GDAL_IDENTITY or (
        seq[2] == seq[4] == 0.0 and seq[1] > 0 and seq[5] < 0)


def guard_transform(transform):
    """Return an Affine transformation instance."""
    if not isinstance(transform, Affine):
        if tastes_like_gdal(transform):
            raise TypeError(
                "GDAL-style transforms have been deprecated.  This "
                "exception will be raised for a period of time to highlight "
                "potentially confusing errors, but will eventually be removed.")
        else:
            transform = Affine(*transform)
    return transform


def from_origin(west, north, xsize, ysize):
    """Return an Affine transformation given upper left and pixel sizes.

    Return an Affine transformation for a georeferenced raster given
    the coordinates of its upper left corner `west`, `north` and pixel
    sizes `xsize`, `ysize`.
    """
    return Affine.translation(west, north) * Affine.scale(xsize, -ysize)


def from_bounds(west, south, east, north, width, height):
    """Return an Affine transformation given bounds, width and height.

    Return an Affine transformation for a georeferenced raster given
    its bounds `west`, `south`, `east`, `north` and its `width` and
    `height` in number of pixels.
    """
    return Affine.translation(west, north) * Affine.scale(
        (east - west) / width, (south - north) / height)


def array_bounds(height, width, transform):
    """Return the bounds of an array given height, width, and a transform.

    Return the `west, south, east, north` bounds of an array given
    its height, width, and an affine transform.
    """
    w, n = transform.xoff, transform.yoff
    e, s = transform * (width, height)
    return w, s, e, n


def xy(transform, rows, cols, offset='center'):
    """Returns the x and y coordinates of pixels at `rows` and `cols`.
    The pixel's center is returned by default, but a corner can be returned
    by setting `offset` to one of `ul, ur, ll, lr`.

    Parameters
    ----------
    transform : affine.Affine
        Transformation from pixel coordinates to coordinate reference system.
    rows : list or int
        Pixel rows.
    cols : list or int
        Pixel columns.
    offset : str, optional
        Determines if the returned coordinates are for the center of the
        pixel or for a corner.

    Returns
    -------
    xs : list
        x coordinates in coordinate reference system
    ys : list
        y coordinates in coordinate reference system
    """
    if not isinstance(cols, Iterable):
        cols = [cols]
    if not isinstance(rows, Iterable):
        rows = [rows]

    if offset == 'center':
        coff, roff = (0.5, 0.5)
    elif offset == 'ul':
        coff, roff = (0, 0)
    elif offset == 'ur':
        coff, roff = (1, 0)
    elif offset == 'll':
        coff, roff = (0, 1)
    elif offset == 'lr':
        coff, roff = (1, 1)
    else:
        raise ValueError("Invalid offset")

    T = transform * transform.translation(coff, roff)
    xs, ys = zip(*(T * pt for pt in zip(cols, rows)))

    if len(xs) == 1:
        return xs[0], ys[0]
    return xs, ys


def rowcol(transform, xs, ys, op=math.floor, precision=None):
    """
    Returns the rows and cols of the pixels containing (x, y) given a
    coordinate reference system.

    Use an epsilon, magnitude determined by the precision parameter
    and sign determined by the op function:
        positive for floor, negative for ceil.

    Parameters
    ----------
    transform : Affine
        Coefficients mapping pixel coordinates to coordinate reference system.
    xs : list or float
        x values in coordinate reference system
    ys : list or float
        y values in coordinate reference system
    op : function
        Function to convert fractional pixels to whole numbers (floor, ceiling,
        round)
    precision : int or float, optional
        An integer number of decimal points of precision when computing
        inverse transform, or an absolute float precision.

    Returns
    -------
    rows : list of ints
        list of row indices
    cols : list of ints
        list of column indices
    """

    if not isinstance(xs, Iterable):
        xs = [xs]
    if not isinstance(ys, Iterable):
        ys = [ys]

    if precision is None:
        eps = sys.float_info.epsilon
    elif isinstance(precision, int):
        eps = 10.0 ** -precision
    else:
        eps = precision

    # If op rounds up, switch the sign of eps.
    if op(0.1) >= 1:
        eps = -eps

    invtransform = ~transform

    cols, rows = zip(*(invtransform * (x + eps, y - eps) for x, y in zip(xs, ys)))
    cols = list(map(op, cols))
    rows = list(map(op, rows))

    if len(cols) == 1:
        return rows[0], cols[0]
    return rows, cols


def from_gcps(gcps):
    """Make an Affine transform from ground control points.

    Parameters
    ----------
    gcps : sequence of GroundControlPoint
        Such as the first item of a dataset's `gcps` property.

    Returns
    -------
    Affine

    """
    return Affine.from_gdal(*_transform_from_gcps(gcps))


def affine_to_ndarray(transform):
    """
    Create ndarray of Affine object

    Parameters
    ----------
    transform: ndarray (Affine)

    Returns
    -------
    - : ndarray (3x3)
        The equivalent ndarray
    """
    return np.fromiter(transform, dtype='float64').reshape(3, 3)


def translate_ndarray(transform, xoff, yoff):
    """
    Translate ndarray representing an affine transformation

    Parameters
    ----------
    transform: ndarray (3x3)
    xoff: number
    yoff: number

    Returns
    -------
    translated: ndarray
        A transform with the translation applied.
    """
    translated = transform.copy()
    translated[:, 2] = transform @ np.array([xoff, yoff, 1])
    return translated

def rowcol_np(transform, xs, ys, op='floor', precision=None):
    """
    Returns the rows and cols of the pixels containing (x, y) given a
    coordinate reference system.

    Use an epsilon, magnitude determined by the precision parameter
    and sign determined by the op function:
        positive for floor, negative for ceil.

    This numpy based version is optimized for applying the transform
    on many points.

    Parameters
    ----------
    transform : ndarray
        Coefficients mapping pixel coordinates to coordinate reference system.
    xs : Sequence
        x values in coordinate reference system
    ys : Sequence
        y values in coordinate reference system
    op : function (one of 'floor', 'ceil', 'round')
        Function to convert fractional pixels to whole numbers (floor, ceiling,
        round)
    precision : int or float, optional
        An integer number of decimal points of precision when computing
        inverse transform, or an absolute float precision.

    Returns
    -------
    rows : ndarray of ints
        array of row indices
    cols : ndarray of ints
        array of column indices
    """
    if len(xs) != len(ys):
        raise ValueError("xs and ys must be the same length.")

    if precision is None:
        eps = np.finfo('float64').eps
    elif isinstance(precision, int):
        eps = 10.0 ** -precision
    else:
        eps = precision

    if op in {'floor', 'ceil', 'round'}:
        operator = getattr(np, op)
    else:
        raise ValueError("Invalid op")

    # If op rounds up, switch the sign of eps.
    if operator(0.1) >= 1:
        eps = -eps

    invtransform = np.linalg.inv(transform)
    coords = np.empty((3, len(xs)), dtype='float64')
    coords[0] = xs
    coords[0] += eps
    coords[1] = ys
    coords[1] -= eps
    coords[2] = 1

    np.matmul(invtransform, coords, out=coords)
    operator(coords, out=coords)

    return coords[1], coords[0]

def xy_np(transform, rows, cols, offset='center'):
    """Returns the x and y coordinates of pixels at `rows` and `cols`.
    The pixel's center is returned by default, but a corner can be returned
    by setting `offset` to one of `ul, ur, ll, lr`.

    This numpy based version is optimized for applying the transform
    on many points.

    Parameters
    ----------
    transform : ndarray
        Transformation from pixel coordinates to coordinate reference system.
    rows : Sequence
        Pixel rows.
    cols : Sequence
        Pixel columns.
    offset : str, optional
        Determines if the returned coordinates are for the center of the
        pixel or for a corner.

    Returns
    -------
    xs : ndarray
        x coordinates in coordinate reference system
    ys : ndarray
        y coordinates in coordinate reference system
    """
    if len(cols) != len(rows):
        raise ValueError

    if offset == 'center':
        coff, roff = (0.5, 0.5)
    elif offset == 'ul':
        coff, roff = (0, 0)
    elif offset == 'ur':
        coff, roff = (1, 0)
    elif offset == 'll':
        coff, roff = (0, 1)
    elif offset == 'lr':
        coff, roff = (1, 1)
    else:
        raise ValueError("Invalid offset")

    coords = np.empty((3, len(cols)), dtype='float64')
    coords[0] = rows
    coords[1] = cols
    coords[2] = 1

    np.matmul(translate_ndarray(transform, coff, roff), coords, out=coords)
    return coords[0], coords[1]

def array_bounds_ndarray(height, width, transform):
    """Return the bounds of an array given height, width, and a transform.

    Return the `west, south, east, north` bounds of an array given
    its height, width, and an affine transform.
    """
    w, n = transform[:2, 2]
    e, s = transform @ np.array([width, height])
    return w, s, e, n

def from_bounds_ndarray(west, south, east, north, width, height):
    """Return an Affine transformation given bounds, width and height.

    Return an Affine transformation for a georeferenced raster given
    its bounds `west`, `south`, `east`, `north` and its `width` and
    `height` in number of pixels.
    """
    transform = np.eye(3, 3, dtype='float64')
    transform[:2, 2] = west, north
    transform[0, 0] = (east - west) / width
    transform[1, 1] = (south - north) / height
    return transform

def from_origin_ndarray(west, north, xsize, ysize):
    """Return an Affine transformation given upper left and pixel sizes.

    Return an Affine transformation for a georeferenced raster given
    the coordinates of its upper left corner `west`, `north` and pixel
    sizes `xsize`, `ysize`.
    """
    transform = np.eye(3, 3, dtype='float64')
    transform[:2, 2] = west, north
    transform[0, 0] = xsize
    transform[1, 1] = -ysize
    return transform

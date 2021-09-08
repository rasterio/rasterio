"""Geospatial transforms"""

from collections.abc import Iterable
import math
import sys

from affine import Affine

from rasterio.errors import TransformError
from rasterio._transform import _transform_from_gcps

IDENTITY = Affine.identity()
GDAL_IDENTITY = IDENTITY.to_gdal()


def wrap_noniterable(x):
    if isinstance(x, Iterable):
        return x
    else:
        return [x]

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
    """Get the x and y coordinates of pixels at `rows` and `cols`.

    The pixel's center is returned by default, but a corner can be returned
    by setting `offset` to one of `ul, ur, ll, lr`.

    Parameters
    ----------
    transform : affine.Affine
        Transformation from pixel coordinates to coordinate reference system.
    rows : int or sequence of ints
        Pixel rows.
    cols : int or sequence of ints
        Pixel columns.
    offset : str, optional
        Determines if the returned coordinates are for the center of the
        pixel or for a corner.

    Returns
    -------
    xs : float or list of floats
        x coordinates in coordinate reference system
    ys : float or list of floats
        y coordinates in coordinate reference system

    """
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
        raise TransformError("Invalid offset")

    adjusted_transform = transform * Affine.translation(coff, roff)

    cols_rows = zip(wrap_noniterable(cols), wrap_noniterable(rows))
    try:
        xs, ys = zip(*(adjusted_transform * (col, row) for col, row in cols_rows))
        xs = list(xs)
        ys = list(ys)
        if not isinstance(rows, Iterable) and not isinstance(cols, Iterable):
            return xs[0], ys[0]
        else:
            return xs, ys
    except TypeError as exc:
        raise TransformError("Invalid inputs") from exc


def rowcol(transform, xs, ys, op=math.floor, precision=None):
    """The rows and cols of the pixels containing (x, y).

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
    rows : list or int
        Row indices.
    cols : list or int
        Column indices.

    """
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

    xs_ys = zip(wrap_noniterable(xs), wrap_noniterable(ys))
    try:
        fcols, frows = zip(*(invtransform * (x + eps, y + eps) for x, y in xs_ys))
        fcols = list(map(op, fcols))
        frows = list(map(op, frows))
        if not isinstance(xs, Iterable) and not isinstance(ys, Iterable):
            return frows[0], fcols[0]
        else:
            return frows, fcols
    except TypeError as exc:
        raise TransformError("Invalid inputs") from exc


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

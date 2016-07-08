"""Geospatial transforms"""


from __future__ import division
import math

from affine import Affine


IDENTITY = Affine.identity()
GDAL_IDENTITY = IDENTITY.to_gdal()


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


def xy(row, col, transform, offset='center'):
    """Returns the coordinates ``(x, y)`` of a pixel at `row` and `col`.
    The pixel's center is returned by default, but a corner can be returned
    by setting `offset` to one of `ul, ur, ll, lr`.

    Parameters
    ----------
    row : int
        Pixel row.
    col : int
        Pixel column.
    transform : affine.Affine
        Transformation from pixel coordinates to coordinate reference system.
    offset : str, optional
        Determines if the returned coordinates are for the center of the
        pixel or for a corner.

    Returns
    -------
    tuple
        ``(x, y)``
    """

    cr = (col, row)

    if offset == 'center':
        return transform * transform.translation(0.5, 0.5) * cr
    elif offset == 'ul':
        return transform * cr
    elif offset == 'ur':
        return transform * transform.translation(1, 0) * cr
    elif offset == 'll':
        return transform * transform.translation(0, 1) * cr
    elif offset == 'lr':
        return transform * transform.translation(1, 1) * cr
    else:
        raise ValueError("Invalid offset")


def get_index(x, y, transform, op=math.floor, precision=6):
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
    transform : Affine
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

    eps = 10.0**-precision * (1.0 - 2.0*op(0.1))
    fcol, frow = ~transform * (x + eps, y - eps)
    col = int(op(fcol))
    row = int(op(frow))
    return row, col

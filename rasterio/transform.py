"""Geospatial transforms"""

from __future__ import absolute_import
from __future__ import division

import warnings

from affine import Affine


IDENTITY = Affine.identity()


def tastes_like_gdal(seq):
    """Return True if `seq` matches the GDAL geotransform pattern."""
    return seq[2] == seq[4] == 0.0 and seq[1] > 0 and seq[5] < 0


def guard_transform(transform):
    """Return an Affine transformation instance."""
    if not isinstance(transform, Affine):
        if tastes_like_gdal(transform):
            warnings.warn(
                "GDAL-style transforms are deprecated and will not "
                "be supported in Rasterio 1.0.",
                FutureWarning,
                stacklevel=2)
            transform = Affine.from_gdal(*transform)
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

    rc = (row, col)

    if offset == 'center':
        return transform * transform.translation(0.5, 0.5) * rc
    elif offset == 'ul':
        return transform * rc
    elif offset == 'ur':
        return transform * transform.translation(1, 0) * rc
    elif offset == 'll':
        return transform * transform.translation(0, 1) * rc
    elif offset == 'lr':
        return transform * transform.translation(1, 1) * rc
    else:
        raise ValueError("Invalid offset")

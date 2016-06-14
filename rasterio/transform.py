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
            raise ValueError(
                "GDAL-style transforms have been deprecated in 1.0.  This "
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

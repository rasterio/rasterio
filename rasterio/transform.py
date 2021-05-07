"""Geospatial transforms"""

from collections.abc import Iterable
import math
import sys
from pathlib import Path

from affine import Affine

import rasterio._loading
with rasterio._loading.add_gdal_dll_directories():
    import rasterio
    from rasterio.env import env_ctx_if_needed
    from rasterio._transform import (
        _transform_from_gcps,
        RPCTransformerBase,
        GCPTransformerBase
    )
    from rasterio.enums import TransformDirection

IDENTITY = Affine.identity()
GDAL_IDENTITY = IDENTITY.to_gdal()


class TransformMethodsMixin:
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

    xs = []
    ys = []
    T = transform * transform.translation(coff, roff)
    for pt in zip(cols, rows):
        x, y = T * pt
        xs.append(x)
        ys.append(y)

    if len(xs) == 1:
        # xs and ys will always have the same length
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

    rows = []
    cols = []
    for x, y in zip(xs, ys):
        fcol, frow = invtransform * (x + eps, y + eps)
        cols.append(op(fcol))
        rows.append(op(frow))

    if len(cols) == 1:
        # rows and cols will always have the same length
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

class TransformerBase:
    """
    Generic GDAL transformer base class
    """
    def close(self):
        raise NotImplementedError

    def __enter__(self):
        self._env = env_ctx_if_needed()
        self._env.__enter__()
        return self

    def __exit__(self, type, value, traceback):
        self.close()
        self._env.__exit__()
    
    def rowcol(self, xs, ys, zs=None):
        """
        Returns rows and cols coordinates given geographic coordinates

        Parameters
        ----------
        xs, ys : float or list of float
            Geographic coordinates
        zs : float or list of float, optional
            Geodetic height

        Raises
        ------
        ValueError
            If input coordinates are not all equal length

        Returns
        -------
            tuple of float or list of float
        """
        if not isinstance(xs, Iterable):
            xs = [xs]
        if not isinstance(ys, Iterable):
            ys = [ys]
        if zs is None:
            zs = [0] * len(xs)
        if len(set((len(xs), len(ys), len(zs)))) > 1:
            raise ValueError("Input coordinate arrays should be of equal length")

        new_rows, new_cols =  self._transform(xs, ys, zs, transform_direction=TransformDirection.forward)

        if len(new_rows) == 1:
            return (new_rows[0], new_cols[0])
        return (new_rows, new_cols)

    def xy(self, rows, cols, zs=None):
        """
        Returns geographic coordinates given dataset rows and cols coordinates

        Parameters
        ----------
        rows, cols : float or list of float
            Image pixel coordinates
        zs : float or list of float, optional
            Geodetic height
        Raises
        ------
        ValueError
            If input coordinates are not all equal length

        Returns
        -------
            tuple of float or list of float
        """

        if not isinstance(rows, Iterable):
            rows = [rows]
        if not isinstance(cols, Iterable):
            cols = [cols]
        if zs is None:
            zs = [0] * len(rows)
        if len(set((len(rows), len(cols), len(zs)))) > 1:
            raise ValueError("Input coordinate arrays should be of equal length")

        new_ys, new_xs =  self._transform(rows, cols, zs, transform_direction=TransformDirection.reverse)

        if len(new_ys) == 1:
            return (new_ys[0], new_xs[0])
        
        return (new_ys, new_xs)


class AffineTransformer(TransformerBase):
    def __init__(self, affine_transform):
        pass

    def close(self):
        pass
    
    def _transform(xs, ys, zs, transform_direction):
        

class RPCTransformer(RPCTransformerBase, TransformerBase):
    def __init__(self, rpcs, **kwargs):
        super().__init__(rpcs, **kwargs)

    def __repr__(self):
        return "<{} RPCTransformer>".format(
            self.closed and 'closed' or 'open')

    @classmethod
    def from_dataset(cls, dataset, **kwargs):
        is_pathlike = False
        if isinstance(dataset, str) or isinstance(dataset, Path):
            dataset = rasterio.open(dataset)
            is_pathlike = True

        if not dataset.rpcs:
            raise ValueError("{} has no rpcs".format(dataset))

        if is_pathlike:
            dataset.close()

        return cls(dataset.rpcs, **kwargs)


class GCPTransformer(GCPTransformerBase, TransformerBase):
    def __init__(self, gcps):
        super().__init__(gcps)

    def __repr__(self):
        return "<{} GCPTransformer>".format(
            self.closed and 'closed' or 'open')

    @classmethod
    def from_dataset(cls, dataset):
        is_pathlike = False
        if isinstance(dataset, str) or isinstance(dataset, Path):
            dataset = rasterio.open(dataset)
            is_pathlike = True

        if not dataset.rpcs:
            raise ValueError("{} has no rpcs".format(dataset))

        if is_pathlike:
            dataset.close()

        return cls(dataset.rpcs)
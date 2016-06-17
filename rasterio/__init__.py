"""Rasterio"""

from __future__ import absolute_import

from collections import namedtuple
import logging
try:
    from logging import NullHandler
except ImportError:  # pragma: no cover
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass
import math
import warnings

from rasterio._base import (
    eval_window, window_shape, window_index, gdal_version,
    crop_window, get_index, get_window)
from rasterio.dtypes import (
    bool_, ubyte, uint8, uint16, int16, uint32, int32, float32, float64,
    complex_, check_dtype)
from rasterio.env import ensure_env, Env
from rasterio.coords import BoundingBox
from rasterio.compat import string_types
from rasterio.profiles import default_gtiff_profile
from rasterio.transform import Affine, guard_transform
from rasterio.vfs import parse_path
from rasterio import windows

# These modules are imported from the Cython extensions, but are also import
# here to help tools like cx_Freeze find them automatically
from rasterio import _err, coords, enums, vfs

# Classes in rasterio._io are imported below just before we need them.

__all__ = [
    'band', 'open', 'copy', 'pad']
__version__ = "1.0.dev1"
__gdal_version__ = gdal_version()

# Rasterio attaches NullHandler to the 'rasterio' logger and its
# descendents. See
# https://docs.python.org/2/howto/logging.html#configuring-logging-for-a-library
# Applications must attach their own handlers in order to see messages.
# See rasterio/rio/main.py for an example.
log = logging.getLogger(__name__)
log.addHandler(NullHandler())


@ensure_env
def open(path, mode='r', driver=None, width=None, height=None,
         count=None, crs=None, transform=None, dtype=None, nodata=None,
         **kwargs):
    """Open file at ``path`` in ``mode`` 'r' (read), 'r+' (read and
    write), or 'w' (write) and return a dataset Reader or Updater
    object.

    In write mode, a driver name such as "GTiff" or "JPEG" (see GDAL
    docs or ``gdal_translate --help`` on the command line),
    ``width`` (number of pixels per line) and ``height`` (number of
    lines), the ``count`` number of bands in the new file must be
    specified.  Additionally, the data type for bands such as
    ``rasterio.ubyte`` for 8-bit bands or ``rasterio.uint16`` for
    16-bit bands must be specified using the ``dtype`` argument.

    Parameters
    ----------
    mode: string
        "r" (read), "r+" (read/write), or "w" (write)
    driver: string
        driver code specifying the format name (e.g. "GTiff" or
        "JPEG"). See GDAL docs at
        http://www.gdal.org/formats_list.html (optional, required
        for writing).
    width: int
        number of pixels per line
        (optional, required for write)
    height: int
        number of lines
        (optional, required for write)
    count: int > 0
        number of bands
        (optional, required for write)
    dtype: rasterio.dtype
        the data type for bands such as ``rasterio.ubyte`` for
        8-bit bands or ``rasterio.uint16`` for 16-bit bands
        (optional, required for write)
    crs: dict or string
        Coordinate reference system
        (optional, recommended for write)
    transform: Affine instance
        Affine transformation mapping the pixel space to geographic
        space (optional, recommended for writing).
    nodata: number
        Defines pixel value to be interpreted as null/nodata
        (optional, recommended for write)

    Returns
    -------
    A ``DatasetReader`` or ``DatasetUpdater`` object.

    Notes
    -----
    In write mode, you must specify at least ``width``, ``height``,
    ``count`` and ``dtype``.

    A coordinate reference system for raster datasets in write mode
    can be defined by the ``crs`` argument. It takes Proj4 style
    mappings like

    .. code::

      {'proj': 'longlat', 'ellps': 'WGS84', 'datum': 'WGS84',
       'no_defs': True}

    An affine transformation that maps ``col,row`` pixel coordinates
    to ``x,y`` coordinates in the coordinate reference system can be
    specified using the ``transform`` argument. The value should be
    an instance of ``affine.Affine``

    .. code:: python

        >>> from affine import Affine
        >>> transform = Affine(0.5, 0.0, -180.0, 0.0, -0.5, 90.0)

    These coefficients are shown in the figure below.

    .. code::

      | x |   | a  b  c | | c |
      | y | = | d  e  f | | r |
      | 1 |   | 0  0  1 | | 1 |

      a: rate of change of X with respect to increasing column,
         i.e. pixel width
      b: rotation, 0 if the raster is oriented "north up"
      c: X coordinate of the top left corner of the top left pixel
      d: rotation, 0 if the raster is oriented "north up"
      e: rate of change of Y with respect to increasing row,
         usually a negative number (i.e. -1 * pixel height) if
         north-up.
      f: Y coordinate of the top left corner of the top left pixel

    A 6-element sequence of the affine transformation matrix
    coefficients in ``c, a, b, f, d, e`` order, (i.e. GDAL
    geotransform order) will be accepted until 1.0 (deprecated).

    A virtual filesystem can be specified. The ``vfs`` parameter may
    be an Apache Commons VFS style string beginning with "zip://" or
    "tar://"". In this case, the ``path`` must be an absolute path
    within that container.

    """
    if not isinstance(path, string_types):
        raise TypeError("invalid path: {0!r}".format(path))
    if mode and not isinstance(mode, string_types):
        raise TypeError("invalid mode: {0!r}".format(mode))
    if driver and not isinstance(driver, string_types):
        raise TypeError("invalid driver: {0!r}".format(driver))
    if dtype and not check_dtype(dtype):
        raise TypeError("invalid dtype: {0!r}".format(dtype))
    if transform:
        transform = guard_transform(transform)
    elif 'affine' in kwargs:
        affine = kwargs.pop('affine')
        transform = guard_transform(affine)

    # Get AWS credentials if we're attempting to access a raster
    # on S3.
    pth, archive, scheme = parse_path(path)
    if scheme == 's3':
        Env().get_aws_credentials()
        log.debug("AWS credentials have been obtained")

    # Create dataset instances and pass the given env, which will
    # be taken over by the dataset's context manager if it is not
    # None.
    if mode == 'r':
        from rasterio._io import RasterReader
        s = RasterReader(path)
    elif mode == 'r+':
        from rasterio._io import writer
        s = writer(path, mode)
    elif mode == 'r-':
        from rasterio._base import DatasetReader
        s = DatasetReader(path)
    elif mode == 'w':
        from rasterio._io import writer
        s = writer(path, mode, driver=driver,
                   width=width, height=height, count=count,
                   crs=crs, transform=transform, dtype=dtype,
                   nodata=nodata, **kwargs)
    else:
        raise ValueError(
            "mode string must be one of 'r', 'r+', or 'w', not %s" % mode)
    s.start()
    return s


@ensure_env
def copy(src, dst, **kw):
    """Copy a source raster to a new destination with driver specific
    creation options.

    Parameters
    ----------
    src: string
        an existing raster file
    dst: string
        valid path to output file.

    Returns
    -------
    None

    Raises
    ------
    ValueError:
        If source path is not a valid Dataset

    Notes
    -----
    A ``driver`` keyword argument with value like 'GTiff' or 'JPEG' is
    used to control the output format.

    This is the one way to create write-once files like JPEGs.
    """
    from rasterio._copy import RasterCopier
    return RasterCopier()(src, dst, **kw)


def drivers(**kwargs):
    """Create a gdal environment with registered drivers and creation
    options.

    This function is deprecated; please use ``env.Env`` instead.

    Parameters
    ----------
    **kwargs:: keyword arguments
        Configuration options that define GDAL driver behavior

        See https://trac.osgeo.org/gdal/wiki/ConfigOptions

    Returns
    -------
    GDALEnv responsible for managing the environment.

    Notes
    -----
    Use as a context manager, ``with rasterio.drivers(): ...``
    """
    warnings.warn("Deprecated; Use env.Env instead", DeprecationWarning)
    return Env(**kwargs)


Band = namedtuple('Band', ['ds', 'bidx', 'dtype', 'shape'])

def band(ds, bidx):
    """Wraps a dataset and a band index up as a 'Band'

    Parameters
    ----------
    ds: rasterio.RasterReader
        Open rasterio dataset
    bidx: int
        Band number, index starting at 1

    Returns
    -------
    a rasterio.Band
    """
    return Band(
        ds,
        bidx,
        set(ds.dtypes).pop(),
        ds.shape)


def pad(array, transform, pad_width, mode=None, **kwargs):
    """pad array and adjust affine transform matrix.

    Parameters
    ----------
    array: ndarray
        Numpy ndarray, for best results a 2D array
    transform: Affine transform
        transform object mapping pixel space to coordinates
    pad_width: int
        number of pixels to pad array on all four
    mode: str or function
        define the method for determining padded values

    Returns
    -------
    (array, transform): tuple
        Tuple of new array and affine transform

    Notes
    -----
    See numpy docs for details on mode and other kwargs:
    http://docs.scipy.org/doc/numpy-1.10.0/reference/generated/numpy.pad.html
    """
    import numpy as np
    transform = guard_transform(transform)
    padded_array = np.pad(array, pad_width, mode, **kwargs)
    padded_trans = list(transform)
    padded_trans[2] -= pad_width * padded_trans[0]
    padded_trans[5] -= pad_width * padded_trans[4]
    return padded_array, Affine(*padded_trans[:6])


def get_data_window(arr, nodata=None):
    warnings.warn("Deprecated; Use rasterio.windows instead", DeprecationWarning)
    return windows.get_data_window(arr, nodata)


def window_union(data):
    warnings.warn("Deprecated; Use rasterio.windows instead", DeprecationWarning)
    return windows.union(data)


def window_intersection(data):
    warnings.warn("Deprecated; Use rasterio.windows instead", DeprecationWarning)
    return windows.intersection(data)

def windows_intersect(data):
    warnings.warn("Deprecated; Use rasterio.windows instead", DeprecationWarning)
    return windows.intersect(data)



class GeoArray(object):
    def __init__(self, image, transform, crs=None):
        self.image = image
        self.transform = guard_transform(transform)  # must be an Affine
        self.crs = crs

    @property
    def bounds(self):
        a, b, c, d, e, f, _, _, _ = self.transform
        return BoundingBox(c, f + e * self.height, c + a * self.width, f)

    @property
    def count(self):
        if len(self.image.shape) == 2:
            return 1
        else:
            return self.image.shape[0]

    @property
    def dtypes(self):
        return (self.image.dtype.name, ) * self.count

    @property
    def height(self):
        return self.image.shape[-2]

    def index(self, x, y, op=math.floor, precision=6):
        """Returns the (row, col) index of the pixel containing (x, y)."""
        return get_index(x, y, self.transform, op=op, precision=precision)

    @property
    def shape(self):
        return self.image.shape[-2:]

    @property
    def res(self):
        """Returns the (width, height) of pixels in the units of its
        coordinate reference system."""
        a, b, c, d, e, f, _, _, _ = self.transform
        if b == d == 0:
            return a, -e
        else:
            return math.sqrt(a * a + d * d), math.sqrt(b * b + e * e)

    def ul(self, row, col):
        """Returns the coordinates (x, y) of the upper left corner of a
        pixel at `row` and `col` in the units of the dataset's
        coordinate reference system.
        """
        a, b, c, d, e, f, _, _, _ = self.transform
        if col < 0:
            col += self.width
        if row < 0:
            row += self.height
        return c + a * col, f + e * row

    @property
    def width(self):
        return self.image.shape[-1]

    def window(self, left, bottom, right, top, boundless=False):
        """Returns the window corresponding to the world bounding box.
        If boundless is False, window is limited to extent of this dataset."""

        window = get_window(left, bottom, right, top, self.transform)
        if boundless:
            return window
        else:
            return crop_window(window, self.height, self.width)

    def window_bounds(self, window):
        """Returns the bounds of a window as x_min, y_min, x_max, y_max."""
        ((row_min, row_max), (col_min, col_max)) = window
        x_min, y_min = self.transform * (col_min, row_max)
        x_max, y_max = self.transform * (col_max, row_min)
        return x_min, y_min, x_max, y_max

    def window_transform(self, window):
        """Returns the affine transform for a dataset window."""
        (r, _), (c, _) = window
        return self.transform * Affine.translation(c or 0, r or 0)


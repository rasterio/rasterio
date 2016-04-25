"""Rasterio"""

from __future__ import absolute_import

from collections import namedtuple
import logging
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

from rasterio._base import (
    eval_window, window_shape, window_index, gdal_version)
from rasterio._drivers import driver_count, GDALEnv
from rasterio.dtypes import (
    bool_, ubyte, uint8, uint16, int16, uint32, int32, float32, float64,
    complex_)
from rasterio.five import string_types
from rasterio.profiles import default_gtiff_profile
from rasterio.transform import Affine, guard_transform
from rasterio import windows

# These modules are imported from the Cython extensions, but are also import
# here to help tools like cx_Freeze find them automatically
from rasterio import _err, coords, enums, vfs

# Classes in rasterio._io are imported below just before we need them.

__all__ = [
    'band', 'open', 'drivers', 'copy', 'pad']
__version__ = "0.34.0"
__gdal_version__ = gdal_version()

# Rasterio attaches NullHandler to the 'rasterio' logger and its
# descendents. See
# https://docs.python.org/2/howto/logging.html#configuring-logging-for-a-library
# Applications must attach their own handlers in order to see messages.
# See rasterio/rio/main.py for an example.
logging.getLogger(__name__).addHandler(NullHandler())


def open(
        path, mode='r',
        driver=None,
        width=None, height=None,
        count=None,
        crs=None, transform=None,
        dtype=None,
        nodata=None,
        **kwargs):
    """Open file at ``path`` in ``mode`` "r" (read), "r+" (read/write),
    or "w" (write) and return a ``Reader`` or ``Updater`` object.

    In write mode, a driver name such as "GTiff" or "JPEG" (see GDAL
    docs or ``gdal_translate --help`` on the command line), ``width``
    (number of pixels per line) and ``height`` (number of lines), the
    ``count`` number of bands in the new file must be specified.
    Additionally, the data type for bands such as ``rasterio.ubyte`` for
    8-bit bands or ``rasterio.uint16`` for 16-bit bands must be
    specified using the ``dtype`` argument.

    Parameters
    ----------
    mode: string
        "r" (read), "r+" (read/write), or "w" (write)
    driver: string
        driver code specifying the format name (e.g. "GTiff" or "JPEG")
        See GDAL docs at http://www.gdal.org/formats_list.html
        (optional, required for write)
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
        Affine transformation mapping the pixel space to geographic space
        (optional, recommended for write)
    nodata: number
        Defines pixel value to be interpreted as null/nodata
        (optional, recommended for write)

    Returns
    -------
    A ``Reader`` or ``Updater`` object.

    Notes
    -----
    In write mode, you must specify at least ``width``, ``height``, ``count``
    and ``dtype``.

    A coordinate reference system for raster datasets in write mode can
    be defined by the ``crs`` argument. It takes Proj4 style mappings
    like

    .. code::

      {'proj': 'longlat', 'ellps': 'WGS84', 'datum': 'WGS84', 'no_defs': True}

    An affine transformation that maps ``col,row`` pixel coordinates to
    ``x,y`` coordinates in the coordinate reference system can be
    specified using the ``transform`` argument. The value should be
    an instance of ``affine.Affine``

    .. code:: python

        >>> from affine import Affine
        >>> Affine(0.5, 0.0, -180.0, 0.0, -0.5, 90.0)

    These coefficients are shown in the figure below.

    .. code::

      | x |   | a  b  c | | c |
      | y | = | d  e  f | | r |
      | 1 |   | 0  0  1 | | 1 |

        a: rate of change of X with respect to increasing column, i.e.  pixel width
        b: rotation, 0 if the raster is oriented "north up"
        c: X coordinate of the top left corner of the top left pixel
        d: rotation, 0 if the raster is oriented "north up"
        e: rate of change of Y with respect to increasing row, usually
                a negative number (i.e. -1 * pixel height) if north-up.
        f: Y coordinate of the top left corner of the top left pixel

    A 6-element sequence of the affine transformation
    matrix coefficients in ``c, a, b, f, d, e`` order,
    (i.e. GDAL geotransform order) will be accepted until 1.0 (deprecated).

    A virtual filesystem can be specified. The ``vfs`` parameter may be
    an Apache Commons VFS style string beginning with "zip://" or
    "tar://"". In this case, the ``path`` must be an absolute path
    within that container.

    """
    if not isinstance(path, string_types):
        raise TypeError("invalid path: %r" % path)
    if mode and not isinstance(mode, string_types):
        raise TypeError("invalid mode: %r" % mode)
    if driver and not isinstance(driver, string_types):
        raise TypeError("invalid driver: %r" % driver)

    if transform:
        transform = guard_transform(transform)
    elif 'affine' in kwargs:
        affine = kwargs.pop('affine')
        transform = guard_transform(affine)

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
                   nodata=nodata,
                   **kwargs)
    else:
        raise ValueError(
            "mode string must be one of 'r', 'r+', or 'w', not %s" % mode)
    s.start()
    return s


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
    with drivers():
        return RasterCopier()(src, dst, **kw)


def drivers(**kwargs):
    """Create a gdal environment with registered drivers and
    creation options.

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
    return GDALEnv(**kwargs)


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
        ds.shape[1:])


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
    import numpy
    transform = guard_transform(transform)
    padded_array = numpy.pad(array, pad_width, mode, **kwargs)
    padded_trans = list(transform)
    padded_trans[2] -= pad_width * padded_trans[0]
    padded_trans[5] -= pad_width * padded_trans[4]
    return padded_array, Affine(*padded_trans[:6])


def get_data_window(arr, nodata=None):
    import warnings
    warnings.warn("Deprecated; Use rasterio.windows instead", DeprecationWarning)
    return windows.get_data_window(arr, nodata)


def window_union(data):
    import warnings
    warnings.warn("Deprecated; Use rasterio.windows instead", DeprecationWarning)
    return windows.union(data)


def window_intersection(data):
    import warnings
    warnings.warn("Deprecated; Use rasterio.windows instead", DeprecationWarning)
    return windows.intersection(data)

def windows_intersect(data):
    import warnings
    warnings.warn("Deprecated; Use rasterio.windows instead", DeprecationWarning)
    return windows.intersect(data)

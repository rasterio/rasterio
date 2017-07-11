"""Rasterio"""

from __future__ import absolute_import

from collections import namedtuple
from contextlib import contextmanager
import logging
import warnings
try:
    from logging import NullHandler
except ImportError:  # pragma: no cover
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

from rasterio._base import gdal_version
from rasterio._copy import copy
from rasterio.drivers import is_blacklisted
from rasterio.dtypes import (
    bool_, ubyte, uint8, uint16, int16, uint32, int32, float32, float64,
    complex_, check_dtype)
from rasterio.env import ensure_env, Env
from rasterio.errors import RasterioIOError
from rasterio.compat import string_types
from rasterio.io import (
    DatasetReader, get_writer_for_path, get_writer_for_driver, MemoryFile)
from rasterio.profiles import default_gtiff_profile
from rasterio.transform import Affine, guard_transform
from rasterio.vfs import parse_path
from rasterio import windows

# These modules are imported from the Cython extensions, but are also import
# here to help tools like cx_Freeze find them automatically
from rasterio import _err, coords, enums, vfs


# TODO deprecate or remove in factor of rasterio.windows.___
def eval_window(*args, **kwargs):
    from rasterio.windows import evaluate
    warnings.warn("Deprecated; Use rasterio.windows instead", FutureWarning)
    return evaluate(*args, **kwargs)


def window_shape(*args, **kwargs):
    from rasterio.windows import shape
    warnings.warn("Deprecated; Use rasterio.windows instead", FutureWarning)
    return shape(*args, **kwargs)


def window_index(*args, **kwargs):
    from rasterio.windows import window_index
    warnings.warn("Deprecated; Use rasterio.windows instead", FutureWarning)
    return window_index(*args, **kwargs)


__all__ = [
    'band', 'open', 'copy', 'pad']
__version__ = "1.0a10"
__gdal_version__ = gdal_version()

# Rasterio attaches NullHandler to the 'rasterio' logger and its
# descendents. See
# https://docs.python.org/2/howto/logging.html#configuring-logging-for-a-library
# Applications must attach their own handlers in order to see messages.
# See rasterio/rio/main.py for an example.
log = logging.getLogger(__name__)
log.addHandler(NullHandler())


def open(fp, mode='r', driver=None, width=None, height=None, count=None,
         crs=None, transform=None, dtype=None, nodata=None, **kwargs):
    """Open a dataset for reading or writing.

    The dataset may be located in a local file, in a resource located
    by a URL, or contained within a stream of bytes.

    To access a dataset within a zip file without unzipping the archive
    use an Apache VFS style zip:// URL like

      zip://path/to/archive.zip!path/to/example.tif

    In read ('r') or read/write ('r+') mode, no other keyword arguments
    are required: the attributes are supplied by the opened dataset.

    In write mode, a driver name such as "GTiff" or "JPEG" (see GDAL
    docs or ``gdal_translate --help`` on the command line), ``width``
    (number of pixels per line) and ``height`` (number of lines), the
    ``count`` number of bands in the new file must be specified.
    Additionally, the data type for bands such as ``rasterio.ubyte`` for
    8-bit bands or ``rasterio.uint16`` for 16-bit bands must be
    specified using the ``dtype`` argument.

    Parameters
    ----------
    fp: string or file
        A filename or URL, or file object opened in binary mode.
    mode: string
        "r" (read), "r+" (read/write), or "w" (write)
    driver: string
        Driver code specifying the format name (e.g. "GTiff" or
        "JPEG"). See GDAL docs at
        http://www.gdal.org/formats_list.html (optional, required
        for writing).
    width: int
        Number of pixels per line (optional, required for write).
    height: int
        Number of lines (optional, required for write).
    count: int > 0
        Count of bands (optional, required for write).
    dtype: rasterio.dtype
        the data type for bands such as ``rasterio.ubyte`` for
        8-bit bands or ``rasterio.uint16`` for 16-bit bands
        (optional, required for write)
    crs: dict or string
        Coordinate reference system (optional, recommended for write).
    transform: Affine instance
        Affine transformation mapping the pixel space to geographic
        space (optional, recommended for writing).
    nodata: number
        Defines pixel value to be interpreted as null/nodata
        (optional, recommended for write, will be broadcast to all
        bands).

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
    if not isinstance(fp, string_types):
        if not (hasattr(fp, 'read') or hasattr(fp, 'write')):
            raise TypeError("invalid path or file: {0!r}".format(fp))
    if mode and not isinstance(mode, string_types):
        raise TypeError("invalid mode: {0!r}".format(mode))
    if driver and not isinstance(driver, string_types):
        raise TypeError("invalid driver: {0!r}".format(driver))
    if dtype and not check_dtype(dtype):
        raise TypeError("invalid dtype: {0!r}".format(dtype))
    if nodata is not None:
        nodata = float(nodata)
    if 'affine' in kwargs:
        # DeprecationWarning's are ignored by default
        with warnings.catch_warnings():
            warnings.warn(
                "The 'affine' kwarg in rasterio.open() is deprecated at 1.0 "
                "and only remains to ease the transition.  Please switch to "
                "the 'transform' kwarg.  See "
                "https://github.com/mapbox/rasterio/issues/86 for details.",
                DeprecationWarning,
                stacklevel=2)

            if transform:
                warnings.warn(
                    "Found both 'affine' and 'transform' in rasterio.open() - "
                    "choosing 'transform'")
                transform = transform
            else:
                transform = kwargs.pop('affine')

    if transform:
        transform = guard_transform(transform)

    # Check driver/mode blacklist.
    if driver and is_blacklisted(driver, mode):
        raise RasterioIOError(
            "Blacklisted: file cannot be opened by "
            "driver '{0}' in '{1}' mode".format(driver, mode))

    # Special case for file object argument.
    if mode == 'r' and hasattr(fp, 'read'):

        @contextmanager
        def fp_reader(fp):
            memfile = MemoryFile(fp.read())
            dataset = memfile.open()
            try:
                yield dataset
            finally:
                dataset.close()
                memfile.close()

        return fp_reader(fp)

    elif mode == 'w' and hasattr(fp, 'write'):

        @contextmanager
        def fp_writer(fp):
            memfile = MemoryFile()
            dataset = memfile.open(driver=driver, width=width, height=height,
                                   count=count, crs=crs, transform=transform,
                                   dtype=dtype, nodata=nodata, **kwargs)
            try:
                yield dataset
            finally:
                dataset.close()
                memfile.seek(0)
                fp.write(memfile.read())
                memfile.close()

        return fp_writer(fp)

    else:
        # The 'normal' filename or URL path.
        _, _, scheme = parse_path(fp)

        with Env() as env:
            # Get AWS credentials only if we're attempting to access a
            # raster using the S3 scheme.
            if scheme == 's3':
                env.get_aws_credentials()
                log.debug("AWS credentials have been obtained")

            # Create dataset instances and pass the given env, which will
            # be taken over by the dataset's context manager if it is not
            # None.
            if mode == 'r':
                s = DatasetReader(fp)
            elif mode == 'r-':
                warnings.warn("'r-' mode is deprecated, use 'r'",
                              DeprecationWarning)
                s = DatasetReader(fp)
            elif mode == 'r+':
                s = get_writer_for_path(fp)(fp, mode)
            elif mode == 'w':
                s = get_writer_for_driver(driver)(fp, mode, driver=driver,
                                                  width=width, height=height,
                                                  count=count, crs=crs,
                                                  transform=transform,
                                                  dtype=dtype, nodata=nodata,
                                                  **kwargs)
            else:
                raise ValueError(
                    "mode must be one of 'r', 'r+', or 'w', not %s" % mode)
            s.start()
            return s


Band = namedtuple('Band', ['ds', 'bidx', 'dtype', 'shape'])


def band(ds, bidx):
    """A dataset and one or more of its bands

    Parameters
    ----------
    ds: dataset object
        An opened rasterio dataset object.
    bidx: int or sequence of ints
        Band number(s), index starting at 1.

    Returns
    -------
    rasterio.Band
    """
    return Band(ds, bidx, set(ds.dtypes).pop(), ds.shape)


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

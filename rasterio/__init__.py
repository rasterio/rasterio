"""Rasterio"""

from __future__ import absolute_import

from collections import namedtuple
from contextlib import contextmanager
import logging
import warnings

try:
    from pathlib import Path
except ImportError:  # pragma: no cover
    class Path:
        pass

try:
    from logging import NullHandler
except ImportError:  # pragma: no cover
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

from rasterio._base import gdal_version
from rasterio.drivers import is_blacklisted
from rasterio.dtypes import (
    bool_, ubyte, uint8, uint16, int16, uint32, int32, float32, float64,
    complex_, check_dtype)
from rasterio.env import ensure_env_with_credentials, Env
from rasterio.errors import RasterioIOError
from rasterio.compat import string_types
from rasterio.io import (
    DatasetReader, get_writer_for_path, get_writer_for_driver, MemoryFile)
from rasterio.profiles import default_gtiff_profile
from rasterio.transform import Affine, guard_transform
from rasterio.path import parse_path

# These modules are imported from the Cython extensions, but are also import
# here to help tools like cx_Freeze find them automatically
import rasterio._err
import rasterio.coords
import rasterio.enums
import rasterio.path


__all__ = ['band', 'open', 'pad', 'Env']
__version__ = "1.0.9"
__gdal_version__ = gdal_version()

# Rasterio attaches NullHandler to the 'rasterio' logger and its
# descendents. See
# https://docs.python.org/2/howto/logging.html#configuring-logging-for-a-library
# Applications must attach their own handlers in order to see messages.
# See rasterio/rio/main.py for an example.
log = logging.getLogger(__name__)
log.addHandler(NullHandler())


@ensure_env_with_credentials
def open(fp, mode='r', driver=None, width=None, height=None, count=None,
         crs=None, transform=None, dtype=None, nodata=None, sharing=True,
         **kwargs):
    """Open a dataset for reading or writing.

    The dataset may be located in a local file, in a resource located by
    a URL, or contained within a stream of bytes.

    In read ('r') or read/write ('r+') mode, no keyword arguments are
    required: these attributes are supplied by the opened dataset.

    In write ('w' or 'w+') mode, the driver, width, height, count, and dtype
    keywords are strictly required.

    Parameters
    ----------
    fp : str, file object or pathlib.Path object
        A filename or URL, a file object opened in binary ('rb') mode,
        or a Path object.
    mode : str, optional
        'r' (read, the default), 'r+' (read/write), 'w' (write), or
        'w+' (write/read).
    driver : str, optional
        A short format driver name (e.g. "GTiff" or "JPEG") or a list of
        such names (see GDAL docs at
        http://www.gdal.org/formats_list.html). In 'w' or 'w+' modes
        a single name is required. In 'r' or 'r+' modes the driver can
        usually be omitted. Registered drivers will be tried
        sequentially until a match is found. When multiple drivers are
        available for a format such as JPEG2000, one of them can be
        selected by using this keyword argument.
    width, height : int, optional
        The numbers of rows and columns of the raster dataset. Required
        in 'w' or 'w+' modes, they are ignored in 'r' or 'r+' modes.
    count : int, optional
        The count of dataset bands. Required in 'w' or 'w+' modes, it is
        ignored in 'r' or 'r+' modes.
    dtype : str or numpy dtype
        The data type for bands. For example: 'uint8' or
        ``rasterio.uint16``. Required in 'w' or 'w+' modes, it is
        ignored in 'r' or 'r+' modes.
    crs : str, dict, or CRS; optional
        The coordinate reference system. Required in 'w' or 'w+' modes,
        it is ignored in 'r' or 'r+' modes.
    transform : Affine instance, optional
        Affine transformation mapping the pixel space to geographic
        space. Required in 'w' or 'w+' modes, it is ignored in 'r' or
        'r+' modes.
    nodata : int, float, or nan; optional
        Defines the pixel value to be interpreted as not valid data.
        Required in 'w' or 'w+' modes, it is ignored in 'r' or 'r+'
        modes.
    sharing : bool
        A flag that allows sharing of dataset handles. Default is
        `True`. Should be set to `False` in a multithreaded:w program.
    kwargs : optional
        These are passed to format drivers as directives for creating or
        interpreting datasets. For example: in 'w' or 'w+' modes
        a `tiled=True` keyword argument will direct the GeoTIFF format
        driver to create a tiled, rather than striped, TIFF.

    Returns
    -------
    A ``DatasetReader`` or ``DatasetWriter`` object.

    Examples
    --------

    To open a GeoTIFF for reading using standard driver discovery and
    no directives:

    >>> import rasterio
    >>> with rasterio.open('example.tif') as dataset:
    ...     print(dataset.profile)

    To open a JPEG2000 using only the JP2OpenJPEG driver:

    >>> with rasterio.open(
    ...         'example.jp2', driver='JP2OpenJPEG') as dataset:
    ...     print(dataset.profile)

    To create a new 8-band, 16-bit unsigned, tiled, and LZW-compressed
    GeoTIFF with a global extent and 0.5 degree resolution:

    >>> from rasterio.transform import from_origin
    >>> with rasterio.open(
    ...         'example.tif', 'w', driver='GTiff', dtype='uint16',
    ...         width=720, height=360, count=8, crs='EPSG:4326',
    ...         transform=from_origin(-180.0, 90.0, 0.5, 0.5),
    ...         nodata=0, tiled=True, compress='lzw') as dataset:
    ...     dataset.write(...)
    """

    if not isinstance(fp, string_types):
        if not (hasattr(fp, 'read') or hasattr(fp, 'write') or isinstance(fp, Path)):
            raise TypeError("invalid path or file: {0!r}".format(fp))
    if mode and not isinstance(mode, string_types):
        raise TypeError("invalid mode: {0!r}".format(mode))
    if driver and not isinstance(driver, string_types):
        raise TypeError("invalid driver: {0!r}".format(driver))
    if dtype and not check_dtype(dtype):
        raise TypeError("invalid dtype: {0!r}".format(dtype))
    if nodata is not None:
        nodata = float(nodata)
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

    elif mode in ('w', 'w+') and hasattr(fp, 'write'):

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
        # If a pathlib.Path instance is given, convert it to a string path.
        if isinstance(fp, Path):
            fp = str(fp)

        # The 'normal' filename or URL path.
        path = parse_path(fp)

        # Create dataset instances and pass the given env, which will
        # be taken over by the dataset's context manager if it is not
        # None.
        if mode == 'r':
            s = DatasetReader(path, driver=driver, **kwargs)
        elif mode == 'r+':
            s = get_writer_for_path(path)(path, mode, driver=driver, **kwargs)
        elif mode.startswith("w"):
            s = get_writer_for_driver(driver)(path, mode, driver=driver,
                                              width=width, height=height,
                                              count=count, crs=crs,
                                              transform=transform,
                                              dtype=dtype, nodata=nodata,
                                              **kwargs)
        else:
            raise ValueError(
                "mode must be one of 'r', 'r+', or 'w', not %s" % mode)
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

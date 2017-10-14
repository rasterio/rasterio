"""Raster management."""


include "gdal.pxi"

import logging

from rasterio._io cimport DatasetReaderBase
from rasterio._err cimport exc_wrap_int, exc_wrap_pointer
from rasterio.env import ensure_env
from rasterio._err import CPLE_OpenFailedError
from rasterio.errors import DriverRegistrationError, RasterioIOError
from rasterio.vfs import parse_path, vsi_path


log = logging.getLogger(__name__)


@ensure_env
def exists(path):

    """Determine if a dataset exists by attempting to open it.

    Parameters
    ----------
    path : str
        Path to dataset.
    """

    cdef GDALDatasetH h_dataset = NULL

    gdal_path = vsi_path(*parse_path(path))
    b_path = gdal_path.encode('utf-8')
    cdef char* c_path = b_path

    with nogil:
        h_dataset = GDALOpenShared(c_path, <GDALAccess>0)

    try:
        h_dataset = exc_wrap_pointer(h_dataset)
        return True
    except CPLE_OpenFailedError:
        return False
    finally:
        GDALClose(h_dataset)


@ensure_env
def copy(src, dst, driver='GTiff', strict=True, **creation_options):

    """Copy a raster from a path or open dataset handle to a new destination
    with driver specific creation options.

    Parameters
    ----------
    src : str or rasterio.io.DatasetReader
        Path to source dataset or open dataset handle.
    dst : str
        Output dataset path.
    driver : str, optional
        Output driver name.
    strict : bool, optional.  Default: True
        Indicates if the output must be strictly equivalent or if the
        driver may adapt as necessary.
    creation_options : **kwargs, optional
        Creation options for output dataset.
    """

    cdef bint c_strictness
    cdef char **options = NULL
    cdef char* c_src_path = NULL
    cdef char* c_dst_path = NULL
    cdef GDALDatasetH src_dataset = NULL
    cdef GDALDatasetH dst_dataset = NULL
    cdef GDALDriverH drv = NULL

    # Creation options
    for key, val in creation_options.items():
        kb, vb = (x.upper().encode('utf-8') for x in (key, str(val)))
        options = CSLSetNameValue(
            options, <const char *>kb, <const char *>vb)
        log.debug("Option %r:%r", kb, vb)

    c_strictness = strict
    driverb = driver.encode('utf-8')
    drv = GDALGetDriverByName(driverb)
    if drv == NULL:
        raise DriverRegistrationError("Unrecognized driver: {}".format(driver))

    # Input is a path or GDAL connection string
    if isinstance(src, str):
        src = src.encode('utf-8')
        c_src_path = src
        with nogil:
            src_dataset = GDALOpenShared(c_src_path, <GDALAccess>0)
        src_dataset = exc_wrap_pointer(src_dataset)
        close_src = True
    # Input is something like 'rasterio.open()'
    else:
        src_dataset = (<DatasetReaderBase?>src).handle()
        close_src = False

    dst = dst.encode('utf-8')
    c_dst_path = dst
    try:
        with nogil:
            dst_dataset = GDALCreateCopy(
                drv, c_dst_path, src_dataset, c_strictness, options, NULL, NULL)
        dst_dataset = exc_wrap_pointer(dst_dataset)
    finally:
        CSLDestroy(options)
        if close_src:
            GDALClose(src_dataset)

        if dst_dataset != NULL:
            GDALClose(dst_dataset)


@ensure_env
def delete(path, driver=None):

    """Delete a GDAL dataset.

    Parameters
    ----------
    path : path
        Path to dataset to delete.
    driver : str or None, optional
        Name of driver to use for deleting.  Defaults to whatever GDAL
        determines is the appropriate driver.
    """

    cdef GDALDatasetH h_dataset = NULL
    cdef GDALDriverH h_driver = NULL

    gdal_path = vsi_path(*parse_path(path))
    b_path = gdal_path.encode('utf-8')
    cdef char* c_path = b_path

    if driver:
        b_driver = driver.encode('utf-8')
        h_driver = GDALGetDriverByName(b_driver)
        if h_driver == NULL:
            raise DriverRegistrationError(
                "Unrecognized driver: {}".format(driver))

    # Need to determine driver by opening the input dataset
    else:
        with nogil:
            h_dataset = GDALOpenShared(c_path, <GDALAccess>0)

        try:
            h_dataset = exc_wrap_pointer(h_dataset)
            h_driver = GDALGetDatasetDriver(h_dataset)
            if h_driver == NULL:
                raise DriverRegistrationError(
                    "Could not determine driver for: {}".format(path))
        except CPLE_OpenFailedError:
            raise RasterioIOError(
                "Invalid dataset: {}".format(path))
        finally:
            GDALClose(h_dataset)

    with nogil:
        res = GDALDeleteDataset(h_driver, c_path)
    exc_wrap_int(res)

"""Raster copying."""


include "gdal.pxi"

import logging

from rasterio._io cimport DatasetReaderBase
from rasterio._err cimport exc_wrap_pointer
from rasterio.env import ensure_env
from rasterio.errors import DriverRegistrationError


log = logging.getLogger(__name__)


@ensure_env
def copy(src, dst, driver='GTiff', strict=False, **creation_options):

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
    strict : bool, optional
        Indicates if the output must be strictly equivalent or if the
        driver may adapt as necessary.
    creation_options : **kwargs, optional
        Creation options for output dataset.
    """

    cdef char **options = NULL
    cdef GDALDatasetH src_dataset = NULL
    cdef GDALDatasetH dst_dataset = NULL
    cdef GDALDriverH drv = NULL

    # Creation options
    for key, val in creation_options.items():
        kb, vb = (x.upper().encode('utf-8') for x in (key, str(val)))
        options = CSLSetNameValue(
            options, <const char *>kb, <const char *>vb)
        log.debug("Option %r:%r", kb, vb)

    strictness = int(strict)

    driverb = driver.encode('utf-8')

    drv = GDALGetDriverByName(driverb)
    if drv == NULL:
        raise DriverRegistrationError("Unrecognized driver: {}".format(driver))

    # Input is a path or GDAL connection string
    if isinstance(src, str):
        src = src.encode('utf-8')
        src_dataset = exc_wrap_pointer(
            GDALOpenShared(<const char *>src, <GDALAccess>0))
        close_src = True
    # Input is something like 'rasterio.open()'
    else:
        src_dataset = (<DatasetReaderBase?>src).handle()
        close_src = False

    dst = dst.encode('utf-8')

    try:
        dst_dataset = exc_wrap_pointer(
            GDALCreateCopy(drv, <const char *>dst, src_dataset,
                           strictness, options, NULL, NULL))
    finally:
        CSLDestroy(options)
        if close_src:
            GDALClose(src_dataset)

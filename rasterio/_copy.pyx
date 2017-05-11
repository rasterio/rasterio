"""Raster copying."""


include "gdal.pxi"

import logging

from rasterio._err cimport exc_wrap_pointer


log = logging.getLogger(__name__)


cdef class RasterCopier:

    """Copy a raster from a path or open dataset handle."""

    def __call__(self, srcpath, dstpath, driver='GTiff', strict=False, **kwds):

        """
        Parameters
        ----------
        src : str or rasterio.io.DatasetReader
            Path to source dataset or open dataset handle.
        dstpath : str
            Output dataset path.
        driver : str, optional
            Output driver name.
        strict : bool, optional
            Indicates if the output must be strictly equivalent or if the
            driver may adapt as necessary.
        kwds : **kwargs, optional
            Creation options for output dataset. 
        """

        cdef char **options = NULL
        cdef GDALDatasetH src_dataset = NULL
        cdef GDALDatasetH dst_dataset = NULL
        cdef GDALDriverH drv = NULL

        # Creation options
        for key, val in kwds.items():
            kb, vb = (x.upper().encode('utf-8') for x in (key, str(val)))
            options = CSLSetNameValue(
                options, <const char *>kb, <const char *>vb)
            log.debug("Option %r:%r", kb, vb)

        strictness = int(strict)

        driverb = driver.encode('utf-8')
        drv = GDALGetDriverByName(<const char *>driverb)
        if drv == NULL:
            raise ValueError("NULL driver")

        srcpath = srcpath.encode('utf-8')
        dstpath = dstpath.encode('utf-8')

        try:
            src_dataset = exc_wrap_pointer(GDALOpen(<const char *>srcpath, 0))
            dst_dataset = exc_wrap_pointer(
                GDALCreateCopy(drv, <const char *>dstpath, src_dataset,
                               strictness, options, NULL, NULL))
        finally:
            CSLDestroy(options)
            GDALClose(src_dataset)
            GDALClose(dst_dataset)

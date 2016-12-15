"""Raster copying."""

import logging
import os
import os.path

from rasterio._err cimport exc_wrap_int, exc_wrap_pointer
from rasterio._gdal cimport (
    CSLDestroy, CSLSetNameValue, GDALClose, GDALCreateCopy,
    GDALGetDriverByName, GDALOpen)

include "gdal.pxi"


log = logging.getLogger(__name__)


cdef class RasterCopier:

    def __call__(self, srcpath, dstpath, driver='GTiff', strict=False, **kwds):
        cdef char **options = NULL
        cdef GDALDatasetH src_dataset = NULL
        cdef GDALDatasetH dst_dataset = NULL
        cdef GDALDriverH drv = NULL

        # Creation options
        for key, val in kwds.items():
            kb, vb = (x.upper().encode('utf-8') for x in (key, val))
            options = CSLSetNameValue(
                options, <const char *>kb, <const char *>vb)
            log.debug("Option %r:%r", (key, val))

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
                               strictness, NULL, NULL, NULL))
        finally:
            CSLDestroy(options)
            GDALClose(src_dataset)
            GDALClose(dst_dataset)

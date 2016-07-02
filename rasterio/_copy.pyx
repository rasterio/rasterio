"""Raster copying."""

import logging
import os
import os.path

from rasterio cimport _gdal

include "gdal.pxi"


log = logging.getLogger(__name__)


cdef class RasterCopier:

    def __call__(self, src, dst, **kwds):
        cdef char **options = NULL
        cdef GDALDatasetH src_dataset = NULL
        cdef GDALDatasetH dst_dataset = NULL
        cdef GDALDriverH driver = NULL

        src = src.encode('utf-8')
        dst = dst.encode('utf-8')

        src_dataset = _gdal.GDALOpen(<const char *>src, 0)
        if src_dataset == NULL:
            raise ValueError("NULL source dataset")

        drivername = kwds.pop('driver', 'GTiff').encode('utf-8')
        driver = _gdal.GDALGetDriverByName(<const char *>drivername)
        if driver == NULL:
            raise ValueError("NULL driver")

        strictness = 0
        if kwds.pop('strict', None):
            strictness = 1

        # Creation options
        for k, v in kwds.items():
            k, v = k.upper(), v.upper()
            key = k.encode('utf-8')
            val = v.encode('utf-8')
            options = _gdal.CSLSetNameValue(
                options, <const char *>key, <const char *>val)
            log.debug("Option: %r\n", (k, v))

        dst_dataset = _gdal.GDALCreateCopy(
            driver, dst, src_dataset, strictness, NULL, NULL, NULL)
        if dst_dataset == NULL:
            raise ValueError("NULL destination dataset")

        if options != NULL:
            _gdal.CSLDestroy(options)

        _gdal.GDALClose(src_dataset)
        _gdal.GDALClose(dst_dataset)

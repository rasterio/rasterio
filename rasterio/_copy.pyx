import logging
import os
import os.path

from rasterio cimport _gdal


log = logging.getLogger('rasterio')
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())


cdef class RasterCopier:

    def __call__(self, src, dst, **kw):
        cdef char **options = NULL
        src_b = src.encode('utf-8')
        cdef const char *src_c = src_b
        dst_b = dst.encode('utf-8')
        cdef const char *dst_c = dst_b
        cdef void *src_ds = _gdal.GDALOpen(src_c, 0)
        if src_ds is NULL:
            raise ValueError("NULL source dataset")
        driver = kw.pop('driver', 'GTiff')
        driver_b = driver.encode('utf-8')
        cdef const char *driver_c = driver_b
        cdef void *drv = _gdal.GDALGetDriverByName(driver_c)
        if drv is NULL:
            raise ValueError("NULL driver")
        strictness = 0
        if kw.pop('strict', None):
            strictness = 1

        # Creation options
        for k, v in kw.items():
            k, v = k.upper(), v.upper()
            key_b = k.encode('utf-8')
            val_b = v.encode('utf-8')
            key_c = key_b
            val_c = val_b
            options = _gdal.CSLSetNameValue(options, key_c, val_c)
            log.debug("Option: %r\n", (k, v))

        cdef void *dst_ds = _gdal.GDALCreateCopy(
            drv, dst_c, src_ds, strictness, NULL, NULL, NULL)
        if dst_ds is NULL:
            raise ValueError("NULL destination dataset")
        _gdal.GDALClose(src_ds)
        _gdal.GDALClose(dst_ds)

        if options:
            _gdal.CSLDestroy(options)


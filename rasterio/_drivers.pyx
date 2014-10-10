# The GDAL and OGR driver registry.
# GDAL driver management.

import logging

from rasterio.five import string_types

cdef extern from "cpl_conv.h":
    void    CPLFree (void *ptr)
    void    CPLSetThreadLocalConfigOption (char *key, char *val)
    const char * CPLGetConfigOption ( const char *key, const char *default)

cdef extern from "cpl_error.h":
    void CPLSetErrorHandler (void *handler)

cdef extern from "gdal.h":
    void GDALAllRegister()
    void GDALDestroyDriverManager()
    int GDALGetDriverCount()
    void * GDALGetDriver(int i)
    const char * GDALGetDriverShortName(void *driver)
    const char * GDALGetDriverLongName(void *driver)

cdef extern from "ogr_api.h":
    void OGRRegisterAll()
    void OGRCleanupAll()
    int OGRGetDriverCount()

log = logging.getLogger('GDAL')
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())

level_map = {
    0: 0,
    1: logging.DEBUG,
    2: logging.WARNING,
    3: logging.ERROR,
    4: logging.CRITICAL }

code_map = {
    0: 'CPLE_None',
    1: 'CPLE_AppDefined',
    2: 'CPLE_OutOfMemory',
    3: 'CPLE_FileIO',
    4: 'CPLE_OpenFailed',
    5: 'CPLE_IllegalArg',
    6: 'CPLE_NotSupported',
    7: 'CPLE_AssertionFailed',
    8: 'CPLE_NoWriteAccess',
    9: 'CPLE_UserInterrupt',
    10: 'CPLE_ObjectNull'
}

cdef void * errorHandler(int eErrClass, int err_no, char *msg):
    log.log(level_map[eErrClass], "%s in %s", code_map[err_no], msg)

def driver_count():
    return GDALGetDriverCount() + OGRGetDriverCount()


cdef class GDALEnv(object):

    cdef object is_chef
    cdef public object options

    def __init__(self, is_chef=True, **options):
        self.is_chef = is_chef
        self.options = options.copy()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self.stop()

    def start(self):
        cdef const char *key_c
        cdef const char *val_c
        GDALAllRegister()
        OGRRegisterAll()
        CPLSetErrorHandler(<void *>errorHandler)
        if driver_count() == 0:
            raise ValueError("Drivers not registered")
        for key, val in self.options.items():
            key_b = key.upper().encode('utf-8')
            key_c = key_b
            if isinstance(val, string_types):
                val_b = val.encode('utf-8')
            else:
                val_b = ('ON' if val else 'OFF').encode('utf-8')
            val_c = val_b
            CPLSetThreadLocalConfigOption(key_c, val_c)
            log.debug("Option %s=%s", key, CPLGetConfigOption(key_c, NULL))
        return self

    def stop(self):
        cdef const char *key_c
        for key in self.options:
            key_b = key.upper().encode('utf-8')
            key_c = key_b
            CPLSetThreadLocalConfigOption(key_c, NULL)
        CPLSetErrorHandler(NULL)

    def drivers(self):
        cdef void *drv = NULL
        cdef char *key = NULL
        cdef char *val = NULL
        cdef int i
        result = {}
        for i in range(GDALGetDriverCount()):
            drv = GDALGetDriver(i)
            key = GDALGetDriverShortName(drv)
            key_b = key
            val = GDALGetDriverLongName(drv)
            val_b = val
            result[key_b.decode('utf-8')] = val_b.decode('utf-8')
        return result

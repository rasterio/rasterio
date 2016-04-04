# The GDAL and OGR driver registry.
# GDAL driver management.

import os
import os.path
import logging
import sys

from rasterio.five import string_types


cdef extern from "cpl_conv.h":
    void    CPLFree (void *ptr)
    void    CPLSetThreadLocalConfigOption (char *key, char *val)
    void    CPLSetConfigOption (char *key, char *val)
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
    1: 'CPLE_AppDefined',
    2: 'CPLE_OutOfMemory',
    3: 'CPLE_FileIO',
    4: 'CPLE_OpenFailed',
    5: 'CPLE_IllegalArg',
    6: 'CPLE_NotSupported',
    7: 'CPLE_AssertionFailed',
    8: 'CPLE_NoWriteAccess',
    9: 'CPLE_UserInterrupt',
    10: 'ObjectNull',

    # error numbers 11-16 are introduced in GDAL 2.1. See 
    # https://github.com/OSGeo/gdal/pull/98.
    11: 'CPLE_HttpResponse',
    12: 'CPLE_AWSBucketNotFound',
    13: 'CPLE_AWSObjectNotFound',
    14: 'CPLE_AWSAccessDenied',
    15: 'CPLE_AWSInvalidCredentials',
    16: 'CPLE_AWSSignatureDoesNotMatch'}


cdef void * errorHandler(int eErrClass, int err_no, char *msg):
    if err_no in code_map:
        log.log(level_map[eErrClass], "%s in %s", code_map[err_no], msg)


def driver_count():
    return GDALGetDriverCount() + OGRGetDriverCount()


cdef class ConfigEnv(object):

    cdef public object options
    cdef public object prev_options

    def __init__(self, **options):
        self.options = options.copy()
        self.prev_options = {}

    def enter_config_options(self):
        """Set GDAL config options."""
        cdef const char *key_c
        cdef const char *val_c

        for key, val in self.options.items():
            key_b = key.upper().encode('utf-8')
            key_c = key_b

            # Save current value of that key.
            val_c = CPLGetConfigOption(key_c, NULL)
            if val_c != NULL:
                val_b = val_c
                self.prev_options[key_b] = val_b

            if isinstance(val, string_types):
                val_b = val.encode('utf-8')
            else:
                val_b = ('ON' if val else 'OFF').encode('utf-8')
            val_c = val_b
            CPLSetConfigOption(key_c, val_c)

            # Redact AWS credentials.
            if key in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                       'AWS_SESSION_TOKEN', 'AWS_REGION']:
                val = '******'
            log.debug("Option %s=%s", key, val)

    def exit_config_options(self):
        """Clear GDAL config options."""
        cdef const char *key_c
        cdef const char *val_c

        for key in self.options:
            key_b = key.upper().encode('utf-8')
            key_c = key_b
            if key_b in self.prev_options:
                val_b = self.prev_options[key_b]
                key_c = key_b; val_c = val_b
                CPLSetConfigOption(key_c, val_c)
            else:
                CPLSetConfigOption(key_c, NULL)

    def __enter__(self):
        self.enter_config_options()
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self.exit_config_options()


cdef class GDALEnv(ConfigEnv):

    def __init__(self, **options):
        self.options = options.copy()
        self.prev_options = {}

    def __enter__(self):
        self.start()
        self.enter_config_options()
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self.exit_config_options()
        self.stop()

    def start(self):
        cdef const char *key_c
        cdef const char *val_c
        GDALAllRegister()
        OGRRegisterAll()
        CPLSetErrorHandler(<void *>errorHandler)
        if driver_count() == 0:
            raise ValueError("Drivers not registered")

        if 'GDAL_DATA' not in os.environ:
            whl_datadir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "gdal_data"))
            share_datadir = os.path.join(sys.prefix, 'share/gdal')
            if os.path.exists(os.path.join(whl_datadir, 'pcs.csv')):
                os.environ['GDAL_DATA'] = whl_datadir
            elif os.path.exists(os.path.join(share_datadir, 'pcs.csv')):
                os.environ['GDAL_DATA'] = share_datadir
        if 'PROJ_LIB' not in os.environ:
            whl_datadir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "proj_data"))
            os.environ['PROJ_LIB'] = whl_datadir

    def stop(self):
        CPLSetErrorHandler(NULL)

    def drivers(self):
        cdef void *drv = NULL
        cdef const char *key = NULL
        cdef const char *val = NULL
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

"""GDAL and OGR driver management."""

import logging
import os
import os.path
import sys

from rasterio.five import string_types


cdef extern from "cpl_conv.h":
    void    CPLFree (void *ptr)
    void    CPLSetThreadLocalConfigOption (char *key, char *val)
    void    CPLSetConfigOption (char *key, char *val)
    const char * CPLGetConfigOption ( const char *key, const char *default)


cdef extern from "cpl_error.h":
    void CPLSetErrorHandler(void *handler)


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
    10: 'ObjectNull',

    # error numbers 11-16 are introduced in GDAL 2.1. See 
    # https://github.com/OSGeo/gdal/pull/98.
    11: 'CPLE_HttpResponse',
    12: 'CPLE_AWSBucketNotFound',
    13: 'CPLE_AWSObjectNotFound',
    14: 'CPLE_AWSAccessDenied',
    15: 'CPLE_AWSInvalidCredentials',
    16: 'CPLE_AWSSignatureDoesNotMatch'}

log = logging.getLogger(__name__)


cdef void * errorHandler(int eErrClass, int err_no, char *msg):
    if err_no in code_map:
        # 'rasterio._gdal' is the name in our logging hierarchy for
        # messages coming direct from CPLError().
        logger = logging.getLogger('rasterio._gdal')
        logger.log(level_map[eErrClass], "%s in %s", code_map[err_no], msg)


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
        self.update_config_options(**self.options)

    def update_config_options(self, **kwargs):
        """Update GDAL config options."""
        cdef const char *key_c
        cdef const char *val_c

        self.options.update(**kwargs)
        for key, val in kwargs.items():
            key_b = key.upper().encode('utf-8')
            key_c = key_b

            # Save current value of that key.
            #if key not in self.prev_options:
            #    val_c = CPLGetConfigOption(key_c, NULL)
            #    if val_c != NULL:
            #        val_b = val_c
            #        self.prev_options[key] = val_b

            if isinstance(val, string_types):
                val_b = val.encode('utf-8')
            else:
                val_b = ('ON' if val else 'OFF').encode('utf-8')
            val_c = val_b
            CPLSetConfigOption(key_c, val_c)

            # Redact AWS credentials.
            if key.upper() in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                               'AWS_SESSION_TOKEN']:
                val = '******'
            log.debug("Set option %s=%s in env %r", key, val, self)

    def exit_config_options(self):
        """Clear GDAL config options."""
        cdef const char *key_c
        cdef const char *val_c

        for key in self.options:
            key_b = key.upper().encode('utf-8')
            key_c = key_b
            if key in self.prev_options:
                val = self.prev_options[key]
                val_b = val.encode('utf-8')
                val_c = val_b
                CPLSetConfigOption(key_c, val_c)
                log.debug("Restored previous option %s=%s in env %r", key, val, self)
            else:
                CPLSetConfigOption(key_c, NULL)
                log.debug("Unset option %s in env %r", key, self)

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
        log.debug("Entering env %r context", self)
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        self.exit_config_options()
        self.stop()
        log.debug("Exiting env %r context", self)

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
        log.debug("Env %r has been started", self)


    def stop(self):
        # NB: do not restore the CPL error handler to its default
        # state here. If you do, log messages will be written to stderr
        # by GDAL instead of being sent to Python's logging module.
        log.debug("Env %r has been stopped", self)

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

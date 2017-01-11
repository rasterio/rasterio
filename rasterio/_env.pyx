# cython: c_string_type=unicode, c_string_encoding=utf8
"""GDAL and OGR driver management."""

import logging
import os
import os.path
import sys

from rasterio.compat import string_types

from rasterio._gdal cimport (
    CPLSetConfigOption, GDALAllRegister, GDALGetDriver,
    GDALGetDriverCount, GDALGetDriverLongName, GDALGetDriverShortName,
    OGRGetDriverCount, OGRRegisterAll, CPLPopErrorHandler, CPLPushErrorHandler)

include "gdal.pxi"


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


cdef void logging_error_handler(CPLErr err_class, int err_no,
                                const char* msg) with gil:
    """Send CPL debug messages and warnings to Python's logger."""
    log = logging.getLogger('rasterio._gdal')
    if err_no in code_map:
        # 'rasterio._gdal' is the name in our logging hierarchy for
        # messages coming direct from CPLError().
        log.log(level_map[err_class], "%s in %s", code_map[err_no], msg)
    else:
        log.info("Unknown error number %r", err_no)

def driver_count():
    """Return the count of all drivers"""
    return GDALGetDriverCount() + OGRGetDriverCount()


cpdef get_gdal_config(key):
    """Get the value of a GDAL configuration option"""
    key = key.upper().encode('utf-8')
    val = CPLGetConfigOption(<const char *>key, NULL)
    if not val:
        return None
    else:
        if val == u'ON':
            return True
        elif val == u'OFF':
            return False
        else:
            return val


cpdef set_gdal_config(key, val):
    """Set a GDAL configuration option's value"""
    key = key.upper().encode('utf-8')
    if isinstance(val, string_types):
        val = val.encode('utf-8')
    else:
        val = ('ON' if val else 'OFF').encode('utf-8')
    CPLSetConfigOption(<const char *>key, <const char *>val)


cpdef del_gdal_config(key):
    """Delete a GDAL configuration option"""
    key = key.upper().encode('utf-8')
    CPLSetConfigOption(<const char *>key, NULL)


cdef class ConfigEnv(object):
    """Configuration option management"""

    cdef public object options

    def __init__(self, **options):
        self.options = {}
        self.update_config_options(**self.options)

    def update_config_options(self, **kwargs):
        """Update GDAL config options."""
        for key, val in kwargs.items():
            set_gdal_config(key, val)
            self.options[key] = val
            # Redact AWS credentials for logs
            if key.upper() in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY',
                               'AWS_SESSION_TOKEN']:
                val = '******'
            log.debug("Set option %s=%s in env %r", key, val, self)

    def clear_config_options(self):
        """Clear GDAL config options."""
        while self.options:
            key, val = self.options.popitem()
            del_gdal_config(key)
            log.debug("Unset option %s in env %r", key, self)


cdef class GDALEnv(ConfigEnv):
    """Configuration and driver management"""

    def __init__(self, **options):
        super(GDALEnv, self).__init__(**options)

    def start(self):
        CPLPushErrorHandler(<CPLErrorHandler>logging_error_handler)
        log.debug("Logging error handler pushed.")
        GDALAllRegister()
        OGRRegisterAll()
        log.debug("All drivers registered.")

        if driver_count() == 0:
            CPLPopErrorHandler()
            log.debug("Error handler popped")
            raise ValueError("Drivers not registered.")

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

        log.debug("Started GDALEnv %r.", self)

    def stop(self):
        # NB: do not restore the CPL error handler to its default
        # state here. If you do, log messages will be written to stderr
        # by GDAL instead of being sent to Python's logging module.
        log.debug("Stopping GDALEnv %r.", self)
        CPLPopErrorHandler()
        log.debug("Error handler popped.")
        log.debug("Stopped GDALEnv %r.", self)

    def drivers(self):
        cdef GDALDriverH driver = NULL
        cdef int i

        result = {}
        for i in range(GDALGetDriverCount()):
            driver = GDALGetDriver(i)
            key = GDALGetDriverShortName(driver)
            val = GDALGetDriverLongName(driver)
            result[key] = val

        return result

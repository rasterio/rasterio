# cython: language_level=3, c_string_type=unicode, c_string_encoding=utf8

"""GDAL and OGR driver and configuration management

The main thread always utilizes CPLSetConfigOption. Child threads
utilize CPLSetThreadLocalConfigOption instead. All threads use
CPLGetConfigOption and not CPLGetThreadLocalConfigOption, thus child
threads will inherit config options from the main thread unless the
option is set to a new value inside the thread.
"""

include "gdal.pxi"

from contextlib import contextmanager
import logging
import os
import os.path
import sys
import threading

from rasterio._base cimport _safe_osr_release
from rasterio._err import CPLE_BaseError
from rasterio._err cimport exc_wrap_ogrerr, exc_wrap_int
from rasterio._shim cimport set_proj_search_path

from libc.stdio cimport stderr


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

try:
    import certifi
    os.environ.setdefault("CURL_CA_BUNDLE", certifi.where())
except ImportError:
    pass

cdef bint is_64bit = sys.maxsize > 2 ** 32


cdef void log_error(CPLErr err_class, int err_no, const char* msg) with gil:
    """Send CPL debug messages and warnings to Python's logger."""
    log = logging.getLogger(__name__)
    if err_class < 3:
        if err_no in code_map:
            log.log(level_map[err_class], "%s in %s", code_map[err_no], msg)
        else:
            log.info("Unknown error number %r", err_no)


# Definition of GDAL callback functions, one for Windows and one for
# other platforms. Each calls log_error().
IF UNAME_SYSNAME == "Windows":
    cdef void __stdcall logging_error_handler(CPLErr err_class, int err_no,
                                              const char* msg) with gil:
        log_error(err_class, err_no, msg)
ELSE:
    cdef void logging_error_handler(CPLErr err_class, int err_no,
                                    const char* msg) with gil:
        log_error(err_class, err_no, msg)


def driver_count():
    """Return the count of all drivers"""
    return GDALGetDriverCount() + OGRGetDriverCount()


cpdef get_gdal_config(key, normalize=True):
    """Get the value of a GDAL configuration option.  When requesting
    ``GDAL_CACHEMAX`` the value is returned unaltered. 

    Parameters
    ----------
    key : str
        Name of config option.
    normalize : bool, optional
        Convert values of ``"ON"'`` and ``"OFF"`` to ``True`` and ``False``.
    """
    key = key.encode('utf-8')

    # GDAL_CACHEMAX is a special case
    if key.lower() == b'gdal_cachemax':
        if is_64bit:
            return GDALGetCacheMax64()
        else:
            return GDALGetCacheMax()
    else:
        val = CPLGetConfigOption(<const char *>key, NULL)

    if not val:
        return None
    elif not normalize:
        return val
    elif val.isdigit():
        return int(val)
    else:
        if val == u'ON':
            return True
        elif val == u'OFF':
            return False
        else:
            return val


cpdef set_gdal_config(key, val, normalize=True):
    """Set a GDAL configuration option's value.

    Parameters
    ----------
    key : str
        Name of config option.
    normalize : bool, optional
        Convert ``True`` to `"ON"` and ``False`` to `"OFF"``.
    """
    key = key.encode('utf-8')

    # GDAL_CACHEMAX is a special case
    if key.lower() == b'gdal_cachemax':
        if is_64bit:
            GDALSetCacheMax64(val)
        else:
            GDALSetCacheMax(val)
        return
    elif normalize and isinstance(val, bool):
        val = ('ON' if val and val else 'OFF').encode('utf-8')
    else:
        # Value could be an int
        val = str(val).encode('utf-8')

    if isinstance(threading.current_thread(), threading._MainThread):
        CPLSetConfigOption(<const char *>key, <const char *>val)
    else:
        CPLSetThreadLocalConfigOption(<const char *>key, <const char *>val)


cpdef del_gdal_config(key):
    """Delete a GDAL configuration option.

    Parameters
    ----------
    key : str
        Name of config option.
    """
    key = key.encode('utf-8')
    if isinstance(threading.current_thread(), threading._MainThread):
        CPLSetConfigOption(<const char *>key, NULL)
    else:
        CPLSetThreadLocalConfigOption(<const char *>key, NULL)


cdef class ConfigEnv(object):
    """Configuration option management"""

    def __init__(self, **options):
        self.options = options.copy()
        self.update_config_options(**self.options)

    def update_config_options(self, **kwargs):
        """Update GDAL config options."""
        for key, val in kwargs.items():
            set_gdal_config(key, val)
            self.options[key] = val

    def clear_config_options(self):
        """Clear GDAL config options."""
        while self.options:
            key, val = self.options.popitem()
            del_gdal_config(key)

    def get_config_options(self):
        return {k: get_gdal_config(k) for k in self.options}


class GDALDataFinder(object):
    """Finds GDAL data files

    Note: this is not part of the public API in 1.0.x.

    """
    def find_file(self, basename):
        """Returns path of a GDAL data file or None

        Parameters
        ----------
        basename : str
            Basename of a data file such as "header.dxf"

        Returns
        -------
        str (on success) or None (on failure)

        """
        cdef const char *path_c = NULL
        basename_b = basename.encode('utf-8')
        path_c = CPLFindFile("gdal", <const char *>basename_b)
        if path_c == NULL:
            return None
        else:
            path = path_c
            return path

    def search(self, prefix=None):
        """Returns GDAL data directory

        Note well that os.environ is not consulted.

        Returns
        -------
        str or None

        """
        path = self.search_wheel(prefix or __file__)
        if not path:
            path = self.search_prefix(prefix or sys.prefix)
            if not path:
                path = self.search_debian(prefix or sys.prefix)
        return path

    def search_wheel(self, prefix=None):
        """Check wheel location"""
        if prefix is None:
            prefix = __file__
        datadir = os.path.abspath(os.path.join(os.path.dirname(prefix), "gdal_data"))
        return datadir if os.path.exists(os.path.join(datadir, 'header.dxf')) else None

    def search_prefix(self, prefix=sys.prefix):
        """Check sys.prefix location"""
        datadir = os.path.join(prefix, 'share', 'gdal')
        return datadir if os.path.exists(os.path.join(datadir, 'header.dxf')) else None

    def search_debian(self, prefix=sys.prefix):
        """Check Debian locations"""
        gdal_release_name = GDALVersionInfo("RELEASE_NAME")
        datadir = os.path.join(prefix, 'share', 'gdal', '{}.{}'.format(*gdal_release_name.split('.')[:2]))
        return datadir if os.path.exists(os.path.join(datadir, 'header.dxf')) else None


@contextmanager
def catch_errors():
    """Intercept GDAL errors"""
    try:
        CPLPushErrorHandler(CPLQuietErrorHandler)
        yield None
    finally:
        CPLPopErrorHandler()


class PROJDataFinder(object):
    """Finds PROJ data files

    Note: this is not part of the public API in 1.0.x.

    """
    def has_data(self):
        """Returns True if PROJ's data files can be found

        Returns
        -------
        bool

        """
        cdef OGRSpatialReferenceH osr = OSRNewSpatialReference(NULL)

        try:
            with catch_errors():
                exc_wrap_ogrerr(exc_wrap_int(OSRImportFromProj4(osr, "+init=epsg:4326")))
        except CPLE_BaseError:
            return False
        else:
            return True
        finally:
            _safe_osr_release(osr)


    def search(self, prefix=None):
        """Returns PROJ data directory

        Note well that os.environ is not consulted.

        Returns
        -------
        str or None

        """
        path = self.search_wheel(prefix or __file__)
        if not path:
            path = self.search_prefix(prefix or sys.prefix)
        return path

    def search_wheel(self, prefix=None):
        """Check wheel location"""
        if prefix is None:
            prefix = __file__
        datadir = os.path.abspath(os.path.join(os.path.dirname(prefix), "proj_data"))
        return datadir if os.path.exists(datadir) else None

    def search_prefix(self, prefix=sys.prefix):
        """Check sys.prefix location"""
        datadir = os.path.join(prefix, 'share', 'proj')
        return datadir if os.path.exists(datadir) else None


cdef class GDALEnv(ConfigEnv):
    """Configuration and driver management"""

    def __init__(self, **options):
        super().__init__(**options)
        self._have_registered_drivers = False

    def start(self):
        CPLPushErrorHandler(<CPLErrorHandler>logging_error_handler)

        # The outer if statement prevents each thread from acquiring a
        # lock when the environment starts, and the inner avoids a
        # potential race condition.
        if not self._have_registered_drivers:
            with threading.Lock():
                if not self._have_registered_drivers:

                    GDALAllRegister()
                    OGRRegisterAll()

                    if 'GDAL_DATA' in os.environ:
                        log.debug("GDAL_DATA found in environment.")
                        self.update_config_options(GDAL_DATA=os.environ['GDAL_DATA'])

                    else:
                        path = GDALDataFinder().search_wheel()

                        if path:
                            log.debug("GDAL data found in package: path=%r.", path)
                            self.update_config_options(GDAL_DATA=path)

                        # See https://github.com/mapbox/rasterio/issues/1631.
                        elif GDALDataFinder().find_file("header.dxf"):
                            log.debug("GDAL data files are available at built-in paths.")

                        else:
                            path = GDALDataFinder().search()

                            if path:
                                log.debug("GDAL data found in other locations: path=%r.", path)
                                self.update_config_options(GDAL_DATA=path)

                    if 'PROJ_LIB' in os.environ:
                        log.debug("PROJ_LIB found in environment.")
                        path = os.environ["PROJ_LIB"]
                        set_proj_data_search_path(path)

                    else:
                        path = PROJDataFinder().search_wheel()

                        if path:
                            log.debug("PROJ data found in package: path=%r.", path)
                            set_proj_data_search_path(path)

                        elif PROJDataFinder().has_data():
                            log.debug("PROJ data files are available at built-in paths.")

                        else:
                            path = PROJDataFinder().search()

                            if path:
                                log.debug("PROJ data found in other locations: path=%r.", path)
                                set_proj_data_search_path(path)

                    if driver_count() == 0:
                        CPLPopErrorHandler()
                        raise ValueError("Drivers not registered.")

                    # Flag the drivers as registered, otherwise every thread
                    # will acquire a threadlock every time a new environment
                    # is started rather than just whenever the first thread
                    # actually makes it this far.
                    self._have_registered_drivers = True

        log.debug("Started GDALEnv: self=%r.", self)

    def stop(self):
        # NB: do not restore the CPL error handler to its default
        # state here. If you do, log messages will be written to stderr
        # by GDAL instead of being sent to Python's logging module.
        CPLPopErrorHandler()
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

    def _dump_open_datasets(self):
        GDALDumpOpenDatasets(stderr)


def set_proj_data_search_path(path):
    """Set PROJ data search path"""
    set_proj_search_path(path)

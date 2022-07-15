"""rasterio._err

Exception-raising wrappers for GDAL API functions.

"""

import contextlib
from enum import IntEnum
from itertools import zip_longest
import logging
import sys

log = logging.getLogger(__name__)


class CPLE_BaseError(Exception):
    """Base CPL error class

    Exceptions deriving from this class are intended for use only in
    Rasterio's Cython code. Let's not expose API users to them.
    """

    def __init__(self, error, errno, errmsg):
        self.error = error
        self.errno = errno
        self.errmsg = errmsg

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "{}".format(self.errmsg)

    @property
    def args(self):
        return self.error, self.errno, self.errmsg


class CPLE_AppDefinedError(CPLE_BaseError):
    pass


class CPLE_OutOfMemoryError(CPLE_BaseError):
    pass


class CPLE_FileIOError(CPLE_BaseError):
    pass


class CPLE_OpenFailedError(CPLE_BaseError):
    pass


class CPLE_IllegalArgError(CPLE_BaseError):
    pass


class CPLE_NotSupportedError(CPLE_BaseError):
    pass


class CPLE_AssertionFailedError(CPLE_BaseError):
    pass


class CPLE_NoWriteAccessError(CPLE_BaseError):
    pass


class CPLE_UserInterruptError(CPLE_BaseError):
    pass


class ObjectNullError(CPLE_BaseError):
    pass


class CPLE_HttpResponseError(CPLE_BaseError):
    pass


class CPLE_AWSBucketNotFoundError(CPLE_BaseError):
    pass


class CPLE_AWSObjectNotFoundError(CPLE_BaseError):
    pass


class CPLE_AWSAccessDeniedError(CPLE_BaseError):
    pass


class CPLE_AWSInvalidCredentialsError(CPLE_BaseError):
    pass


class CPLE_AWSSignatureDoesNotMatchError(CPLE_BaseError):
    pass


class CPLE_AWSError(CPLE_BaseError):
    pass


# Map of GDAL error numbers to the Python exceptions.
exception_map = {
    1: CPLE_AppDefinedError,
    2: CPLE_OutOfMemoryError,
    3: CPLE_FileIOError,
    4: CPLE_OpenFailedError,
    5: CPLE_IllegalArgError,
    6: CPLE_NotSupportedError,
    7: CPLE_AssertionFailedError,
    8: CPLE_NoWriteAccessError,
    9: CPLE_UserInterruptError,
    10: ObjectNullError,

    # error numbers 11-16 are introduced in GDAL 2.1. See
    # https://github.com/OSGeo/gdal/pull/98.
    11: CPLE_HttpResponseError,
    12: CPLE_AWSBucketNotFoundError,
    13: CPLE_AWSObjectNotFoundError,
    14: CPLE_AWSAccessDeniedError,
    15: CPLE_AWSInvalidCredentialsError,
    16: CPLE_AWSSignatureDoesNotMatchError,
    17: CPLE_AWSError
}


# CPL Error types as an enum.
class GDALError(IntEnum):
    none = CE_None
    debug = CE_Debug
    warning = CE_Warning
    failure = CE_Failure
    fatal = CE_Fatal


cdef inline object exc_check():
    """Checks GDAL error stack for fatal or non-fatal errors

    Returns
    -------
    An Exception, SystemExit, or None

    """
    cdef const char *msg_c = NULL

    err_type = CPLGetLastErrorType()
    err_no = CPLGetLastErrorNo()
    msg_c = CPLGetLastErrorMsg()

    if msg_c == NULL:
        msg = "No error message."
    else:
        msg_b = msg_c
        msg = msg_b.decode('utf-8')
        msg = msg.replace("`", "'")
        msg = msg.replace("\n", " ")

    if err_type == 3:
        exception = exception_map.get(err_no, CPLE_BaseError)(err_type, err_no, msg)
        CPLErrorReset()
        return exception
    elif err_type == 4:
        exception = SystemExit("Fatal error: {0}".format((err_type, err_no, msg)))
        CPLErrorReset()
        return exception
    else:
        CPLErrorReset()
        return None


cdef int exc_wrap(int retval) except -1:
    """Wrap a GDAL function that returns int without checking the retval"""
    exc = exc_check()
    if exc:
        raise exc
    return retval


cdef void chaining_error_handler(CPLErr err_class, int err_no, const char* msg) with gil:
    msg_b = msg
    message = msg_b.decode("utf-8")
    exception = exception_map.get(err_no, CPLE_BaseError)(err_class, err_no, message)
    error_stack = <object>CPLGetErrorHandlerUserData()
    if err_class == 3:
        error_stack.append(exception)


cdef int exc_wrap_int(int err) except -1:
    """Wrap a GDAL/OGR function that returns CPLErr or OGRErr (int)

    Raises a Rasterio exception if a non-fatal error has be set.
    """
    if err:
        exc = exc_check()
        if exc:
            raise exc
    CPLErrorReset()
    return err


cdef OGRErr exc_wrap_ogrerr(OGRErr err) except -1:
    """Wrap a function that returns OGRErr but does not use the
    CPL error stack.

    """
    if err == 0:
        CPLErrorReset()
        return err
    else:
        raise CPLE_BaseError(3, err, "OGR Error code {}".format(err))


@contextlib.contextmanager
def stack_errors():
    """TODO: better name."""
    # Set up.
    CPLErrorReset()
    error_stack = []

    # chaining_error_handler (better name a TODO) records GDAL errors
    # in the order they occur and converts to exceptions.
    CPLPushErrorHandlerEx(chaining_error_handler, <void *>error_stack)

    # Run code in the `with` block.
    yield

    # Link errors via __cause__.
    for error, cause in zip_longest(error_stack[::-1], error_stack[::-1][1:]):
        if error is not None and cause is not None:
            error.__cause__ = cause

    # Tear down.
    CPLPopErrorHandler()
    CPLErrorReset()

    # Raise the final exception.
    if error_stack:
        last = error_stack.pop()
        if last is not None:
            raise last


cdef void *exc_wrap_pointer(void *ptr) except NULL:
    """Wrap a GDAL/OGR function that returns GDALDatasetH etc (void *)

    Raises a Rasterio exception if a non-fatal error has be set.
    """
    if ptr == NULL:
        exc = exc_check()
        if exc:
            raise exc
    CPLErrorReset()
    return ptr


cdef VSILFILE *exc_wrap_vsilfile(VSILFILE *vsifile) except NULL:
    """Wrap a GDAL/OGR function that returns GDALDatasetH etc (void *)

    Raises a Rasterio exception if a non-fatal error has be set.

    """
    if vsifile == NULL:
        exc = exc_check()
        if exc:
            raise exc
    CPLErrorReset()
    return vsifile

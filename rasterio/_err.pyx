"""rasterio._err

Transformation of GDAL C API errors to Python exceptions using Python's
``with`` statement and an error-handling context manager class.

The ``CPLErrors`` error-handling context manager is intended for use in
Rasterio's Cython code. When entering the body of a ``with`` statement,
the context manager clears GDAL's error stack. On exit, the stack is
cleared again. Its ``check()`` method can be called after calling any
GDAL function to determine if ``CPLError()`` was called, and raise an
exception appropriately.

When used to wrap a call to open a PNG in update mode

    with CPLErrors() as cple:
        cdef void *hds = GDALOpen('file.png', 1)
        cple.check()
    if hds == NULL:
        raise ValueError("NULL dataset")

the ValueError of last resort never gets raised because the context
manager raises a more useful and informative error:

    Traceback (most recent call last):
      File "/Users/sean/code/rasterio/scripts/rio_insp", line 65, in <module>
        with rasterio.open(args.src, args.mode) as src:
      File "/Users/sean/code/rasterio/rasterio/__init__.py", line 111, in open
        s.start()
    CPLE_OpenFailed: The PNG driver does not support update access to existing datasets.

"""

from enums import IntEnum
import sys

from rasterio._gdal cimport (
    CPLErrorReset, CPLGetLastErrorMsg, CPLGetLastErrorNo,
    CPLGetLastErrorType)

include "gdal.pxi"


# Python exceptions expressing the CPL error numbers.

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
    16: CPLE_AWSSignatureDoesNotMatchError}


# CPL Error types as an enum.
class GDALError(IntEnum):
    none = CE_None
    debug = CE_Debug
    warning = CE_Warning
    failure = CE_Failure
    fatal = CE_Fatal


cdef class CPLErrors:
    """A manager for GDAL error handling contexts."""

    def check(self):
        """Check the error stack and raise or exit as appropriate."""
        cdef const char *msg_c = NULL

        err_type = CPLGetLastErrorType()
        # Return True if there's no error.
        # Debug and warnings are already picked up by the drivers()
        # context manager.
        if err_type < 3:
            CPLErrorReset()
            return

        err_no = CPLGetLastErrorNo()
        msg_c = CPLGetLastErrorMsg()
        if msg_c == NULL:
            msg = "No error message."
        else:
        # Reformat messages.
            msg_b = msg_c
            msg = msg_b.decode('utf-8')
            msg = msg.replace("`", "'")
            msg = msg.replace("\n", " ")

        if err_type == 4:
            sys.exit("Fatal error: {0}".format((err_type, err_no, msg)))
        else:
            CPLErrorReset()
            raise exception_map.get(err_no, CPLE_BaseError)(
                err_type, err_no, msg)

    def __enter__(self):
        CPLErrorReset()
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        CPLErrorReset()

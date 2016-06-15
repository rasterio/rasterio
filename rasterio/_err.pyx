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


# CPL function declarations.
cdef extern from "cpl_error.h":
    int CPLGetLastErrorNo()
    const char* CPLGetLastErrorMsg()
    int CPLGetLastErrorType()
    void CPLErrorReset()


# Python exceptions expressing the CPL error numbers.

class CPLError(Exception):
    """Base CPL error class

    Exceptions deriving from this class are intended for use only in
    Rasterio's Cython code. Let's not expose API users to them.
    """

    def __init__(self, errtype, errno, errmsg):
        self.errtype = errtype
        self.errno = errno
        self.errmsg = errmsg

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return "{}".format(self.errmsg)

    @property
    def args(self):
        return self.errtype, self.errno, self.errmsg


class CPLE_AppDefined(CPLError):
    pass


class CPLE_OutOfMemory(CPLError):
    pass


class CPLE_FileIO(CPLError):
    pass


class CPLE_OpenFailed(CPLError):
    pass


class CPLE_IllegalArg(CPLError):
    pass


class CPLE_NotSupported(CPLError):
    pass


class CPLE_AssertionFailed(CPLError):
    pass


class CPLE_NoWriteAccess(CPLError):
    pass


class CPLE_UserInterrupt(CPLError):
    pass


class ObjectNull(CPLError):
    pass


class CPLE_HttpResponse(CPLError):
    pass


class CPLE_AWSBucketNotFound(CPLError):
    pass


class CPLE_AWSObjectNotFound(CPLError):
    pass


class CPLE_AWSAccessDenied(CPLError):
    pass


class CPLE_AWSInvalidCredentials(CPLError):
    pass


class CPLE_AWSSignatureDoesNotMatch(CPLError):
    pass


# Map of GDAL error numbers to the Python exceptions.
exception_map = {
    1: CPLE_AppDefined,
    2: CPLE_OutOfMemory,
    3: CPLE_FileIO,
    4: CPLE_OpenFailed,
    5: CPLE_IllegalArg,
    6: CPLE_NotSupported,
    7: CPLE_AssertionFailed,
    8: CPLE_NoWriteAccess,
    9: CPLE_UserInterrupt,
    10: ObjectNull,

    # error numbers 11-16 are introduced in GDAL 2.1. See
    # https://github.com/OSGeo/gdal/pull/98.
    11: CPLE_HttpResponse,
    12: CPLE_AWSBucketNotFound,
    13: CPLE_AWSObjectNotFound,
    14: CPLE_AWSAccessDenied,
    15: CPLE_AWSInvalidCredentials,
    16: CPLE_AWSSignatureDoesNotMatch}


# CPL Error types as an enum.
class GDALError(IntEnum):
    none = 0    # CE_None
    debug = 1   # CE_Debug
    warning= 2  # CE_Warning
    failure = 3 # CE_Failure
    fatal = 4   # CE_Fatal


cdef class CPLErrors:
    """A manager for GDAL error handling contexts."""

    def check(self):
        """Check the errror stack and raise or exit as appropriate."""
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
            raise exception_map.get(err_no, CPLError)(err_type, err_no, msg)

    def __enter__(self):
        CPLErrorReset()
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        CPLErrorReset()

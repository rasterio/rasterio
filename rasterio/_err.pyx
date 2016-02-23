"""rasterio._err

Transformation of GDAL C API errors to Python exceptions using Python's
``with`` statement and an error-handling context manager class.

The ``cpl_errs`` error-handling context manager is intended for use in
Rasterio's Cython code. When entering the body of a ``with`` statement,
the context manager clears GDAL's error stack. On exit, the context
manager pops the last error off the stack and raises an appropriate
Python exception. It's otherwise pretty difficult to do this kind of
thing.  I couldn't make it work with a CPL error handler, Cython's
C code swallows exceptions raised from C callbacks.

When used to wrap a call to open a PNG in update mode

    with cpl_errs:
        cdef void *hds = GDALOpen('file.png', 1)
    if hds == NULL:
        raise ValueError("NULL dataset")

the ValueError of last resort never gets raised because the context
manager raises a more useful and informative error:

    Traceback (most recent call last):
      File "/Users/sean/code/rasterio/scripts/rio_insp", line 65, in <module>
        with rasterio.open(args.src, args.mode) as src:
      File "/Users/sean/code/rasterio/rasterio/__init__.py", line 111, in open
        s.start()
    ValueError: The PNG driver does not support update access to existing datasets.
"""

from enums import IntEnum


# CPL function declarations.
cdef extern from "cpl_error.h":
    int CPLGetLastErrorNo()
    const char* CPLGetLastErrorMsg()
    int CPLGetLastErrorType()
    void CPLErrorReset()

# Map GDAL error numbers to Python exceptions.
exception_map = {
    1: RuntimeError,        # CPLE_AppDefined
    2: MemoryError,         # CPLE_OutOfMemory
    3: IOError,             # CPLE_FileIO
    4: IOError,             # CPLE_OpenFailed
    5: TypeError,           # CPLE_IllegalArg
    6: ValueError,          # CPLE_NotSupported
    7: AssertionError,      # CPLE_AssertionFailed
    8: IOError,             # CPLE_NoWriteAccess
    9: KeyboardInterrupt,   # CPLE_UserInterrupt
    10: ValueError          # ObjectNull
    }


cdef class GDALErrCtxManager:
    """A manager for GDAL error handling contexts."""

    def __enter__(self):
        CPLErrorReset()
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        cdef int err_type = CPLGetLastErrorType()
        cdef int err_no = CPLGetLastErrorNo()
        cdef const char *msg = CPLGetLastErrorMsg()
        # TODO: warn for err_type 2?
        if err_type > 0:
            raise exception_map[err_no](msg)

cpl_errs = GDALErrCtxManager()


class GDALError(IntEnum):
    none = 0,  # CE_None
    debug = 1,  # CE_Debug
    warning= 2,  # CE_Warning
    failure = 3,  # CE_Failure
    fatal = 4  # CE_Fatal

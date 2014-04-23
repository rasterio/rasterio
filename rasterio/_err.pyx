
from rasterio cimport _gdal

import logging

cdef extern from "cpl_error.h":
    void    CPLSetErrorHandler (void *handler)
    int CPLGetLastErrorNo ( )
    const char* CPLGetLastErrorMsg ( )
    int CPLGetLastErrorType ()
    void CPLErrorReset ()

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

exception_map = {
    1: RuntimeError,
    2: MemoryError,
    3: IOError,
    4: IOError,
    5: TypeError,
    6: ValueError,
    7: AssertionError,
    8: IOError,
    9: KeyboardInterrupt,
    10: ValueError }


cdef class GDALErrCtxManager:
    """Wraps up calls to GDAL library functions in a function that also
    checks a GDAL error stack, allowing propagation of GDAL errors to
    Python's exceptions mechanism.
    """

    def __enter__(self):
        CPLErrorReset()
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        cdef int err_type = CPLGetLastErrorType()
        cdef int err_no = CPLGetLastErrorNo()
        cdef char *msg = CPLGetLastErrorMsg()
        # TODO: warn for err_type 2?
        if err_type >= 3:
            raise exception_map[err_no](msg)

def g_errs():
    return GDALErrCtxManager()


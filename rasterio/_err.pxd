include "gdal.pxi"

from libc.stdio cimport *


cdef object getexc()
cdef int exc_wrap(int retval) except -1
cdef int exc_wrap_int(int retval) except -1
cdef OGRErr exc_wrap_ogrerr(OGRErr retval) except -1
cdef void *exc_wrap_pointer(void *ptr) except NULL
cdef VSILFILE *exc_wrap_vsilfile(VSILFILE *f) except NULL

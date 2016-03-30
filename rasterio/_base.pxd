# Base class.

cdef class DatasetReader:
    # Read-only access to dataset metadata. No IO!
    
    cdef void *_hds

    cdef readonly object name
    cdef readonly object mode
    cdef readonly object options
    cdef readonly object width, height
    cdef readonly object shape
    cdef public object driver
    cdef public object _count
    cdef public object _dtypes
    cdef public object _closed
    cdef public object _crs
    cdef public object _crs_wkt
    cdef public object _transform
    cdef public object _block_shapes
    cdef public object _nodatavals
    cdef public object _read
    cdef object env

    cdef void *band(self, int bidx) except NULL


cdef void *_osr_from_crs(object crs)

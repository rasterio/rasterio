cdef class RasterReader:
    # Read-only access to raster data and metadata.
    
    cdef void *_hds

    cdef readonly object name
    cdef readonly object mode
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
    cdef object driver_manager

    cdef void *band(self, int bidx)

cdef class RasterUpdater(RasterReader):
    # Read-write access to raster data and metadata.
    cdef readonly object _init_dtype
    cdef readonly object _init_nodata
    cdef readonly object _options


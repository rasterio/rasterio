include "gdal.pxi"


cdef class _CRS:

    cdef OGRSpatialReferenceH _osr
    cdef object _epsg

# cython: language_level=3

include "gdal.pxi"


cdef class _CRS:

    cdef OGRSpatialReferenceH _osr
    cdef object _epsg

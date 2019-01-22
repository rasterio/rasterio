# _CRS class definition

include "gdal.pxi"


cdef class _CRS:

    cdef OGRSpatialReferenceH _osr

include "gdal.pxi"


cdef class CRS:

    cdef OGRSpatialReferenceH _osr
    cdef object _data
    cdef object _epsg
    cdef object _wkt

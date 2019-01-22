# _CRS class definition

include "gdal.pxi"


cdef class _CRS:

    cdef OGRSpatialReferenceH _osr

cdef class OSRCloneManager:
    cdef OGRSpatialReferenceH osr

    @staticmethod
    cdef OSRCloneManager create(OGRSpatialReferenceH in_osr, int from_esri)
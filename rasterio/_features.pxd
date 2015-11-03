
cdef class GeomBuilder:
    cdef void *geom
    cdef object code
    cdef object geomtypename
    cdef object ndims
    cdef _buildCoords(self, void *geom)
    cpdef _buildPoint(self)
    cpdef _buildLineString(self)
    cpdef _buildLinearRing(self)
    cdef _buildParts(self, void *geom)
    cpdef _buildPolygon(self)
    cpdef _buildMultiPolygon(self)
    cdef build(self, void *geom)


cdef class OGRGeomBuilder:
    cdef void * _createOgrGeometry(self, int geom_type) except NULL
    cdef _addPointToGeometry(self, void *cogr_geometry, object coordinate)
    cdef void * _buildPoint(self, object coordinates) except NULL
    cdef void * _buildLineString(self, object coordinates) except NULL
    cdef void * _buildLinearRing(self, object coordinates) except NULL
    cdef void * _buildPolygon(self, object coordinates) except NULL
    cdef void * _buildMultiPoint(self, object coordinates) except NULL
    cdef void * _buildMultiLineString(self, object coordinates) except NULL
    cdef void * _buildMultiPolygon(self, object coordinates) except NULL
    cdef void * _buildGeometryCollection(self, object coordinates) except NULL
    cdef void * build(self, object geom) except NULL

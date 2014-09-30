
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
    cpdef build_wkb(self, object wkb)


cdef class OGRGeomBuilder:
    cdef void * _createOgrGeometry(self, int geom_type)
    cdef _addPointToGeometry(self, void *cogr_geometry, object coordinate)
    cdef void * _buildPoint(self, object coordinates)
    cdef void * _buildLineString(self, object coordinates)
    cdef void * _buildLinearRing(self, object coordinates)
    cdef void * _buildPolygon(self, object coordinates)
    cdef void * _buildMultiPoint(self, object coordinates)
    cdef void * _buildMultiLineString(self, object coordinates)
    cdef void * _buildMultiPolygon(self, object coordinates)
    cdef void * _buildGeometryCollection(self, object coordinates)
    cdef void * build(self, object geom)

# cython: profile=True

import logging

import numpy as np
cimport numpy as np

from rasterio cimport _gdal, _ogr


log = logging.getLogger('rasterio')
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())


cdef int registered = 0

cdef void register():
    _ogr.OGRRegisterAll();
    registered = 1


def polygonize(image):
    """Return an iterator over Fiona-style features extracted from the
    image.
    """
    # Write the image into an in-memory raster.
    cdef int retval, rows, cols
    cdef void *hrdriver, *hds, *hband, *hfdriver, *hfs, *hlayer, *fielddefn

    if not registered:
        register()

    hrdriver = _gdal.GDALGetDriverByName("MEM")
    if hrdriver is NULL:
        raise ValueError("NULL driver for 'MEM'")
    rows = image.shape[0]
    cols = image.shape[1]
    hds = _gdal.GDALCreate(hrdriver, "temp", cols, rows, 1, 1, NULL)
    if hds is NULL:
        raise ValueError("NULL datasource")
    hband = _gdal.GDALGetRasterBand(hds, 1)
    if hband is NULL:
        raise ValueError("NULL band")
    retval = io_ubyte(hband, 1, 0, 0, cols, rows, image)

    # Create an in-memory feature store.
    hfdriver = _ogr.OGRGetDriverByName("Memory")
    if hfdriver is NULL:
        raise ValueError("NULL driver")
    hfs = _ogr.OGR_Dr_CreateDataSource(hfdriver, "temp", NULL)
    if hfs is NULL:
        raise ValueError("NULL feature dataset")
    
    # And a layer.
    hlayer = _ogr.OGR_DS_CreateLayer(hfs, "polygons", NULL, 3, NULL)
    if hlayer is NULL:
        raise ValueError("NULL layer")

    fielddefn = _ogr.OGR_Fld_Create("image_value", 0)
    if fielddefn is NULL:
        raise ValueError("NULL field definition")
    _ogr.OGR_L_CreateField(hlayer, fielddefn, 1)
    _ogr.OGR_Fld_Destroy(fielddefn)
    
    # TODO: masked arrays.
    retval = _gdal.GDALPolygonize(hband, NULL, hlayer, 0, NULL, NULL, NULL)
    
    # Yield Fiona-style features
    cdef ShapeIterator shape_iter = ShapeIterator()
    shape_iter.hfs = hfs
    shape_iter.hlayer = hlayer
    for s, v in shape_iter:
        yield s, v

    if hds is not NULL:
        _gdal.GDALClose(hds)
    if hfs is not NULL:
        _ogr.OGR_DS_Destroy(hfs)


ctypedef np.uint8_t DTYPE_UBYTE_t

cdef int io_ubyte(
        void *hband,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height, 
        np.ndarray[DTYPE_UBYTE_t, ndim=2, mode='c'] buffer):
    return _gdal.GDALRasterIO(
        hband, mode, xoff, yoff, width, height,
        &buffer[0, 0], buffer.shape[1], buffer.shape[0], 1, 0, 0)


# Mapping of OGR integer geometry types to GeoJSON type names.
GEOMETRY_TYPES = {
    0: 'Unknown',
    1: 'Point',
    2: 'LineString',
    3: 'Polygon',
    4: 'MultiPoint',
    5: 'MultiLineString',
    6: 'MultiPolygon',
    7: 'GeometryCollection',
    100: 'None',
    101: 'LinearRing',
    0x80000001: '3D Point',
    0x80000002: '3D LineString',
    0x80000003: '3D Polygon',
    0x80000004: '3D MultiPoint',
    0x80000005: '3D MultiLineString',
    0x80000006: '3D MultiPolygon',
    0x80000007: '3D GeometryCollection' }

# Geometry related functions and classes follow.

cdef void * _createOgrGeomFromWKB(object wkb) except NULL:
    """Make an OGR geometry from a WKB string"""
    geom_type = bytearray(wkb)[1]
    cdef unsigned char *buffer = wkb
    cdef void *cogr_geometry = _ogr.OGR_G_CreateGeometry(geom_type)
    if cogr_geometry is not NULL:
        _ogr.OGR_G_ImportFromWkb(cogr_geometry, buffer, len(wkb))
    return cogr_geometry


cdef _deleteOgrGeom(void *cogr_geometry):
    """Delete an OGR geometry"""
    if cogr_geometry is not NULL:
        _ogr.OGR_G_DestroyGeometry(cogr_geometry)
    cogr_geometry = NULL


cdef class GeomBuilder:
    """Builds Fiona (GeoJSON) geometries from an OGR geometry handle.
    """
    cdef void *geom
    cdef object code
    cdef object typename
    cdef object ndims

    cdef _buildCoords(self, void *geom):
        # Build a coordinate sequence
        cdef int i
        if geom is NULL:
            raise ValueError("Null geom")
        npoints = _ogr.OGR_G_GetPointCount(geom)
        coords = []
        for i in range(npoints):
            values = [_ogr.OGR_G_GetX(geom, i), _ogr.OGR_G_GetY(geom, i)]
            if self.ndims > 2:
                values.append(_ogr.OGR_G_GetZ(geom, i))
            coords.append(tuple(values))
        return coords
    
    cpdef _buildPoint(self):
        return {'type': 'Point', 'coordinates': self._buildCoords(self.geom)[0]}
    
    cpdef _buildLineString(self):
        return {'type': 'LineString', 'coordinates': self._buildCoords(self.geom)}
    
    cpdef _buildLinearRing(self):
        return {'type': 'LinearRing', 'coordinates': self._buildCoords(self.geom)}
    
    cdef _buildParts(self, void *geom):
        cdef int j
        cdef void *part
        if geom is NULL:
            raise ValueError("Null geom")
        parts = []
        for j in range(_ogr.OGR_G_GetGeometryCount(geom)):
            part = _ogr.OGR_G_GetGeometryRef(geom, j)
            parts.append(GeomBuilder().build(part))
        return parts
    
    cpdef _buildPolygon(self):
        coordinates = [p['coordinates'] for p in self._buildParts(self.geom)]
        return {'type': 'Polygon', 'coordinates': coordinates}
    
    cpdef _buildMultiPolygon(self):
        coordinates = [p['coordinates'] for p in self._buildParts(self.geom)]
        return {'type': 'MultiPolygon', 'coordinates': coordinates}

    cdef build(self, void *geom):
        # The only method anyone needs to call
        if geom is NULL:
            raise ValueError("Null geom")
        
        cdef unsigned int etype = _ogr.OGR_G_GetGeometryType(geom)
        self.code = etype
        self.typename = GEOMETRY_TYPES[self.code & (~0x80000000)]
        self.ndims = _ogr.OGR_G_GetCoordinateDimension(geom)
        self.geom = geom
        return getattr(self, '_build' + self.typename)()
    
    cpdef build_wkb(self, object wkb):
        # The only other method anyone needs to call
        cdef object data = wkb
        cdef void *cogr_geometry = _createOgrGeomFromWKB(data)
        result = self.build(cogr_geometry)
        _deleteOgrGeom(cogr_geometry)
        return result


cdef geometry(void *geom):
    """Factory for Fiona geometries"""
    return GeomBuilder().build(geom)


# Feature extension classes and functions follow.

cdef _deleteOgrFeature(void *cogr_feature):
    """Delete an OGR feature"""
    if cogr_feature is not NULL:
        _ogr.OGR_F_Destroy(cogr_feature)
    cogr_feature = NULL


cdef class ShapeIterator:

    """Provides iterated access to feature shapes.
    """

    # Reference to its Collection
    cdef void *hfs, *hlayer

    def __iter__(self):
        _ogr.OGR_L_ResetReading(self.hlayer)
        return self

    def __next__(self):
        cdef long fid
        cdef void *ftr
        cdef void *geom
        ftr = _ogr.OGR_L_GetNextFeature(self.hlayer)
        if ftr == NULL:
            raise StopIteration
        image_value = _ogr.OGR_F_GetFieldAsInteger(ftr, 0)
        geom = _ogr.OGR_F_GetGeometryRef(ftr)
        if geom is not NULL:
            shape = GeomBuilder().build(geom)
        else:
            shape = None
        _deleteOgrFeature(ftr)
        return shape, image_value


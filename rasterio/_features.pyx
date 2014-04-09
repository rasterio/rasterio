# cython: profile=True

import logging
import json
import numpy as np
cimport numpy as np
from rasterio cimport _gdal, _ogr, _io


log = logging.getLogger('rasterio')
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())


def _shapes(image, mask, connectivity, transform):
    """Return an iterator over Fiona-style features extracted from the
    image.

    The image must be of unsigned 8-bit integer (rasterio.byte or
    numpy.uint8) data type. It may be either a numpy ndarray or a 
    rasterio Band object (RasterReader, bidx namedtuple).
    """
    # Write the image into an in-memory raster.
    cdef int retval, rows, cols
    cdef void *hrdriver
    cdef void *hds
    cdef void *hband
    cdef void *hmask
    cdef void *hmaskband
    cdef void *hfdriver
    cdef void *hfs
    cdef void *hlayer
    cdef void *fielddefn
    cdef double gt[6]
    cdef _io.RasterReader rdr
    cdef _io.RasterReader mrdr
    cdef char **options = NULL

    if isinstance(image, np.ndarray):
        hrdriver = _gdal.GDALGetDriverByName("MEM")
        if hrdriver == NULL:
            raise ValueError("NULL driver for 'MEM'")
        rows = image.shape[0]
        cols = image.shape[1]
        hds = _gdal.GDALCreate(
                    hrdriver, "temp", cols, rows, 1, 
                    <_gdal.GDALDataType>1, NULL)
        if hds == NULL:
            raise ValueError("NULL datasource")
        if transform:
            for i in range(6):
                gt[i] = transform[i]
            err = _gdal.GDALSetGeoTransform(hds, gt)
            if err:
                raise ValueError("transform not set: %s" % transform)

        hband = _gdal.GDALGetRasterBand(hds, 1)
        if hband == NULL:
            raise ValueError("NULL band")
        retval = _io.io_ubyte(hband, 1, 0, 0, cols, rows, image)
    elif isinstance(image, tuple):
        rdr = image.ds
        hband = rdr.band(image.bidx)
    else:
        raise ValueError("Invalid source image")

    # The boolean mask must be converted to 0 and 1 for GDAL.
    if isinstance(mask, np.ndarray):
        if mask.shape != image.shape:
            raise ValueError("Mask must have same shape as image")
        hmask = _gdal.GDALCreate(
                    hrdriver, "mask", cols, rows, 1, 
                    <_gdal.GDALDataType>1, NULL)
        if hmask == NULL:
            raise ValueError("NULL datasource")
        hmaskband = _gdal.GDALGetRasterBand(hmask, 1)
        if hmaskband == NULL:
            raise ValueError("NULL band")
        a = np.ones(mask.shape, dtype=np.uint8)
        a[mask == False] = 0
        a[mask == True] = 1
        retval = _io.io_ubyte(hmaskband, 1, 0, 0, cols, rows, a)
    elif isinstance(mask, tuple):
        if mask.shape != image.shape:
            raise ValueError("Mask must have same shape as image")
        mrdr = mask.ds
        hmaskband = mrdr.band(mask.bidx)
    else:
        hmaskband = NULL

    # Create an in-memory feature store.
    hfdriver = _ogr.OGRGetDriverByName("Memory")
    if hfdriver == NULL:
        raise ValueError("NULL driver")
    hfs = _ogr.OGR_Dr_CreateDataSource(hfdriver, "temp", NULL)
    if hfs == NULL:
        raise ValueError("NULL feature dataset")
    
    # And a layer.
    hlayer = _ogr.OGR_DS_CreateLayer(hfs, "polygons", NULL, 3, NULL)
    if hlayer == NULL:
        raise ValueError("NULL layer")

    fielddefn = _ogr.OGR_Fld_Create("image_value", 0)
    if fielddefn == NULL:
        raise ValueError("NULL field definition")
    _ogr.OGR_L_CreateField(hlayer, fielddefn, 1)
    _ogr.OGR_Fld_Destroy(fielddefn)

    if connectivity == 8:
        options = _gdal.CSLSetNameValue(options, "8CONNECTED", "8")
    retval = _gdal.GDALPolygonize(hband, hmaskband, hlayer, 0, options, NULL, NULL)
    
    # Yield Fiona-style features
    cdef ShapeIterator shape_iter = ShapeIterator()
    shape_iter.hfs = hfs
    shape_iter.hlayer = hlayer
    for s, v in shape_iter:
        yield s, v

    if hds != NULL:
        _gdal.GDALClose(hds)
    if hmask != NULL:
        _gdal.GDALClose(hmask)
    if hfs != NULL:
        _ogr.OGR_DS_Destroy(hfs)
    if options:
        _gdal.CSLDestroy(options)


def _sieve(image, size, connectivity=4, output=None):
    """Return an ndarray with features of smaller than size removed.
    
    The image must be of unsigned 8-bit integer (rasterio.byte or
    numpy.uint8) data type. It may be either a numpy ndarray or a 
    rasterio Band object (RasterReader, bidx namedtuple).

    Likewise, the optional output must be of unsigned 8-bit integer
    (rasterio.byte or numpy.uint8) data type. It may be either a numpy
    ndarray or a rasterio Band object (RasterUpdater, bidx namedtuple).
    """
    cdef int retval, rows, cols
    cdef void *hrdriver
    cdef void *hdsin
    cdef void *hdsout
    cdef void *hbandin
    cdef void *hbandout
    cdef _io.RasterReader rdr
    cdef _io.RasterUpdater udr

    if isinstance(image, np.ndarray):
        hrdriver = _gdal.GDALGetDriverByName("MEM")
        if hrdriver == NULL:
            raise ValueError("NULL driver for 'MEM'")
        rows = image.shape[0]
        cols = image.shape[1]
        hdsin = _gdal.GDALCreate(
                    hrdriver, "input", cols, rows, 1, 
                    <_gdal.GDALDataType>1, NULL)
        if hdsin == NULL:
            raise ValueError("NULL input datasource")
        hbandin = _gdal.GDALGetRasterBand(hdsin, 1)
        if hbandin == NULL:
            raise ValueError("NULL input band")
        retval = _io.io_ubyte(hbandin, 1, 0, 0, cols, rows, image)
    elif isinstance(image, tuple):
        rdr = image.ds
        hband = rdr.band(image.bidx)
    else:
        raise ValueError("Invalid source image")

    if output is None or isinstance(output, np.ndarray):
        hdsout = _gdal.GDALCreate(
                    hrdriver, "output", cols, rows, 1, 
                    <_gdal.GDALDataType>1, NULL)
        if hdsout == NULL:
            raise ValueError("NULL output datasource")
        hbandout = _gdal.GDALGetRasterBand(hdsout, 1)
        if hbandout == NULL:
            raise ValueError("NULL output band")
    elif isinstance(image, tuple):
        udr = output.ds
        hbandout = udr.band(output.bidx)
    else:
        raise ValueError("Invalid source image")

    retval = _gdal.GDALSieveFilter(
                hbandin, NULL, hbandout, size, connectivity,
                NULL, NULL, NULL)

    out = output or np.zeros(image.shape, np.uint8)
    retval = _io.io_ubyte(hbandout, 0, 0, 0, cols, rows, out)

    if hdsin != NULL:
        _gdal.GDALClose(hdsin)
    if hdsout != NULL:
        _gdal.GDALClose(hdsout)

    return out


def _rasterize(shapes, image, transform, all_touched):
    """
    Burn shapes with their values into the image.
    """

    cdef int retval
    cdef size_t i
    cdef size_t num_geometries = len(shapes)
    cdef void *memdriver
    cdef void *out_ds
    cdef void *out_band
    cdef void **ogr_geoms = NULL
    cdef char **options = NULL
    cdef double geotransform[6]
    cdef double *pixel_values = NULL  # requires one value per geometry
    cdef int dst_bands[1]  # only need one band to burn into

    dst_bands[0] = 1
    
    cdef int width = image.shape[1]
    cdef int height = image.shape[0]

    try:
        if all_touched:
            options = _gdal.CSLSetNameValue(options, "ALL_TOUCHED", "TRUE")

        # Do the boilerplate required to create a dataset, band, and 
        # set transformation
        memdriver = _gdal.GDALGetDriverByName("MEM")
        if memdriver == NULL:
            raise ValueError("NULL driver for 'MEM'")
        out_ds = _gdal.GDALCreate(
                    memdriver, "output", width, height, 1,
                    <_gdal.GDALDataType>1, NULL)
        if out_ds == NULL:
            raise ValueError("NULL output datasource")
        for i in range(6):
            geotransform[i] = transform[i]
        err = _gdal.GDALSetGeoTransform(out_ds, geotransform)
        if err:
            raise ValueError("transform not set: %s" % transform)
        
        out_band = _gdal.GDALGetRasterBand(out_ds, 1)
        if out_band == NULL:
            raise ValueError("NULL output band")


        ogr_geoms = <void **>_gdal.CPLMalloc(num_geometries * sizeof(void*))
        pixel_values = <double *>_gdal.CPLMalloc(
                            num_geometries * sizeof(double))

        for i, (geometry, value) in enumerate(shapes):
            ogr_geoms[i] = OGRGeomBuilder().build(geometry)
            pixel_values[i] = <double>value

        # First, copy image data to the in-memory band.
        retval = _io.io_ubyte(out_band, 1, 0, 0, width, height, image)

        # Burn the shapes in.
        retval = _gdal.GDALRasterizeGeometries(
                    out_ds, 1, dst_bands,
                    num_geometries, ogr_geoms,
                    NULL, geotransform, pixel_values,
                    options, NULL, NULL)

        # Write the in-memory band back to the image.
        retval = _io.io_ubyte(out_band, 0, 0, 0, width, height, image)

    finally:
        for i in range(num_geometries):
            _deleteOgrGeom(ogr_geoms[i])
        _gdal.CPLFree(ogr_geoms)
        _gdal.CPLFree(pixel_values)
        if out_ds != NULL:
            _gdal.GDALClose(out_ds)
        if options:
            _gdal.CSLDestroy(options)


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

# Mapping of GeoJSON type names to OGR integer geometry types
GEOJSON2OGR_GEOMETRY_TYPES = dict((v, k) for k, v in GEOMETRY_TYPES.iteritems())


# Geometry related functions and classes follow.

cdef void * _createOgrGeomFromWKB(object wkb) except NULL:
    """Make an OGR geometry from a WKB string"""
    geom_type = bytearray(wkb)[1]
    cdef unsigned char *buffer = wkb
    cdef void *cogr_geometry = _ogr.OGR_G_CreateGeometry(geom_type)
    if cogr_geometry != NULL:
        _ogr.OGR_G_ImportFromWkb(cogr_geometry, buffer, len(wkb))
    return cogr_geometry


cdef _deleteOgrGeom(void *cogr_geometry):
    """Delete an OGR geometry"""
    if cogr_geometry != NULL:
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
        if geom == NULL:
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
        if geom == NULL:
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
        if geom == NULL:
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


cdef class OGRGeomBuilder:
    """Builds OGR geometries from Fiona geometries.
    From Fiona: https://github.com/Toblerity/Fiona/blob/master/src/fiona/ogrext.pyx
    """
    cdef void * _createOgrGeometry(self, int geom_type) except NULL:
        cdef void *cogr_geometry = _ogr.OGR_G_CreateGeometry(geom_type)
        if cogr_geometry is NULL:
            raise Exception("Could not create OGR Geometry of type: %i" % geom_type)
        return cogr_geometry

    cdef _addPointToGeometry(self, void *cogr_geometry, object coordinate):
        if len(coordinate) == 2:
            x, y = coordinate
            _ogr.OGR_G_AddPoint_2D(cogr_geometry, x, y)
        else:
            x, y, z = coordinate[:3]
            _ogr.OGR_G_AddPoint(cogr_geometry, x, y, z)

    cdef void * _buildPoint(self, object coordinates) except NULL:
        cdef void *cogr_geometry = self._createOgrGeometry(GEOJSON2OGR_GEOMETRY_TYPES['Point'])
        self._addPointToGeometry(cogr_geometry, coordinates)
        return cogr_geometry

    cdef void * _buildLineString(self, object coordinates) except NULL:
        cdef void *cogr_geometry = self._createOgrGeometry(GEOJSON2OGR_GEOMETRY_TYPES['LineString'])
        for coordinate in coordinates:
            log.debug("Adding point %s", coordinate)
            self._addPointToGeometry(cogr_geometry, coordinate)
        return cogr_geometry

    cdef void * _buildLinearRing(self, object coordinates) except NULL:
        cdef void *cogr_geometry = self._createOgrGeometry(GEOJSON2OGR_GEOMETRY_TYPES['LinearRing'])
        for coordinate in coordinates:
            log.debug("Adding point %s", coordinate)
            self._addPointToGeometry(cogr_geometry, coordinate)
        log.debug("Closing ring")
        _ogr.OGR_G_CloseRings(cogr_geometry)
        return cogr_geometry

    cdef void * _buildPolygon(self, object coordinates) except NULL:
        cdef void *cogr_ring
        cdef void *cogr_geometry = self._createOgrGeometry(GEOJSON2OGR_GEOMETRY_TYPES['Polygon'])
        for ring in coordinates:
            log.debug("Adding ring %s", ring)
            cogr_ring = self._buildLinearRing(ring)
            log.debug("Built ring")
            _ogr.OGR_G_AddGeometryDirectly(cogr_geometry, cogr_ring)
            log.debug("Added ring %s", ring)
        return cogr_geometry

    cdef void * _buildMultiPoint(self, object coordinates) except NULL:
        cdef void *cogr_part
        cdef void *cogr_geometry = self._createOgrGeometry(GEOJSON2OGR_GEOMETRY_TYPES['MultiPoint'])
        for coordinate in coordinates:
            log.debug("Adding point %s", coordinate)
            cogr_part = self._buildPoint(coordinate)
            _ogr.OGR_G_AddGeometryDirectly(cogr_geometry, cogr_part)
            log.debug("Added point %s", coordinate)
        return cogr_geometry

    cdef void * _buildMultiLineString(self, object coordinates) except NULL:
        cdef void *cogr_part
        cdef void *cogr_geometry = self._createOgrGeometry(GEOJSON2OGR_GEOMETRY_TYPES['MultiLineString'])
        for line in coordinates:
            log.debug("Adding line %s", line)
            cogr_part = self._buildLineString(line)
            log.debug("Built line")
            _ogr.OGR_G_AddGeometryDirectly(cogr_geometry, cogr_part)
            log.debug("Added line %s", line)
        return cogr_geometry

    cdef void * _buildMultiPolygon(self, object coordinates) except NULL:
        cdef void *cogr_part
        cdef void *cogr_geometry = self._createOgrGeometry(GEOJSON2OGR_GEOMETRY_TYPES['MultiPolygon'])
        for part in coordinates:
            log.debug("Adding polygon %s", part)
            cogr_part = self._buildPolygon(part)
            log.debug("Built polygon")
            _ogr.OGR_G_AddGeometryDirectly(cogr_geometry, cogr_part)
            log.debug("Added polygon %s", part)
        return cogr_geometry

    cdef void * _buildGeometryCollection(self, object coordinates) except NULL:
        cdef void *cogr_part
        cdef void *cogr_geometry = self._createOgrGeometry(GEOJSON2OGR_GEOMETRY_TYPES['GeometryCollection'])
        for part in coordinates:
            log.debug("Adding part %s", part)
            cogr_part = OGRGeomBuilder().build(part)
            log.debug("Built part")
            _ogr.OGR_G_AddGeometryDirectly(cogr_geometry, cogr_part)
            log.debug("Added part %s", part)
        return cogr_geometry

    cdef void * build(self, object geometry) except NULL:
        cdef object typename = geometry['type']
        cdef object coordinates = geometry.get('coordinates')
        if typename == 'Point':
            return self._buildPoint(coordinates)
        elif typename == 'LineString':
            return self._buildLineString(coordinates)
        elif typename == 'LinearRing':
            return self._buildLinearRing(coordinates)
        elif typename == 'Polygon':
            return self._buildPolygon(coordinates)
        elif typename == 'MultiPoint':
            return self._buildMultiPoint(coordinates)
        elif typename == 'MultiLineString':
            return self._buildMultiLineString(coordinates)
        elif typename == 'MultiPolygon':
            return self._buildMultiPolygon(coordinates)
        elif typename == 'GeometryCollection':
            coordinates = geometry.get('geometries')
            return self._buildGeometryCollection(coordinates)
        else:
            raise ValueError("Unsupported geometry type %s" % typename)


# Feature extension classes and functions follow.

cdef _deleteOgrFeature(void *cogr_feature):
    """Delete an OGR feature"""
    if cogr_feature != NULL:
        _ogr.OGR_F_Destroy(cogr_feature)
    cogr_feature = NULL


cdef class ShapeIterator:

    """Provides iterated access to feature shapes.
    """

    # Reference to its Collection
    cdef void *hfs
    cdef void *hlayer

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
        if geom != NULL:
            shape = GeomBuilder().build(geom)
        else:
            shape = None
        _deleteOgrFeature(ftr)
        return shape, image_value


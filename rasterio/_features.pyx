# cython: profile=True

import logging
import json
import numpy as np
cimport numpy as np

from rasterio cimport _gdal, _ogr, _io
from rasterio.dtypes import dtype_rev


log = logging.getLogger('rasterio')
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())


ctypedef np.uint8_t DTYPE_UBYTE_t


def _shapes(image, mask=None, connectivity=4, transform=None):
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
        retval = io_ubyte(hband, 1, 0, 0, cols, rows, image)
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
        a[mask == True] = 0
        retval = io_ubyte(hmaskband, 1, 0, 0, cols, rows, a)
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
    
    # TODO: connectivity option.
    retval = _gdal.GDALPolygonize(hband, hmaskband, hlayer, 0, NULL, NULL, NULL)
    
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
        retval = io_ubyte(hbandin, 1, 0, 0, cols, rows, image)
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
    retval = io_ubyte(hbandout, 0, 0, 0, cols, rows, out)

    if hdsin != NULL:
        _gdal.GDALClose(hdsin)
    if hdsout != NULL:
        _gdal.GDALClose(hdsout)

    return out


def _rasterize_geometry_json(geometries, size_t rows, size_t columns, transform=None, all_touched=False, DTYPE_UBYTE_t default_value=1):
    """
    :param geometries: array of either geometry json strings, or array of (geometry json string, value) pairs.
    Values must be unsigned integer type.  If not provided, this function will return a binary mask.
    :param rows: number of rows
    :param columns: number of columns
    :param transform: GDAL style geotransform.  If provided, will be set on output.
    :param all_touched: if true, will rasterize all pixels touched, otherwise will use GDAL default method.
    :param default_value: must be 8 bit unsigned, will be used to set all values not specifically passed in geometries.
    """

    cdef int retval
    cdef size_t i
    cdef size_t num_geometries = len(geometries)
    cdef void *memdriver
    cdef void *out_ds
    cdef void *out_band
    cdef void **ogr_geoms = NULL
    cdef char **options = NULL
    cdef double geotransform[6]
    cdef double *pixel_values = NULL  # requires one value per geometry
    cdef int dst_bands[1]  # only need one band to burn into
    dst_bands[0] = 1

    try:
        if all_touched:
            options = <char **>_gdal.CPLMalloc(sizeof(char*))
            options[0] = "ALL_TOUCHED=TRUE"

        #Do the boilerplate required to create a dataset, band, and set transformation
        memdriver = _gdal.GDALGetDriverByName("MEM")
        if memdriver == NULL:
            raise ValueError("NULL driver for 'MEM'")
        out_ds = _gdal.GDALCreate(memdriver, "output", columns, rows, 1, <_gdal.GDALDataType>1, NULL)
        if out_ds == NULL:
            raise ValueError("NULL output datasource")
        if transform:
            for i in range(6):
                geotransform[i] = transform[i]
            err = _gdal.GDALSetGeoTransform(out_ds, geotransform)
            if err:
                raise ValueError("transform not set: %s" % transform)
        out_band = _gdal.GDALGetRasterBand(out_ds, 1)
        if out_band == NULL:
            raise ValueError("NULL output band")

        ogr_geoms = <void **>_gdal.CPLMalloc(num_geometries * sizeof(void*))
        pixel_values = <double *>_gdal.CPLMalloc(num_geometries * sizeof(double))
        for i in range(num_geometries):
            entry = geometries[i]
            if isinstance(entry, (tuple, list)):
                geometry_json, value = entry
            else:
                geometry_json = entry
                value = default_value
            ogr_geoms[i] = _ogr.OGR_G_CreateGeometryFromJson(geometry_json)
            pixel_values[i] = <double>value

        retval = _gdal.GDALRasterizeGeometries(out_ds, 1, dst_bands, num_geometries, ogr_geoms, NULL, geotransform, pixel_values, options, NULL, NULL)
        out = np.zeros((rows, columns), np.uint8)
        retval = io_ubyte(out_band, 0, 0, 0, columns, rows, out)

    finally:
        _gdal.CPLFree(ogr_geoms)
        _gdal.CPLFree(options)
        _gdal.CPLFree(pixel_values)
        if out_ds != NULL:
            _gdal.GDALClose(out_ds)

    return out


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


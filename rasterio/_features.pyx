"""Feature extraction"""

include "gdal.pxi"

import logging

import numpy as np

from rasterio import dtypes
from rasterio.enums import MergeAlg

cimport numpy as np

from rasterio._err cimport exc_wrap_int, exc_wrap_pointer
from rasterio._io cimport DatasetReaderBase, InMemoryRaster, io_auto


log = logging.getLogger(__name__)


def _shapes(image, mask, connectivity, transform):
    """
    Return a generator of (polygon, value) for each each set of adjacent pixels
    of the same value.

    Parameters
    ----------
    image : array or dataset object opened in 'r' mode or Band or tuple(dataset, bidx)
        Data type must be one of rasterio.int16, rasterio.int32,
        rasterio.uint8, rasterio.uint16, or rasterio.float32.
    mask : numpy ndarray or rasterio Band object
        Values of False or 0 will be excluded from feature generation
        Must evaluate to bool (rasterio.bool_ or rasterio.uint8)
    connectivity : int
        Use 4 or 8 pixel connectivity for grouping pixels into features
    transform : Affine
        If not provided, feature coordinates will be generated based on pixel
        coordinates

    Returns
    -------
    Generator of (polygon, value)
        Yields a pair of (polygon, value) for each feature found in the image.
        Polygons are GeoJSON-like dicts and the values are the associated value
        from the image, in the data type of the image.
        Note: due to floating point precision issues, values returned from a
        floating point image may not exactly match the original values.

    """
    cdef int retval
    cdef int rows
    cdef int cols
    cdef GDALRasterBandH band = NULL
    cdef GDALRasterBandH maskband = NULL
    cdef GDALDriverH driver = NULL
    cdef OGRDataSourceH fs = NULL
    cdef OGRLayerH layer = NULL
    cdef OGRFieldDefnH fielddefn = NULL
    cdef char **options = NULL
    cdef InMemoryRaster mem_ds = None
    cdef InMemoryRaster mask_ds = None
    cdef ShapeIterator shape_iter = None

    cdef bint is_float = np.dtype(image.dtype).kind == 'f'
    cdef int fieldtp = 2 if is_float else 0

    valid_dtypes = ('int16', 'int32', 'uint8', 'uint16', 'float32')

    if np.dtype(image.dtype).name not in valid_dtypes:
        raise ValueError("image dtype must be one of: {0}".format(
            ', '.join(valid_dtypes)))

    if connectivity not in (4, 8):
        raise ValueError("Connectivity Option must be 4 or 8")

    if dtypes.is_ndarray(image):
        mem_ds = InMemoryRaster(image=image, transform=transform)
        band = mem_ds.band(1)
    elif isinstance(image, tuple):
        rdr = image.ds
        band = (<DatasetReaderBase?>rdr).band(image.bidx)
    else:
        raise ValueError("Invalid source image")

    if mask is not None:
        if mask.shape != image.shape:
            raise ValueError("Mask must have same shape as image")

        if np.dtype(mask.dtype).name not in ('bool', 'uint8'):
            raise ValueError("Mask must be dtype rasterio.bool_ or "
                             "rasterio.uint8")

        if dtypes.is_ndarray(mask):
            # A boolean mask must be converted to uint8 for GDAL
            mask_ds = InMemoryRaster(image=mask.astype('uint8'),
                                     transform=transform)
            maskband = mask_ds.band(1)
        elif isinstance(mask, tuple):
            mrdr = mask.ds
            maskband = (<DatasetReaderBase?>mrdr).band(mask.bidx)

    # Create an in-memory feature store.
    driver = OGRGetDriverByName("Memory")
    if driver == NULL:
        raise ValueError("NULL driver")
    fs = OGR_Dr_CreateDataSource(driver, "temp", NULL)
    if fs == NULL:
        raise ValueError("NULL feature dataset")

    # And a layer.
    layer = OGR_DS_CreateLayer(fs, "polygons", NULL, 3, NULL)
    if layer == NULL:
        raise ValueError("NULL layer")

    fielddefn = OGR_Fld_Create("image_value", fieldtp)
    if fielddefn == NULL:
        raise ValueError("NULL field definition")
    OGR_L_CreateField(layer, fielddefn, 1)
    OGR_Fld_Destroy(fielddefn)

    if connectivity == 8:
        options = CSLSetNameValue(options, "8CONNECTED", "8")

    if is_float:
        GDALFPolygonize(band, maskband, layer, 0, options, NULL, NULL)
    else:
        GDALPolygonize(band, maskband, layer, 0, options, NULL, NULL)

    # Yield Fiona-style features
    shape_iter = ShapeIterator()
    shape_iter.layer = layer
    shape_iter.fieldtype = fieldtp
    for s, v in shape_iter:
        yield s, v

    if mem_ds is not None:
        mem_ds.close()
    if mask_ds is not None:
        mask_ds.close()
    if fs != NULL:
        OGR_DS_Destroy(fs)
    if options:
        CSLDestroy(options)


def _sieve(image, size, out, mask, connectivity):
    """
    Replaces small polygons in `image` with the value of their largest
    neighbor.  Polygons are found for each set of neighboring pixels of the
    same value.

    Parameters
    ----------
    image : array or dataset object opened in 'r' mode or Band or tuple(dataset, bidx)
        Must be of type rasterio.int16, rasterio.int32, rasterio.uint8,
        rasterio.uint16, or rasterio.float32.
    size : int
        minimum polygon size (number of pixels) to retain.
    out : numpy ndarray
        Array of same shape and data type as `image` in which to store results.
    mask : numpy ndarray or rasterio Band object
        Values of False or 0 will be excluded from feature generation.
        Must evaluate to bool (rasterio.bool_ or rasterio.uint8)
    connectivity : int
        Use 4 or 8 pixel connectivity for grouping pixels into features.

    """
    cdef int retval
    cdef int rows
    cdef int cols
    cdef InMemoryRaster in_mem_ds = None
    cdef InMemoryRaster out_mem_ds = None
    cdef InMemoryRaster mask_mem_ds = None
    cdef GDALRasterBandH in_band = NULL
    cdef GDALRasterBandH out_band = NULL
    cdef GDALRasterBandH mask_band = NULL

    valid_dtypes = ('int16', 'int32', 'uint8', 'uint16')

    if np.dtype(image.dtype).name not in valid_dtypes:
        valid_types_str = ', '.join(('rasterio.{0}'.format(t) for t
                                     in valid_dtypes))
        raise ValueError(
            "image dtype must be one of: {0}".format(valid_types_str))

    if size <= 0:
        raise ValueError('size must be greater than 0')
    elif type(size) == float:
        raise ValueError('size must be an integer number of pixels')
    elif size > (image.shape[0] * image.shape[1]):
        raise ValueError('size must be smaller than size of image')

    if connectivity not in (4, 8):
        raise ValueError('connectivity must be 4 or 8')

    if out.shape != image.shape:
        raise ValueError('out raster shape must be same as image shape')

    if np.dtype(image.dtype).name != np.dtype(out.dtype).name:
        raise ValueError('out raster must match dtype of image')

    if dtypes.is_ndarray(image):
        in_mem_ds = InMemoryRaster(image=image)
        in_band = in_mem_ds.band(1)
    elif isinstance(image, tuple):
        rdr = image.ds
        in_band = (<DatasetReaderBase?>rdr).band(image.bidx)
    else:
        raise ValueError("Invalid source image")

    if dtypes.is_ndarray(out):
        log.debug("out array: %r", out)
        out_mem_ds = InMemoryRaster(image=out)
        out_band = out_mem_ds.band(1)
    elif isinstance(out, tuple):
        udr = out.ds
        out_band = (<DatasetReaderBase?>udr).band(out.bidx)
    else:
        raise ValueError("Invalid out image")

    if mask is not None:
        if mask.shape != image.shape:
            raise ValueError("Mask must have same shape as image")

        if np.dtype(mask.dtype) not in ('bool', 'uint8'):
            raise ValueError("Mask must be dtype rasterio.bool_ or "
                             "rasterio.uint8")

        if dtypes.is_ndarray(mask):
            # A boolean mask must be converted to uint8 for GDAL
            mask_mem_ds = InMemoryRaster(image=mask.astype('uint8'))
            mask_band = mask_mem_ds.band(1)

        elif isinstance(mask, tuple):
            mask_reader = mask.ds
            mask_band = (<DatasetReaderBase?>mask_reader).band(mask.bidx)

    GDALSieveFilter(in_band, mask_band, out_band, size, connectivity,
                          NULL, NULL, NULL)

    # Read from out_band into out
    io_auto(out, out_band, False)

    if in_mem_ds is not None:
        in_mem_ds.close()
    if out_mem_ds is not None:
        out_mem_ds.close()
    if mask_mem_ds is not None:
        mask_mem_ds.close()


def _rasterize(shapes, image, transform, all_touched, merge_alg):
    """
    Burns input geometries into `image`.

    Parameters
    ----------
    shapes : iterable of (geometry, value) pairs
        `geometry` is a GeoJSON-like object.
    image : numpy ndarray
        Array in which to store results.
    transform : Affine transformation object, optional
        Transformation from pixel coordinates of `image` to the
        coordinate system of the input `shapes`. See the `transform`
        property of dataset objects.
    all_touched : boolean, optional
        If True, all pixels touched by geometries will be burned in.
        If false, only pixels whose center is within the polygon or
        that are selected by Bresenham's line algorithm will be burned
        in.
    merge_alg : MergeAlg, required
        Merge algorithm to use.  One of:
            MergeAlg.replace (default): the new value will overwrite the
                existing value.
            MergeAlg.add: the new value will be added to the existing raster.
    """
    cdef int retval
    cdef size_t i
    cdef size_t num_geoms = 0
    cdef OGRGeometryH *geoms = NULL
    cdef char **options = NULL
    cdef double *pixel_values = NULL
    cdef InMemoryRaster mem = None

    try:
        if all_touched:
            options = CSLSetNameValue(options, "ALL_TOUCHED", "TRUE")
        merge_algorithm = merge_alg.value.encode('utf-8')
        options = CSLSetNameValue(options, "MERGE_ALG", merge_algorithm)

        # GDAL needs an array of geometries.
        # For now, we'll build a Python list on the way to building that
        # C array. TODO: make this more efficient.
        all_shapes = list(shapes)
        num_geoms = len(all_shapes)

        geoms = <OGRGeometryH *>CPLMalloc(
            num_geoms * sizeof(OGRGeometryH))
        pixel_values = <double *>CPLMalloc(num_geoms * sizeof(double))

        for i, (geometry, value) in enumerate(all_shapes):
            try:
                geoms[i] = OGRGeomBuilder().build(geometry)
                pixel_values[i] = <double>value
            except:
                log.error("Geometry %r at index %d with value %d skipped",
                    geometry, i, value)

        with InMemoryRaster(image=image, transform=transform) as mem:
            exc_wrap_int(
                GDALRasterizeGeometries(
                    mem.handle(), 1, mem.band_ids,num_geoms, geoms, NULL,
                    mem.gdal_transform, pixel_values, options, NULL, NULL))

            # Read in-memory data back into image
            image = mem.read()

    finally:
        for i in range(num_geoms):
            _deleteOgrGeom(geoms[i])
        CPLFree(geoms)
        CPLFree(pixel_values)
        if options:
            CSLDestroy(options)


def _explode(coords):
    """Explode a GeoJSON geometry's coordinates object and yield
    coordinate tuples. As long as the input is conforming, the type of
    the geometry doesn't matter.  From Fiona 1.4.8"""
    for e in coords:
        if isinstance(e, (float, int)):
            yield coords
            break
        else:
            for f in _explode(e):
                yield f


def _bounds(geometry, north_up=True, transform=None):
    """Bounding box of a GeoJSON geometry.

    left, bottom, right, top
    *not* xmin, ymin, xmax, ymax

    If not north_up, y will be switched to guarantee the above.

    From Fiona 1.4.8 with updates here to handle feature collections.
    TODO: add to Fiona.
    """
    if 'features' in geometry:
        xmins = []
        ymins = []
        xmaxs = []
        ymaxs = []
        for feature in geometry['features']:
            xmin, ymin, xmax, ymax = _bounds(feature['geometry'])
            xmins.append(xmin)
            ymins.append(ymin)
            xmaxs.append(xmax)
            ymaxs.append(ymax)
        if north_up:
            return min(xmins), min(ymins), max(xmaxs), max(ymaxs)
        else:
            return min(xmins), max(ymaxs), max(xmaxs), min(ymins)

    else:
        if transform is not None:
            xyz = list(_explode(geometry['coordinates']))
            xyz_px = [point * transform for point in xyz]
            xyz = tuple(zip(*xyz_px))
            return min(xyz[0]), max(xyz[1]), max(xyz[0]), min(xyz[1])
        else:
            xyz = tuple(zip(*list(_explode(geometry['coordinates']))))
            if north_up:
                return min(xyz[0]), min(xyz[1]), max(xyz[0]), max(xyz[1])
            else:
                return min(xyz[0]), max(xyz[1]), max(xyz[0]), min(xyz[1])


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
    0x80000007: '3D GeometryCollection'
}

# Mapping of GeoJSON type names to OGR integer geometry types
GEOJSON2OGR_GEOMETRY_TYPES = dict(
    (v, k) for k, v in GEOMETRY_TYPES.iteritems()
)


# Geometry related functions and classes follow.


cdef _deleteOgrGeom(OGRGeometryH geom):
    """Delete an OGR geometry"""
    if geom != NULL:
        OGR_G_DestroyGeometry(geom)
    geom = NULL


cdef class GeomBuilder:
    """Builds a GeoJSON (Fiona-style) geometry from an OGR geometry."""

    cdef _buildCoords(self, OGRGeometryH geom):
        # Build a coordinate sequence
        cdef int i
        if geom == NULL:
            raise ValueError("Null geom")
        npoints = OGR_G_GetPointCount(geom)
        coords = []
        for i in range(npoints):
            values = [OGR_G_GetX(geom, i), OGR_G_GetY(geom, i)]
            if self.ndims > 2:
                values.append(OGR_G_GetZ(geom, i))
            coords.append(tuple(values))
        return coords

    cpdef _buildPoint(self):
        return {
            'type': 'Point',
            'coordinates': self._buildCoords(self.geom)[0]}

    cpdef _buildLineString(self):
        return {
            'type': 'LineString',
            'coordinates': self._buildCoords(self.geom)}

    cpdef _buildLinearRing(self):
        return {
            'type': 'LinearRing',
            'coordinates': self._buildCoords(self.geom)}

    cdef _buildParts(self, OGRGeometryH geom):
        cdef int j
        cdef OGRGeometryH part
        if geom == NULL:
            raise ValueError("Null geom")
        parts = []
        for j in range(OGR_G_GetGeometryCount(geom)):
            part = OGR_G_GetGeometryRef(geom, j)
            parts.append(GeomBuilder().build(part))
        return parts

    cpdef _buildPolygon(self):
        coordinates = [p['coordinates'] for p in self._buildParts(self.geom)]
        return {'type': 'Polygon', 'coordinates': coordinates}

    cpdef _buildMultiPoint(self):
        coordinates = [p['coordinates'] for p in self._buildParts(self.geom)]
        return {'type': 'MultiPoint', 'coordinates': coordinates}

    cpdef _buildMultiLineString(self):
        coordinates = [p['coordinates'] for p in self._buildParts(self.geom)]
        return {'type': 'MultiLineString', 'coordinates': coordinates}

    cpdef _buildMultiPolygon(self):
        coordinates = [p['coordinates'] for p in self._buildParts(self.geom)]
        return {'type': 'MultiPolygon', 'coordinates': coordinates}

    cdef build(self, OGRGeometryH geom):
        """Builds a GeoJSON object from an OGR geometry object."""
        if geom == NULL:
            raise ValueError("Null geom")
        cdef unsigned int etype = OGR_G_GetGeometryType(geom)
        self.code = etype
        self.geomtypename = GEOMETRY_TYPES[self.code & (~0x80000000)]
        self.ndims = OGR_G_GetCoordinateDimension(geom)
        self.geom = geom

        return getattr(self, '_build' + self.geomtypename)()


cdef class OGRGeomBuilder:
    """
    Builds an OGR geometry from GeoJSON geometry.
    From Fiona: https://github.com/Toblerity/Fiona/blob/master/src/fiona/ogrext.pyx
    """

    cdef OGRGeometryH _createOgrGeometry(self, int geom_type) except NULL:
        cdef OGRGeometryH geom = OGR_G_CreateGeometry(geom_type)
        if geom is NULL:
            raise Exception(
                "Could not create OGR Geometry of type: %i" % geom_type)
        return geom

    cdef _addPointToGeometry(self, OGRGeometryH geom, object coordinate):
        if len(coordinate) == 2:
            x, y = coordinate
            OGR_G_AddPoint_2D(geom, x, y)
        else:
            x, y, z = coordinate[:3]
            OGR_G_AddPoint(geom, x, y, z)

    cdef OGRGeometryH _buildPoint(self, object coordinates) except NULL:
        cdef OGRGeometryH geom = self._createOgrGeometry(
            GEOJSON2OGR_GEOMETRY_TYPES['Point'])
        self._addPointToGeometry(geom, coordinates)
        return geom

    cdef OGRGeometryH _buildLineString(self, object coordinates) except NULL:
        cdef OGRGeometryH geom = self._createOgrGeometry(
            GEOJSON2OGR_GEOMETRY_TYPES['LineString'])
        for coordinate in coordinates:
            self._addPointToGeometry(geom, coordinate)
        return geom

    cdef OGRGeometryH _buildLinearRing(self, object coordinates) except NULL:
        cdef OGRGeometryH geom = self._createOgrGeometry(
            GEOJSON2OGR_GEOMETRY_TYPES['LinearRing'])
        for coordinate in coordinates:
            self._addPointToGeometry(geom, coordinate)
        OGR_G_CloseRings(geom)
        return geom

    cdef OGRGeometryH _buildPolygon(self, object coordinates) except NULL:
        cdef OGRGeometryH ring = NULL
        cdef OGRGeometryH geom = self._createOgrGeometry(
            GEOJSON2OGR_GEOMETRY_TYPES['Polygon'])
        for r in coordinates:
            ring = self._buildLinearRing(r)
            OGR_G_AddGeometryDirectly(geom, ring)
        return geom

    cdef OGRGeometryH _buildMultiPoint(self, object coordinates) except NULL:
        cdef OGRGeometryH part = NULL
        cdef OGRGeometryH geom = self._createOgrGeometry(
            GEOJSON2OGR_GEOMETRY_TYPES['MultiPoint'])
        for coordinate in coordinates:
            part = self._buildPoint(coordinate)
            OGR_G_AddGeometryDirectly(geom, part)
        return geom

    cdef OGRGeometryH _buildMultiLineString(
            self, object coordinates) except NULL:
        cdef OGRGeometryH part = NULL
        cdef OGRGeometryH geom = self._createOgrGeometry(
            GEOJSON2OGR_GEOMETRY_TYPES['MultiLineString'])
        for line in coordinates:
            part = self._buildLineString(line)
            OGR_G_AddGeometryDirectly(geom, part)
        return geom

    cdef OGRGeometryH _buildMultiPolygon(self, object coordinates) except NULL:
        cdef OGRGeometryH part = NULL
        cdef OGRGeometryH geom = self._createOgrGeometry(
            GEOJSON2OGR_GEOMETRY_TYPES['MultiPolygon'])
        for poly in coordinates:
            part = self._buildPolygon(poly)
            OGR_G_AddGeometryDirectly(geom, part)
        return geom

    cdef OGRGeometryH _buildGeomCollection(self, object geoms) except NULL:
        cdef OGRGeometryH part = NULL
        cdef OGRGeometryH ogr_geom = self._createOgrGeometry(
            GEOJSON2OGR_GEOMETRY_TYPES['GeometryCollection'])
        for g in geoms:
            part = OGRGeomBuilder().build(g)
            OGR_G_AddGeometryDirectly(ogr_geom, part)
        return ogr_geom

    cdef OGRGeometryH build(self, object geometry) except NULL:
        """Builds an OGR geometry from GeoJSON geometry.
        Assumes that geometry has been validated prior to calling this; this
        only does basic checks for validity.
        """
        cdef object typename = geometry['type']
        cdef object coordinates
        cdef object geometries

        valid_types = {'Point', 'MultiPoint', 'LineString', 'MultiLineString',
                       'Polygon', 'MultiPolygon'}

        if typename in valid_types:
            coordinates = geometry.get('coordinates')
            if not (coordinates and len(coordinates) > 0):
                raise ValueError("Input is not a valid geometry object")

            if typename == 'Point':
                return self._buildPoint(coordinates)
            elif typename == 'LineString':
                return self._buildLineString(coordinates)
            elif typename == 'Polygon':
                return self._buildPolygon(coordinates)
            elif typename == 'MultiPoint':
                return self._buildMultiPoint(coordinates)
            elif typename == 'MultiLineString':
                return self._buildMultiLineString(coordinates)
            elif typename == 'MultiPolygon':
                return self._buildMultiPolygon(coordinates)

        elif typename == 'GeometryCollection':
            geometries = geometry.get('geometries')
            if not (geometries and len(geometries) > 0):
                raise ValueError("Input is not a valid geometry object")

            return self._buildGeomCollection(geometries)

        else:
            raise ValueError("Unsupported geometry type %s" % typename)


# Feature extension classes and functions follow.

cdef _deleteOgrFeature(OGRFeatureH feat):
    """Delete an OGR feature"""
    if feat != NULL:
        OGR_F_Destroy(feat)
    feat = NULL


cdef class ShapeIterator:
    """Provides an iterator over shapes in an OGR feature layer."""

    def __iter__(self):
        OGR_L_ResetReading(self.layer)
        return self

    def __next__(self):
        cdef OGRFeatureH feat = NULL
        cdef OGRGeometryH geom = NULL

        try:
            feat = OGR_L_GetNextFeature(self.layer)

            if feat == NULL:
                raise StopIteration

            if self.fieldtype == 0:
                image_value = OGR_F_GetFieldAsInteger(feat, 0)
            else:
                image_value = OGR_F_GetFieldAsDouble(feat, 0)
            geom = OGR_F_GetGeometryRef(feat)
            if geom != NULL:
                shape = GeomBuilder().build(geom)
            else:
                shape = None
            return shape, image_value

        finally:
            _deleteOgrFeature(feat)

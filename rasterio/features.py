"""Functions for working with features in a raster dataset."""

import json
import rasterio
from rasterio._features import _shapes, _sieve, _rasterize_geometry_json


def shapes(image, mask=None, connectivity=4, transform=None):
    """Yields a (shape, image_value) pair for each feature in the image.
    
    The shapes are GeoJSON-like dicts and the image values are ints.
    
    Features are found using a connected-component labeling algorithm.

    The image must be of unsigned 8-bit integer (rasterio.byte or
    numpy.uint8) data type. If a mask is provided, pixels for which the
    mask is `True` will be excluded from feature generation.
    """
    if image.dtype.type != rasterio.ubyte:
        raise ValueError("Image must be dtype uint8/ubyte")

    if mask is not None and mask.dtype.type != rasterio.bool_:
        raise ValueError("Mask must be dtype rasterio.bool_")

    with rasterio.drivers():
        for s, v in _shapes(image, mask, connectivity, transform):
            yield s, v


def sieve(image, size, connectivity=4, output=None):
    """Returns a copy of the image, but with smaller features removed.

    Features smaller than the specified size have their pixel value
    replaced by that of the largest neighboring features.
    
    The image must be of unsigned 8-bit integer (rasterio.byte or
    numpy.uint8) data type.
    """
    if image.dtype.type != rasterio.ubyte:
        raise ValueError("Image must be dtype uint8/ubyte")

    if output is not None and output.dtype.type != rasterio.ubyte:
        raise ValueError("Output must be dtype uint8/ubyte")

    with rasterio.drivers():
        return _sieve(image, size, connectivity)


def rasterize_features(features, rows, columns, transform=None, all_touched=False, value_property=None):
    """
    :param features: Fiona style features iterator (geojson python objects)
    Values must be unsigned integer type.  If not provided, this function will return a binary mask.
    :param rows: number of rows
    :param cols: number of columns
    :param transform: GDAL style geotransform.  If provided, will be set on output.
    :param all_touched: if true, will rasterize all pixels touched, otherwise will use GDAL default method.
    :param value_attribute: if provided, the name of the property to extract the values from for each feature
        (must be unsigned integer type).  If not provided, this function will return a binary mask.
    """


    geoms = []
    for index, feature in enumerate(features):  #have to loop over features, since it may be yielded from a generator
        feature_json = json.dumps(feature['geometry'])
        if value_property is not None:
            if not not (feature['properties'] and value_property in feature['properties']):
                raise ValueError("Value property is missing from feature number %i: %s" % (index, value_property))
            value = feature['properties'][value_property]
            if not (isinstance(value, int) and value >= 0 and value < 256):
                raise ValueError("Value for value_property is not valid for feature %i (must be 8 bit unsigned integer)" % index)
            geoms.append((feature_json, value))
        else:
            geoms.append(feature_json)

    with rasterio.drivers():
        return _rasterize_geometry_json(geoms, rows, columns, transform, all_touched)


def rasterize_geometries(geometries, rows, columns, transform=None, all_touched=False):
    """
    :param geometries: array of Fiona style geometry objects or array of (geometry, value) pairs.
    Values must be unsigned integer type.  If not provided, this function will return a binary mask.
    :param rows: number of rows
    :param cols: number of columns
    :param transform: GDAL style geotransform.  If provided, will be set on output.
    :param all_touched: if true, will rasterize all pixels touched, otherwise will use GDAL default method.
    """


    geoms = []
    for index, entry in enumerate(geometries):  #have to loop over features, since it may be yielded from a generator
        if isinstance(entry, (tuple, list)):
            geometry, value = entry
            if not (isinstance(value, int) and value >= 0 and value < 256):
                raise ValueError("Value for geometry number %i is not valid (must be 8 bit unsigned integer)" % index)
            geoms.append((json.dumps(geometry), value))
        else:
            geoms.append(json.dumps(entry))

    with rasterio.drivers():
        return _rasterize_geometry_json(geoms, rows, columns, transform, all_touched)


"""Functions for working with features in a raster dataset."""

import json
import logging
import time
import warnings

import numpy as np

import rasterio
from rasterio._features import _shapes, _sieve, _rasterize
from rasterio.transform import IDENTITY, guard_transform
from rasterio.dtypes import get_minimum_int_dtype


log = logging.getLogger('rasterio')
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())


def shapes(image, mask=None, connectivity=4, transform=IDENTITY):
    """Yields a (shape, image_value) pair for each feature in the image.
    
    The shapes are GeoJSON-like dicts and the image values are ints.
    
    Features are found using a connected-component labeling algorithm.

    The image must be of unsigned 8-bit integer (rasterio.byte or
    numpy.uint8) data type. If a mask is provided, pixels for which the
    mask is `False` will be excluded from feature generation.
    """
    if np.dtype(image.dtype) != np.dtype(rasterio.ubyte):
        raise ValueError("Image must be dtype uint8/ubyte")

    if mask is not None and np.dtype(mask.dtype) != np.dtype(rasterio.bool_):
        raise ValueError("Mask must be dtype rasterio.bool_")

    if connectivity not in (4, 8):
        raise ValueError("Connectivity Option must be 4 or 8")

    transform = guard_transform(transform)

    with rasterio.drivers():
        for s, v in _shapes(image, mask, connectivity, transform.to_gdal()):
            yield s, v


def sieve(image, size, connectivity=4, output=None):
    """Returns a copy of the image, but with smaller features removed.

    Features smaller than the specified size have their pixel value
    replaced by that of the largest neighboring features.
    
    The image must be of unsigned 8-bit integer (rasterio.byte or
    numpy.uint8) data type.
    """
    if np.dtype(image.dtype) != np.dtype(rasterio.ubyte):
        raise ValueError("Image must be dtype uint8/ubyte")

    if output is not None and (
            np.dtype(output.dtype) != np.dtype(rasterio.ubyte)):
        raise ValueError("Output must be dtype uint8/ubyte")

    with rasterio.drivers():
        return _sieve(image, size, connectivity)


def rasterize(
        shapes, 
        out_shape=None,
        fill=0,
        output=None,
        transform=IDENTITY,
        all_touched=False,
        default_value=1,
        dtype=None):
    """Returns an image array with points, lines, or polygons burned in.

    A different value may be specified for each shape.  The shapes may
    be georeferenced or may have image coordinates. An existing image
    array may be provided, or one may be created. By default, the center
    of image elements determines whether they are updated, but all
    touched elements may be optionally updated.

    Valid data types are: int16, int32, uint8, uint16, uint32, float32, float64

    :param shapes: an iterator over Fiona style geometry objects (with a default
    value of default_value) or an iterator over (geometry, value) pairs.

    :param transform: GDAL style geotransform to be applied to the
    image.

    :param out_shape: shape of created image array
    :param fill: fill value for created image array
    :param output: alternatively, an existing image array

    :param all_touched: if True, will rasterize all pixels touched, 
    otherwise will use GDAL default method.
    :param default_value: value burned in for shapes if not provided as part
    of shapes.
    """

    valid_dtypes = ('int16', 'int32', 'uint8', 'uint16', 'uint32', 'float32',
                    'float64')

    def get_valid_dtype(values):
        values_dtype = values.dtype
        if values_dtype.kind == 'i':
            values_dtype = np.dtype(get_minimum_int_dtype(values))
        if values_dtype.name in valid_dtypes:
            return values_dtype
        return None

    def can_cast_dtype(values, dtype):
        if values.dtype.name == np.dtype(dtype).name:
            return True
        elif values.dtype.kind == 'f':
            return np.allclose(values, values.astype(dtype))
        else:
            return np.array_equal(values, values.astype(dtype))

    if fill != 0:
        fill_array = np.array([fill])
        if get_valid_dtype(fill_array) is None:
            raise ValueError('fill must be one of these types: %s'
                             % (', '.join(valid_dtypes)))
        elif dtype is not None and not can_cast_dtype(fill_array, dtype):
            raise ValueError('fill value cannot be cast to specified dtype')


    if default_value != 1:
        default_value_array = np.array([default_value])
        if get_valid_dtype(default_value_array) is None:
            raise ValueError('default_value must be one of these types: %s'
                             % (', '.join(valid_dtypes)))
        elif dtype is not None and not can_cast_dtype(default_value_array,
                                                      dtype):
            raise ValueError('default_value cannot be cast to specified dtype')

    valid_shapes = []
    shape_values = []
    for index, item in enumerate(shapes):
        try:
            if isinstance(item, (tuple, list)):
                geom, value = item
            else:
                geom = item
                value = default_value
            geom = getattr(geom, '__geo_interface__', None) or geom
            if (not isinstance(geom, dict) or
                'type' not in geom or 'coordinates' not in geom):
                raise ValueError(
                    'Object %r at index %d is not a geometry object' %
                    (geom, index))
            valid_shapes.append((geom, value))
            shape_values.append(value)
        except Exception:
            log.exception('Exception caught, skipping shape %d', index)

    if not valid_shapes:
        raise ValueError('No valid shapes found for rasterize.  Shapes must be '
                         'valid geometry objects')

    shape_values = np.array(shape_values)
    values_dtype = get_valid_dtype(shape_values)
    if values_dtype is None:
        raise ValueError('shape values must be one of these dtypes: %s' %
                         (', '.join(valid_dtypes)))

    if dtype is None:
        dtype = values_dtype
    elif np.dtype(dtype).name not in valid_dtypes:
        raise ValueError('dtype must be one of: %s' % (', '.join(valid_dtypes)))
    elif not can_cast_dtype(shape_values, dtype):
        raise ValueError('shape values could not be cast to specified dtype')

    if output is not None:
        if np.dtype(output.dtype).name not in valid_dtypes:
            raise ValueError('Output image dtype must be one of: %s' 
                             % (', '.join(valid_dtypes)))
        if not can_cast_dtype(shape_values, output.dtype):
            raise ValueError('shape values cannot be cast to dtype of output '
                             'image')

    elif out_shape is not None:
        output = np.empty(out_shape, dtype=dtype)
        output.fill(fill)
    else:
        raise ValueError('Either an output shape or image must be provided')
    
    transform = guard_transform(transform)

    with rasterio.drivers():
        _rasterize(valid_shapes, output, transform.to_gdal(), all_touched)
    
    return output


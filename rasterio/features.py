"""Functions for working with features in a raster dataset."""

import json
import logging
import time
import warnings

import numpy as np

import rasterio
from rasterio._features import _shapes, _sieve, _rasterize, _bounds
from rasterio.transform import IDENTITY, guard_transform
from rasterio.dtypes import get_minimum_int_dtype


log = logging.getLogger('rasterio')


class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())


def geometry_mask(
        geometries,
        out_shape,
        transform,
        all_touched=False,
        invert=False):
    """Create a mask from shapes.  By default, mask is intended for use as a
    numpy mask, where pixels that overlap shapes are False.

    Parameters
    ----------
    geometries : iterable over geometries (GeoJSON-like objects)
    out_shape : tuple or list
        Shape of output numpy ndarray.
    transform : Affine transformation object
        Transformation from pixel coordinates of `image` to the
        coordinate system of the input `shapes`. See the `transform`
        property of dataset objects.
    all_touched : boolean, optional
        If True, all pixels touched by geometries will be burned in.  If
        false, only pixels whose center is within the polygon or that
        are selected by Bresenham's line algorithm will be burned in.
    invert: boolean, optional
        If True, mask will be True for pixels that overlap shapes.
        False by default.

    Returns
    -------
    out : numpy ndarray of type 'bool'
        Result
    """

    fill, mask_value = (0, 1) if invert else (1, 0)

    return rasterize(
        geometries,
        out_shape=out_shape,
        transform=transform,
        all_touched=all_touched,
        fill=fill,
        default_value=mask_value).astype('bool')


def shapes(image, mask=None, connectivity=4, transform=IDENTITY):
    """
    Return a generator of (polygon, value) for each each set of adjacent pixels
    of the same value.

    Parameters
    ----------
    image : numpy ndarray or rasterio Band object
        (RasterReader, bidx namedtuple).
        Data type must be one of rasterio.int16, rasterio.int32,
        rasterio.uint8, rasterio.uint16, or rasterio.float32.
    mask : numpy ndarray or rasterio Band object, optional
        Values of False or 0 will be excluded from feature generation
        Must evaluate to bool (rasterio.bool_ or rasterio.uint8)
    connectivity : int, optional
        Use 4 or 8 pixel connectivity for grouping pixels into features
    transform : Affine transformation, optional
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

    Notes
    -----
    The amount of memory used by this algorithm is proportional to the number
    and complexity of polygons produced.  This algorithm is most appropriate
    for simple thematic data.  Data with high pixel-to-pixel variability, such
    as imagery, may produce one polygon per pixel and consume large amounts of
    memory.

    """

    valid_dtypes = ('int16', 'int32', 'uint8', 'uint16', 'float32')

    if np.dtype(image.dtype).name not in valid_dtypes:
        raise ValueError('image dtype must be one of: %s'
                         % (', '.join(valid_dtypes)))

    if mask is not None and np.dtype(mask.dtype).name not in ('bool', 'uint8'):
        raise ValueError("Mask must be dtype rasterio.bool_ or rasterio.uint8")

    if connectivity not in (4, 8):
        raise ValueError("Connectivity Option must be 4 or 8")

    transform = guard_transform(transform)

    with rasterio.drivers():
        for s, v in _shapes(image, mask, connectivity, transform.to_gdal()):
            yield s, v


def sieve(image, size, out=None, output=None, mask=None, connectivity=4):
    """
    Replaces small polygons in `image` with the value of their largest
    neighbor.  Polygons are found for each set of neighboring pixels of the
    same value.

    Parameters
    ----------
    image : numpy ndarray or rasterio Band object
        (RasterReader, bidx namedtuple)
        Must be of type rasterio.int16, rasterio.int32, rasterio.uint8,
        rasterio.uint16, or rasterio.float32
    size : int
        minimum polygon size (number of pixels) to retain.
    out : numpy ndarray, optional
        Array of same shape and data type as `image` in which to store results.
    output : older alias for `out`, will be removed before 1.0.
    output : numpy ndarray, optional
    mask : numpy ndarray or rasterio Band object, optional
        Values of False or 0 will be excluded from feature generation
        Must evaluate to bool (rasterio.bool_ or rasterio.uint8)
    connectivity : int, optional
        Use 4 or 8 pixel connectivity for grouping pixels into features

    Returns
    -------
    out : numpy ndarray
        Result

    Notes
    -----
    GDAL only supports values that can be cast to 32-bit integers for this
    operation.

    The amount of memory used by this algorithm is proportional to the number
    and complexity of polygons found in the image.  This algorithm is most
    appropriate for simple thematic data.  Data with high pixel-to-pixel
    variability, such as imagery, may produce one polygon per pixel and consume
    large amounts of memory.

    """

    valid_dtypes = ('int16', 'int32', 'uint8', 'uint16')

    if np.dtype(image.dtype).name not in valid_dtypes:
        valid_types_str = ', '.join(('rasterio.{0}'.format(t) for t
                                     in valid_dtypes))
        raise ValueError('image dtype must be one of: %s' % valid_types_str)

    if size <= 0:
        raise ValueError('size must be greater than 0')
    elif type(size) == float:
        raise ValueError('size must be an integer number of pixels')
    elif size > (image.shape[0] * image.shape[1]):
        raise ValueError('size must be smaller than size of image')

    if connectivity not in (4, 8):
        raise ValueError('connectivity must be 4 or 8')

    if mask is not None:
        if np.dtype(mask.dtype) not in ('bool', 'uint8'):
            raise ValueError('Mask must be dtype rasterio.bool_ or '
                             'rasterio.uint8')
        elif mask.shape != image.shape:
            raise ValueError('mask shape must be same as image shape')

    # Start moving users over to 'out'.
    if output is not None:
        warnings.warn(
            "The 'output' keyword arg has been superceded by 'out' "
            "and will be removed before Rasterio 1.0.",
            FutureWarning,
            stacklevel=2)
    
    out = out if out is not None else output
    if out is None:
        if isinstance(image, tuple):
            out = np.zeros(image.shape, image.dtype)
        else:
            out = np.zeros_like(image)
    else:
        if np.dtype(image.dtype).name != np.dtype(out.dtype).name:
            raise ValueError('out raster must match dtype of image')
        elif out.shape != image.shape:
            raise ValueError('out raster shape must be same as image shape')

    with rasterio.drivers():
        _sieve(image, size, out, mask, connectivity)
        return out


def rasterize(
        shapes,
        out_shape=None,
        fill=0,
        out=None,
        output=None,
        transform=IDENTITY,
        all_touched=False,
        default_value=1,
        dtype=None):
    """
    Returns an image array with input geometries burned in.

    Parameters
    ----------
    shapes : iterable of (geometry, value) pairs or iterable over
        geometries. `geometry` can either be an object that implements
        the geo interface or GeoJSON-like object.
    out_shape : tuple or list
        Shape of output numpy ndarray.
    fill : int or float, optional
        Used as fill value for all areas not covered by input
        geometries.
    out : numpy ndarray, optional
        Array of same shape and data type as `image` in which to store
        results.
    output : older alias for `out`, will be removed before 1.0.
    transform : Affine transformation object, optional
        Transformation from pixel coordinates of `image` to the
        coordinate system of the input `shapes`. See the `transform`
        property of dataset objects.
    all_touched : boolean, optional
        If True, all pixels touched by geometries will be burned in.  If
        false, only pixels whose center is within the polygon or that
        are selected by Bresenham's line algorithm will be burned in.
    default_value : int or float, optional
        Used as value for all geometries, if not provided in `shapes`.
    dtype : rasterio or numpy data type, optional
        Used as data type for results, if `out` is not provided.

    Returns
    -------
    out : numpy ndarray
        Results

    Notes
    -----
    Valid data types for `fill`, `default_value`, `out`, `dtype` and
    shape values are rasterio.int16, rasterio.int32, rasterio.uint8,
    rasterio.uint16, rasterio.uint32, rasterio.float32,
    rasterio.float64.

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
        warnings.warn(
            "The 'output' keyword arg has been superceded by 'out' "
            "and will be removed before Rasterio 1.0.",
            FutureWarning,
            stacklevel=2)
    out = out if out is not None else output
    if out is not None:
        if np.dtype(out.dtype).name not in valid_dtypes:
            raise ValueError('Output image dtype must be one of: %s'
                             % (', '.join(valid_dtypes)))
        if not can_cast_dtype(shape_values, out.dtype):
            raise ValueError('shape values cannot be cast to dtype of output '
                             'image')

    elif out_shape is not None:
        out = np.empty(out_shape, dtype=dtype)
        out.fill(fill)
    else:
        raise ValueError('Either an output shape or image must be provided')

    transform = guard_transform(transform)

    with rasterio.drivers():
        _rasterize(valid_shapes, out, transform.to_gdal(), all_touched)

    return out


def bounds(geometry):
    """Returns a (minx, miny, maxx, maxy) bounding box.  From Fiona 1.4.8.
    Modified to return bbox from geometry if available.

    Parameters
    ----------
    geometry: GeoJSON-like feature, feature collection, or geometry.

    Returns
    -------
    tuple
        Bounding box: (minx, miny, maxx, maxy)
    """

    if 'bbox' in geometry:
        return tuple(geometry['bbox'])

    geom = geometry.get('geometry') or geometry
    return _bounds(geom)

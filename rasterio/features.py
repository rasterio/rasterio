"""Functions for working with features in a raster dataset."""

import json
import logging
import time
import warnings

import numpy as np

import rasterio
from rasterio._features import _shapes, _sieve, _rasterize, _bounds
from rasterio.transform import IDENTITY, guard_transform
from rasterio.dtypes import validate_dtype, can_cast_dtype, get_minimum_dtype


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

    # Start moving users over to 'out'.
    if output is not None:
        warnings.warn(
            "The 'output' keyword arg has been superceded by 'out' "
            "and will be removed before Rasterio 1.0.",
            FutureWarning,
            stacklevel=2)  # pragma: no cover
    
    out = out if out is not None else output

    if out is None:
        out = np.zeros(image.shape, image.dtype)

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

    valid_dtypes = (
        'int16', 'int32', 'uint8', 'uint16', 'uint32', 'float32', 'float64'
    )

    def format_invalid_dtype(param):
        return '{0} dtype must be one of: {1}'.format(
            param, ', '.join(valid_dtypes)
        )

    def format_cast_error(param, dtype):
        return '{0} cannot be cast to specified dtype: {1}'.format(param, dtype)


    if fill != 0:
        fill_array = np.array([fill])
        if not validate_dtype(fill_array, valid_dtypes):
            raise ValueError(format_invalid_dtype('fill'))

        if dtype is not None and not can_cast_dtype(fill_array, dtype):
            raise ValueError(format_cast_error('fill', dtype))

    if default_value != 1:
        default_value_array = np.array([default_value])
        if not validate_dtype(default_value_array, valid_dtypes):
            raise ValueError(format_invalid_dtype('default_value'))

        if dtype is not None and not can_cast_dtype(default_value_array, dtype):
            raise ValueError(format_cast_error('default_vaue', dtype))

    if dtype is not None and np.dtype(dtype).name not in valid_dtypes:
        raise ValueError(format_invalid_dtype('dtype'))


    valid_shapes = []
    shape_values = []
    for index, item in enumerate(shapes):
        if isinstance(item, (tuple, list)):
            geom, value = item
        else:
            geom = item
            value = default_value
        geom = getattr(geom, '__geo_interface__', None) or geom

        #not isinstance(geom, dict) or
        if 'type' in geom or 'coordinates' in geom:
            valid_shapes.append((geom, value))
            shape_values.append(value)

        else:
            raise ValueError(
                'Invalid geometry object at index {0}'.format(index)
            )

    if not valid_shapes:
        raise ValueError('No valid geometry objects found for rasterize')

    shape_values = np.array(shape_values)

    if not validate_dtype(shape_values, valid_dtypes):
        raise ValueError(format_invalid_dtype('shape values'))

    if dtype is None:
        dtype = get_minimum_dtype(np.append(shape_values, fill))

    elif not can_cast_dtype(shape_values, dtype):
        raise ValueError(format_cast_error('shape values', dtype))

    if output is not None:
        warnings.warn(
            "The 'output' keyword arg has been superceded by 'out' "
            "and will be removed before Rasterio 1.0.",
            FutureWarning,
            stacklevel=2) # pragma: no cover

    out = out if out is not None else output
    if out is not None:
        if np.dtype(out.dtype).name not in valid_dtypes:
            raise ValueError(format_invalid_dtype('out'))

        if not can_cast_dtype(shape_values, out.dtype):
            raise ValueError(format_cast_error('shape values', out.dtype.name))

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

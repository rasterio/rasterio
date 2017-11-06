"""Functions for working with features in a raster dataset."""


import logging

import numpy as np

from rasterio._features import _shapes, _sieve, _rasterize, _bounds
from rasterio.dtypes import validate_dtype, can_cast_dtype, get_minimum_dtype
from rasterio.env import ensure_env
from rasterio.transform import IDENTITY, guard_transform
from rasterio.windows import Window

log = logging.getLogger(__name__)


@ensure_env
def geometry_mask(
        geometries,
        out_shape,
        transform,
        all_touched=False,
        invert=False):
    """Create a mask from shapes.

    By default, mask is intended for use as a
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


@ensure_env
def shapes(image, mask=None, connectivity=4, transform=IDENTITY):
    """Yield (polygon, value for each set of adjacent pixels of the same value.

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

    Yields
    -------
    tuple
        A pair of (polygon, value) for each feature found in the image.
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
    for s, v in _shapes(image, mask, connectivity, transform.to_gdal()):
        yield s, v


@ensure_env
def sieve(image, size, out=None, mask=None, connectivity=4):
    """Replace small polygons in `image` with value of their largest neighbor.

    Polygons are found for each set of neighboring pixels of the same value.

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

    if out is None:
        out = np.zeros(image.shape, image.dtype)
    _sieve(image, size, out, mask, connectivity)
    return out


@ensure_env
def rasterize(
        shapes,
        out_shape=None,
        fill=0,
        out=None,
        transform=IDENTITY,
        all_touched=False,
        default_value=1,
        dtype=None):
    """Return an image array with input geometries burned in.

    Parameters
    ----------
    shapes : iterable of (geometry, value) pairs or iterable over
        geometries. `geometry` can either be an object that implements
        the geo interface or GeoJSON-like object.
    out_shape : tuple or list with 2 integers
        Shape of output numpy ndarray.
    fill : int or float, optional
        Used as fill value for all areas not covered by input
        geometries.
    out : numpy ndarray, optional
        Array of same shape and data type as `image` in which to store
        results.
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

        # geom must be a valid GeoJSON geometry type and non-empty
        if not is_valid_geom(geom):
            raise ValueError(
                'Invalid geometry object at index {0}'.format(index)
            )

        valid_shapes.append((geom, value))
        shape_values.append(value)

    if not valid_shapes:
        raise ValueError('No valid geometry objects found for rasterize')

    shape_values = np.array(shape_values)

    if not validate_dtype(shape_values, valid_dtypes):
        raise ValueError(format_invalid_dtype('shape values'))

    if dtype is None:
        dtype = get_minimum_dtype(np.append(shape_values, fill))

    elif not can_cast_dtype(shape_values, dtype):
        raise ValueError(format_cast_error('shape values', dtype))

    if out is not None:
        if np.dtype(out.dtype).name not in valid_dtypes:
            raise ValueError(format_invalid_dtype('out'))

        if not can_cast_dtype(shape_values, out.dtype):
            raise ValueError(format_cast_error('shape values', out.dtype.name))

    elif out_shape is not None:

        if len(out_shape) != 2:
            raise ValueError('Invalid out_shape, must be 2D')

        out = np.empty(out_shape, dtype=dtype)
        out.fill(fill)

    else:
        raise ValueError('Either an out_shape or image must be provided')

    if min(out.shape) == 0:
        raise ValueError("width and height must be > 0")

    transform = guard_transform(transform)
    _rasterize(valid_shapes, out, transform.to_gdal(), all_touched)
    return out


def bounds(geometry, north_up=True):
    """Return a (left, bottom, right, top) bounding box.

    From Fiona 1.4.8. Modified to return bbox from geometry if available.

    Parameters
    ----------
    geometry: GeoJSON-like feature, feature collection, or geometry.

    Returns
    -------
    tuple
        Bounding box: (left, bottom, right, top)
    """
    if 'bbox' in geometry:
        return tuple(geometry['bbox'])

    geom = geometry.get('geometry') or geometry
    return _bounds(geom, north_up=north_up)


def geometry_window(raster, shapes, pad_x=0, pad_y=0, north_up=True,
                    pixel_precision=3):
    """Calculate the window within the raster that fits the bounds of the 
    geometry plus optional padding.  The window is the outermost pixel indices
    that contain the geometry (floor of offsets, ceiling of width and height).
    
    If shapes do not overlap raster, a WindowError is raised.

    Parameters
    ----------
    raster: rasterio RasterReader object
        Raster for which the mask will be created.
    shapes: iterable over geometries.
        A geometry is a GeoJSON-like object or implements the geo interface.
        Must be in same coordinate system as raster.
    pad_x: float
        Amount of padding (as fraction of raster's x pixel size) to add to left 
        and right side of bounds.
    pad_y: float
        Amount of padding (as fraction of raster's y pixel size) to add to top 
        and bottom of bounds.
    north_up: bool
        If True (default), the origin point of the raster's transform is the 
        northernmost point and y pixel values are negative.
    pixel_precision: int
        Number of places of rounding precision for evaluating bounds of shapes.

    Returns
    -------
    window: rasterio.windows.Window instance
    """

    if pad_x:
        pad_x = abs(pad_x * raster.res[0])

    if pad_y:
        pad_y = abs(pad_y * raster.res[1])

    all_bounds = [bounds(shape, north_up=north_up) for shape in shapes]
    lefts, bottoms, rights, tops = zip(*all_bounds)

    left = min(lefts) - pad_x
    right = max(rights) + pad_x

    if north_up:
        bottom = min(bottoms) - pad_y
        top = max(tops) + pad_y
    else:
        bottom = max(bottoms) + pad_y
        top = min(tops) - pad_y

    window = raster.window(left, bottom, right, top)
    window = window.round_offsets(op='floor', pixel_precision=pixel_precision)
    window = window.round_shape(op='ceil', pixel_precision=pixel_precision)

    # Make sure that window overlaps raster
    raster_window = Window(0, 0, raster.height, raster.width)

    # This will raise a WindowError if windows do not overlap
    window = window.intersection(raster_window)

    return window


def is_valid_geom(geom):
    """
    Checks to see if geometry is a valid GeoJSON geometry type or
    GeometryCollection.

    Geometries must be non-empty, and have at least x, y coordinates.

    Note: only the first coordinate is checked for validity.
    
    Parameters
    ----------
    geom: an object that implements the geo interface or GeoJSON-like object

    Returns
    -------
    bool: True if object is a valid GeoJSON geometry type
    """
    
    geom_types = {'Point', 'MultiPoint', 'LineString', 'MultiLineString',
                  'Polygon', 'MultiPolygon'}

    if 'type' not in geom:
        return False

    try:
        geom_type = geom['type']
        if geom_type not in geom_types.union({'GeometryCollection'}):
            return False

    except TypeError:
        return False

    if geom_type in geom_types:
        if 'coordinates' not in geom:
            return False

        coords = geom['coordinates']

        if geom_type == 'Point':
            # Points must have at least x, y
            return len(coords) >= 2

        if geom_type == 'MultiPoint':
            # Multi points must have at least one point with at least x, y
            return len(coords) > 0 and len(coords[0]) >= 2

        if geom_type == 'LineString':
            # Lines must have at least 2 coordinates and at least x, y for
            # a coordinate
            return len(coords) >= 2 and len(coords[0]) >= 2

        if geom_type == 'MultiLineString':
            # Multi lines must have at least one LineString
            return (len(coords) > 0 and len(coords[0]) >= 2 and
                    len(coords[0][0]) >=2)

        if geom_type == 'Polygon':
            # Polygons must have at least 1 ring, with at least 4 coordinates,
            # with at least x, y for a coordinate
            return (len(coords) > 0 and len(coords[0]) >= 4 and
                    len(coords[0][0]) >=2)

        if geom_type == 'MultiPolygon':
            # Muti polygons must have at least one Polygon
            return (len(coords) > 0 and len(coords[0]) > 0 and
                    len(coords[0][0]) >= 4 and len(coords[0][0][0]) >=2)

    if geom_type == 'GeometryCollection':
        if not 'geometries' in geom:
            return False

        if not len(geom['geometries']) > 0:
            # While technically valid according to GeoJSON spec, an empty
            # GeometryCollection will cause issues if used in rasterio
            return False

        for g in geom['geometries']:
            if not is_valid_geom(g):
                return False  # short-circuit and fail early

    return True

"""Functions for working with features in a raster dataset."""


import logging
import math
import os
import warnings

import numpy as np

import rasterio
from rasterio.dtypes import validate_dtype, can_cast_dtype, get_minimum_dtype
from rasterio.enums import MergeAlg
from rasterio.env import ensure_env
from rasterio.errors import ShapeSkipWarning
from rasterio._features import _shapes, _sieve, _rasterize, _bounds
from rasterio import warp
from rasterio.rio.helpers import coords
from rasterio.transform import Affine
from rasterio.transform import IDENTITY, guard_transform, rowcol
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
        Transformation from pixel coordinates of `source` to the
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
    numpy ndarray of type 'bool'
        Result

    Notes
    -----
    See rasterize() for performance notes.

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
def shapes(source, mask=None, connectivity=4, transform=IDENTITY):
    """Get shapes and values of connected regions in a dataset or array.

    Parameters
    ----------
    source : array, dataset object, Band, or tuple(dataset, bidx)
        Data type must be one of rasterio.int16, rasterio.int32,
        rasterio.uint8, rasterio.uint16, or rasterio.float32.
    mask : numpy ndarray or rasterio Band object, optional
        Must evaluate to bool (rasterio.bool_ or rasterio.uint8). Values
        of False or 0 will be excluded from feature generation.  Note
        well that this is the inverse sense from Numpy's, where a mask
        value of True indicates invalid data in an array. If `source` is
        a Numpy masked array and `mask` is None, the source's mask will
        be inverted and used in place of `mask`.
    connectivity : int, optional
        Use 4 or 8 pixel connectivity for grouping pixels into features
    transform : Affine transformation, optional
        If not provided, feature coordinates will be generated based on
        pixel coordinates

    Yields
    -------
    polygon, value
        A pair of (polygon, value) for each feature found in the image.
        Polygons are GeoJSON-like dicts and the values are the
        associated value from the image, in the data type of the image.
        Note: due to floating point precision issues, values returned
        from a floating point image may not exactly match the original
        values.

    Notes
    -----
    The amount of memory used by this algorithm is proportional to the
    number and complexity of polygons produced.  This algorithm is most
    appropriate for simple thematic data.  Data with high pixel-to-pixel
    variability, such as imagery, may produce one polygon per pixel and
    consume large amounts of memory.

    Because the low-level implementation uses either an int32 or float32
    buffer, uint32 and float64 data cannot be operated on without
    truncation issues.

    """
    if hasattr(source, 'mask') and mask is None:
        mask = ~source.mask
        source = source.data

    transform = guard_transform(transform)
    for s, v in _shapes(source, mask, connectivity, transform):
        yield s, v


@ensure_env
def sieve(source, size, out=None, mask=None, connectivity=4):
    """Replace small polygons in `source` with value of their largest neighbor.

    Polygons are found for each set of neighboring pixels of the same value.

    Parameters
    ----------
    source : array or dataset object opened in 'r' mode or Band or tuple(dataset, bidx)
        Must be of type rasterio.int16, rasterio.int32, rasterio.uint8,
        rasterio.uint16, or rasterio.float32
    size : int
        minimum polygon size (number of pixels) to retain.
    out : numpy ndarray, optional
        Array of same shape and data type as `source` in which to store results.
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
        out = np.zeros(source.shape, source.dtype)
    _sieve(source, size, out, mask, connectivity)
    return out


@ensure_env
def rasterize(
        shapes,
        out_shape=None,
        fill=0,
        out=None,
        transform=IDENTITY,
        all_touched=False,
        merge_alg=MergeAlg.replace,
        default_value=1,
        dtype=None):
    """Return an image array with input geometries burned in.

    Warnings will be raised for any invalid or empty geometries, and
    an exception will be raised if there are no valid shapes
    to rasterize.

    Parameters
    ----------
    shapes : iterable of (`geometry`, `value`) pairs or iterable over
        geometries. The `geometry` can either be an object that
        implements the geo interface or GeoJSON-like object. If no
        `value` is provided the `default_value` will be used. If `value`
        is `None` the `fill` value will be used.
    out_shape : tuple or list with 2 integers
        Shape of output numpy ndarray.
    fill : int or float, optional
        Used as fill value for all areas not covered by input
        geometries.
    out : numpy ndarray, optional
        Array of same shape and data type as `source` in which to store
        results.
    transform : Affine transformation object, optional
        Transformation from pixel coordinates of `source` to the
        coordinate system of the input `shapes`. See the `transform`
        property of dataset objects.
    all_touched : boolean, optional
        If True, all pixels touched by geometries will be burned in.  If
        false, only pixels whose center is within the polygon or that
        are selected by Bresenham's line algorithm will be burned in.
    merge_alg : MergeAlg, optional
        Merge algorithm to use. One of:
            MergeAlg.replace (default):
                the new value will overwrite the existing value.
            MergeAlg.add:
                the new value will be added to the existing raster.
    default_value : int or float, optional
        Used as value for all geometries, if not provided in `shapes`.
    dtype : rasterio or numpy data type, optional
        Used as data type for results, if `out` is not provided.

    Returns
    -------
    numpy ndarray
        If `out` was not None then `out` is returned, it will have been
        modified in-place. If `out` was None, this will be a new array.

    Notes
    -----
    Valid data types for `fill`, `default_value`, `out`, `dtype` and
    shape values are "int16", "int32", "uint8", "uint16", "uint32",
    "float32", and "float64".

    This function requires significant memory resources. The shapes
    iterator will be materialized to a Python list and another C copy of
    that list will be made. The `out` array will be copied and
    additional temporary raster memory equal to 2x the smaller of `out`
    data or GDAL's max cache size (controlled by GDAL_CACHEMAX, default
    is 5% of the computer's physical memory) is required.

    If GDAL max cache size is smaller than the output data, the array of
    shapes will be iterated multiple times. Performance is thus a linear
    function of buffer size. For maximum speed, ensure that
    GDAL_CACHEMAX is larger than the size of `out` or `out_shape`.

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
            if value is None:
                value = fill
        else:
            geom = item
            value = default_value
        geom = getattr(geom, '__geo_interface__', None) or geom

        if is_valid_geom(geom):
            shape_values.append(value)

            geom_type = geom['type']

            if geom_type == 'GeometryCollection':
                # GeometryCollections need to be handled as individual parts to
                # avoid holes in output:
                # https://github.com/mapbox/rasterio/issues/1253.
                # Only 1-level deep since GeoJSON spec discourages nested
                # GeometryCollections
                for part in geom['geometries']:
                    valid_shapes.append((part, value))

            elif geom_type == 'MultiPolygon':
                # Same issue as above
                for poly in geom['coordinates']:
                    valid_shapes.append(({'type': 'Polygon', 'coordinates': poly}, value))

            else:
                valid_shapes.append((geom, value))

        else:
            # invalid or empty geometries are skipped and raise a warning instead
            warnings.warn('Invalid or empty shape {} at index {} will not be rasterized.'.format(geom, index), ShapeSkipWarning)

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
    _rasterize(valid_shapes, out, transform, all_touched, merge_alg)
    return out


def bounds(geometry, north_up=True, transform=None):
    """Return a (left, bottom, right, top) bounding box.

    From Fiona 1.4.8. Modified to return bbox from geometry if available.

    Parameters
    ----------
    geometry: GeoJSON-like feature (implements __geo_interface__),
              feature collection, or geometry.

    Returns
    -------
    tuple
        Bounding box: (left, bottom, right, top)
    """

    geometry = getattr(geometry, '__geo_interface__', None) or geometry

    if 'bbox' in geometry:
        return tuple(geometry['bbox'])

    geom = geometry.get('geometry') or geometry

    # geometry must be a geometry, GeometryCollection, or FeatureCollection
    if not ('coordinates' in geom or 'geometries' in geom or 'features' in geom):
        raise ValueError(
            "geometry must be a GeoJSON-like geometry, GeometryCollection, "
            "or FeatureCollection"
        )

    return _bounds(geom, north_up=north_up, transform=transform)


def geometry_window(
    dataset,
    shapes,
    pad_x=0,
    pad_y=0,
    north_up=None,
    rotated=None,
    pixel_precision=None,
    boundless=False,
):
    """Calculate the window within the raster that fits the bounds of
    the geometry plus optional padding.  The window is the outermost
    pixel indices that contain the geometry (floor of offsets, ceiling
    of width and height).

    If shapes do not overlap raster, a WindowError is raised.

    Parameters
    ----------
    dataset : dataset object opened in 'r' mode
        Raster for which the mask will be created.
    shapes : iterable over geometries.
        A geometry is a GeoJSON-like object or implements the geo
        interface.  Must be in same coordinate system as dataset.
    pad_x : float
        Amount of padding (as fraction of raster's x pixel size) to add
        to left and right side of bounds.
    pad_y : float
        Amount of padding (as fraction of raster's y pixel size) to add
        to top and bottom of bounds.
    north_up : optional
        This parameter is ignored since version 1.2.1. A deprecation
        warning will be emitted in 1.3.0.
    rotated : optional
        This parameter is ignored since version 1.2.1. A deprecation
        warning will be emitted in 1.3.0.
    pixel_precision : int or float, optional
        Number of places of rounding precision or absolute precision for
        evaluating bounds of shapes.
    boundless : bool, optional
        Whether to allow a boundless window or not.

    Returns
    -------
    rasterio.windows.Window

    """

    if pad_x:
        pad_x = abs(pad_x * dataset.res[0])

    if pad_y:
        pad_y = abs(pad_y * dataset.res[1])

    all_bounds = [bounds(shape) for shape in shapes]

    xs = [
        x
        for (left, bottom, right, top) in all_bounds
        for x in (left - pad_x, right + pad_x, right + pad_x, left - pad_x)
    ]
    ys = [
        y
        for (left, bottom, right, top) in all_bounds
        for y in (top + pad_y, top + pad_y, bottom - pad_x, bottom - pad_x)
    ]

    rows1, cols1 = rowcol(
        dataset.transform, xs, ys, op=math.floor, precision=pixel_precision
    )

    if isinstance(rows1, (int, float)):
        rows1 = [rows1]
    if isinstance(cols1, (int, float)):
        cols1 = [cols1]

    rows2, cols2 = rowcol(
        dataset.transform, xs, ys, op=math.ceil, precision=pixel_precision
    )

    if isinstance(rows2, (int, float)):
        rows2 = [rows2]
    if isinstance(cols2, (int, float)):
        cols2 = [cols2]

    rows = rows1 + rows2
    cols = cols1 + cols2

    row_start, row_stop = min(rows), max(rows)
    col_start, col_stop = min(cols), max(cols)

    window = Window(
        col_off=col_start,
        row_off=row_start,
        width=max(col_stop - col_start, 0.0),
        height=max(row_stop - row_start, 0.0),
    )

    # Make sure that window overlaps raster
    raster_window = Window(0, 0, dataset.width, dataset.height)
    if not boundless:
        window = window.intersection(raster_window)

    return window


def is_valid_geom(geom):
    """
    Checks to see if geometry is a valid GeoJSON geometry type or
    GeometryCollection.  Geometry must be GeoJSON or implement the geo
    interface.

    Geometries must be non-empty, and have at least x, y coordinates.

    Note: only the first coordinate is checked for validity.

    Parameters
    ----------
    geom: an object that implements the geo interface or GeoJSON-like object

    Returns
    -------
    bool: True if object is a valid GeoJSON geometry type
    """

    geom_types = {'Point', 'MultiPoint', 'LineString', 'LinearRing',
                  'MultiLineString', 'Polygon', 'MultiPolygon'}

    geom = getattr(geom, '__geo_interface__', None) or geom

    try:
        geom_type = geom["type"]
        if geom_type not in geom_types.union({'GeometryCollection'}):
            return False

    except (KeyError, TypeError):
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

        if geom_type == 'LinearRing':
            # Rings must have at least 4 coordinates and at least x, y for
            # a coordinate
            return len(coords) >= 4 and len(coords[0]) >= 2

        if geom_type == 'MultiLineString':
            # Multi lines must have at least one LineString
            return (len(coords) > 0 and len(coords[0]) >= 2 and
                    len(coords[0][0]) >= 2)

        if geom_type == 'Polygon':
            # Polygons must have at least 1 ring, with at least 4 coordinates,
            # with at least x, y for a coordinate
            return (len(coords) > 0 and len(coords[0]) >= 4 and
                    len(coords[0][0]) >= 2)

        if geom_type == 'MultiPolygon':
            # Muti polygons must have at least one Polygon
            return (len(coords) > 0 and len(coords[0]) > 0 and
                    len(coords[0][0]) >= 4 and len(coords[0][0][0]) >= 2)

    if geom_type == 'GeometryCollection':
        if 'geometries' not in geom:
            return False

        if not len(geom['geometries']) > 0:
            # While technically valid according to GeoJSON spec, an empty
            # GeometryCollection will cause issues if used in rasterio
            return False

        for g in geom['geometries']:
            if not is_valid_geom(g):
                return False  # short-circuit and fail early

    return True


def dataset_features(
        src,
        bidx=None,
        sampling=1,
        band=True,
        as_mask=False,
        with_nodata=False,
        geographic=True,
        precision=-1):
    """Yield GeoJSON features for the dataset

    The geometries are polygons bounding contiguous regions of the same raster value.

    Parameters
    ----------
    src: Rasterio Dataset

    bidx: int
        band index

    sampling: int (DEFAULT: 1)
        Inverse of the sampling fraction; a value of 10 decimates

    band: boolean (DEFAULT: True)
        extract features from a band (True) or a mask (False)

    as_mask: boolean (DEFAULT: False)
        Interpret band as a mask and output only one class of valid data shapes?

    with_nodata: boolean (DEFAULT: False)
        Include nodata regions?

    geographic: str (DEFAULT: True)
        Output shapes in EPSG:4326? Otherwise use the native CRS.

    precision: int (DEFAULT: -1)
        Decimal precision of coordinates. -1 for full float precision output

    Yields
    ------
    GeoJSON-like Feature dictionaries for shapes found in the given band
    """
    if bidx is not None and bidx > src.count:
        raise ValueError('bidx is out of range for raster')

    img = None
    msk = None

    # Adjust transforms.
    transform = src.transform
    if sampling > 1:
        # Determine the target shape (to decimate)
        shape = (int(math.ceil(src.height / sampling)),
                 int(math.ceil(src.width / sampling)))

        # Calculate independent sampling factors
        x_sampling = src.width / shape[1]
        y_sampling = src.height / shape[0]

        # Decimation of the raster produces a georeferencing
        # shift that we correct with a translation.
        transform *= Affine.translation(
            src.width % x_sampling, src.height % y_sampling)

        # And follow by scaling.
        transform *= Affine.scale(x_sampling, y_sampling)

    # Most of the time, we'll use the valid data mask.
    # We skip reading it if we're extracting every possible
    # feature (even invalid data features) from a band.
    if not band or (band and not as_mask and not with_nodata):
        if sampling == 1:
            msk = src.read_masks(bidx)
        else:
            msk_shape = shape
            if bidx is None:
                msk = np.zeros(
                    (src.count,) + msk_shape, 'uint8')
            else:
                msk = np.zeros(msk_shape, 'uint8')
            msk = src.read_masks(bidx, msk)

        if bidx is None:
            msk = np.logical_or.reduce(msk).astype('uint8')

        # Possibly overridden below.
        img = msk

    # Read the band data unless the --mask option is given.
    if band:
        if sampling == 1:
            img = src.read(bidx, masked=False)
        else:
            img = np.zeros(
                shape,
                dtype=src.dtypes[src.indexes.index(bidx)])
            img = src.read(bidx, img, masked=False)

    # If as_mask option was given, convert the image
    # to a binary image. This reduces the number of shape
    # categories to 2 and likely reduces the number of
    # shapes.
    if as_mask:
        tmp = np.ones_like(img, 'uint8') * 255
        tmp[img == 0] = 0
        img = tmp
        if not with_nodata:
            msk = tmp

    # Prepare keyword arguments for shapes().
    kwargs = {'transform': transform}
    if not with_nodata:
        kwargs['mask'] = msk

    src_basename = os.path.basename(src.name)

    # Yield GeoJSON features.
    for i, (g, val) in enumerate(
            rasterio.features.shapes(img, **kwargs)):
        if geographic:
            g = warp.transform_geom(
                src.crs, 'EPSG:4326', g,
                antimeridian_cutting=True, precision=precision)
        xs, ys = zip(*coords(g))
        yield {
            'type': 'Feature',
            'id': "{0}:{1}".format(src_basename, i),
            'properties': {
                'val': val,
                'filename': src_basename
            },
            'bbox': [min(xs), min(ys), max(xs), max(ys)],
            'geometry': g
        }

"""Raster warping and reprojection"""

from __future__ import absolute_import

from math import ceil
import warnings

from affine import Affine
import numpy as np

from rasterio._base import _transform
from rasterio._warp import _transform_geom, _reproject, Resampling
from rasterio.transform import guard_transform


RESAMPLING = Resampling
warnings.warn(
    "RESAMPLING is deprecated, use Resampling instead.", DeprecationWarning)


def transform(src_crs, dst_crs, xs, ys, zs=None):
    """
    Transform vectors of x, y and optionally z from source
    coordinate reference system into target.

    Parameters
    ------------
    src_crs: dict
        Source coordinate reference system, in rasterio dict format.
        Example: {'init': 'EPSG:4326'}
    dst_crs: dict
        Target coordinate reference system.
    xs: array_like
        Contains x values.  Will be cast to double floating point values.
    ys:  array_like
        Contains y values.
    zs: array_like, optional
        Contains z values.  Assumed to be all 0 if absent.

    Returns
    ---------
    out: tuple of array_like, (xs, ys, [zs])
    Tuple of x, y, and optionally z vectors, transformed into the target
    coordinate reference system.
    """
    return _transform(src_crs, dst_crs, xs, ys, zs)


def transform_geom(
        src_crs,
        dst_crs,
        geom,
        antimeridian_cutting=False,
        antimeridian_offset=10.0,
        precision=-1):
    """
    Transform geometry from source coordinate reference system into target.

    Parameters
    ------------
    src_crs: dict
        Source coordinate reference system, in rasterio dict format.
        Example: {'init': 'EPSG:4326'}
    dst_crs: dict
        Target coordinate reference system.
    geom: GeoJSON like dict object
    antimeridian_cutting: bool, optional
        If True, cut geometries at the antimeridian, otherwise geometries will
        not be cut (default).
    antimeridian_offset: float
        Offset from the antimeridian in degrees (default: 10) within which
        any geometries will be split.
    precision: float
        If >= 0, geometry coordinates will be rounded to this number of decimal
        places after the transform operation, otherwise original coordinate
        values will be preserved (default).

    Returns
    ---------
    out: GeoJSON like dict object
        Transformed geometry in GeoJSON dict format
    """

    return _transform_geom(
        src_crs,
        dst_crs,
        geom,
        antimeridian_cutting,
        antimeridian_offset,
        precision)


def transform_bounds(src_crs, dst_crs, left, bottom, right, top, densify_pts=21):
    """
    Transforms bounds from src_crs to dst_crs, optionally densifying the edges
    (to account for nonlinear transformations along these edges) and extracting
    the outermost bounds.

    Note: this does not account for the antimeridian.

    Parameters
    ----------
    src_crs: dict
        Source coordinate reference system, in rasterio dict format.
        Example: {'init': 'EPSG:4326'}
    dst_crs: dict
        Target coordinate reference system.
    left, bottom, right, top: float
        Bounding coordinates in src_crs, from the bounds property of a raster.
    densify_pts: uint, optional
        Number of points to add to each edge to account for nonlinear
        edges produced by the transform process.  Large numbers will produce
        worse performance.  Default: 21 (gdal default).

    Returns
    -------
    left, bottom, right, top: float
        Outermost coordinates in target coordinate reference system.
    """

    if densify_pts < 0:
        raise ValueError('densify parameter must be >= 0')

    in_xs = []
    in_ys = []

    if densify_pts > 0:
        densify_factor = 1.0 / float(densify_pts + 1)

        # Add points along outer edges.
        for x in (left, right):
            in_xs.extend([x] * (densify_pts + 2))
            in_ys.extend(
                bottom + np.arange(0, densify_pts + 2, dtype=np.float32)
                * ((top - bottom) * densify_factor)
            )

        for y in (bottom, top):
            in_xs.extend(
                left + np.arange(1, densify_pts + 1, dtype=np.float32)
                * ((right - left) * densify_factor)
            )
            in_ys.extend([y] * densify_pts)

    else:
        in_xs = [left, left, right, right]
        in_ys = [bottom, top, bottom, top]

    xs, ys = transform(src_crs, dst_crs, in_xs, in_ys)
    return (min(xs), min(ys), max(xs), max(ys))


def reproject(
        source,
        destination,
        src_transform=None,
        src_crs=None,
        src_nodata=None,
        dst_transform=None,
        dst_crs=None,
        dst_nodata=None,
        resampling=Resampling.nearest,
        **kwargs):
    """
    Reproject a source raster to a destination raster.

    If the source and destination are ndarrays, coordinate reference
    system definitions and affine transformation parameters are required
    for reprojection.

    If the source and destination are rasterio Bands, shorthand for
    bands of datasets on disk, the coordinate reference systems and
    transforms will be read from the appropriate datasets.

    Parameters
    ------------
    source: ndarray or rasterio Band
        Source raster.
    destination: ndarray or rasterio Band
        Target raster.
    src_transform: affine transform object, optional
        Source affine transformation.  Required if source and destination
        are ndarrays.  Will be derived from source if it is a rasterio Band.
    src_crs: dict, optional
        Source coordinate reference system, in rasterio dict format.
        Required if source and destination are ndarrays.
        Will be derived from source if it is a rasterio Band.
        Example: {'init': 'EPSG:4326'}
    src_nodata: int or float, optional
        The source nodata value.  Pixels with this value will not be used
        for interpolation.  If not set, it will be default to the
        nodata value of the source image if a masked ndarray or rasterio band,
        if available.  Must be provided if dst_nodata is not None.
    dst_transform: affine transform object, optional
        Target affine transformation.  Required if source and destination
        are ndarrays.  Will be derived from target if it is a rasterio Band.
    dst_crs: dict, optional
        Target coordinate reference system.  Required if source and destination
        are ndarrays.  Will be derived from target if it is a rasterio Band.
    dst_nodata: int or float, optional
        The nodata value used to initialize the destination; it will remain
        in all areas not covered by the reprojected source.  Defaults to the
        nodata value of the destination image (if set), the value of
        src_nodata, or 0 (GDAL default).
    resampling: int
        Resampling method to use.  One of the following:
            Resampling.nearest,
            Resampling.bilinear,
            Resampling.cubic,
            Resampling.cubic_spline,
            Resampling.lanczos,
            Resampling.average,
            Resampling.mode
    kwargs:  dict, optional
        Additional arguments passed to transformation function.

    Returns
    ---------
    out: None
        Output is written to destination.
    """

    if src_transform:
        src_transform = guard_transform(src_transform).to_gdal()
    if dst_transform:
        dst_transform = guard_transform(dst_transform).to_gdal()

    _reproject(
        source,
        destination,
        src_transform,
        src_crs,
        src_nodata,
        dst_transform,
        dst_crs,
        dst_nodata,
        resampling,
        **kwargs)


def calculate_default_transform(
        src_crs,
        dst_crs,
        width,
        height,
        left,
        bottom,
        right,
        top,
        resolution=None,
        densify_pts=21):
    """
    Transforms bounds to destination coordinate system, calculates resolution
    if not provided, and returns destination transform and dimensions.
    Intended to be used to calculate parameters for reproject function.

    Destination transform is anchored from the left, top coordinate.

    Destination width and height are calculated from the number of pixels on
    each dimension required to fit the destination bounds.

    If resolution is not provided, it is calculated using a weighted average
    of the relative sizes of source width and height compared to the transformed
    bounds (pixels are assumed to be square).


    Parameters
    ----------
    src_crs: dict
        Source coordinate reference system, in rasterio dict format.
        Example: {'init': 'EPSG:4326'}
    dst_crs: dict
        Target coordinate reference system.
    width: int
        Source raster width.
    height: int
        Source raster height.
    left, bottom, right, top: float
        Bounding coordinates in src_crs, from the bounds property of a raster.
    resolution: tuple (x resolution, y resolution) or float, optional
        Target resolution, in units of target coordinate reference system.
    densify_pts: uint, optional
        Number of points to add to each edge to account for nonlinear
        edges produced by the transform process.  Large numbers will produce
        worse performance.  Default: 21 (gdal default).

    Returns
    -------
    tuple of destination affine transform, width, and height
    """

    xmin, ymin, xmax, ymax = transform_bounds(
        src_crs, dst_crs, left, bottom, right, top, densify_pts)

    x_dif = xmax - xmin
    y_dif = ymax - ymin
    size = float(width + height)

    if resolution is None:
        # TODO: compare to gdalwarp default
        avg_resolution = (
            (x_dif / float(width)) * (float(width) / size) +
            (y_dif / float(height)) * (float(height) / size)
        )
        resolution = (avg_resolution, avg_resolution)

    elif not isinstance(resolution, (tuple, list)):
        resolution = (resolution, resolution)

    dst_affine = Affine(resolution[0], 0, xmin, 0, -resolution[1], ymax)
    dst_width = max(int(ceil(x_dif / resolution[0])), 1)
    dst_height = max(int(ceil(y_dif / resolution[1])), 1)

    return dst_affine, dst_width, dst_height

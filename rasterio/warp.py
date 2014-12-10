"""Raster warping and reprojection"""

from rasterio._warp import _reproject, _transform, _transform_geom, RESAMPLING
from rasterio.transform import guard_transform


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


def reproject(
        source,
        destination,
        src_transform=None,
        src_crs=None,
        dst_transform=None,
        dst_crs=None,
        resampling=RESAMPLING.nearest,
        **kwargs):
    """
    Reproject a source raster to a destination raster.

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
    dst_transform: affine transform object, optional
        Target affine transformation.  Required if source and destination
        are ndarrays.  Will be derived from target if it is a rasterio Band.
    dst_crs: dict, optional
        Target coordinate reference system.  Required if source and destination
        are ndarrays.  Will be derived from target if it is a rasterio Band.
    resampling: int
        Resampling method to use.  One of the following:
            RESAMPLING.nearest,
            RESAMPLING.bilinear,
            RESAMPLING.cubic,
            RESAMPLING.cubic_spline,
            RESAMPLING.lanczos,
            RESAMPLING.average,
            RESAMPLING.mode
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
        dst_transform,
        dst_crs,
        resampling,
        **kwargs)

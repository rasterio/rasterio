"""Raster warping and reprojection"""

from rasterio._warp import _reproject, _transform, _transform_geom, RESAMPLING
from rasterio.transform import guard_transform


def transform(src_crs, dst_crs, xs, ys, zs=None):
    """Return transformed vectors of x, y and optionally z.
    
    The sequences of points x, y, z in the coordinate system defined by
    src_crs are transformed in the coordinate system defined by dst_crs.
    z is optional, if it is not set it is assumed to be all zeros and only
    x and y are returned.
    """
    return _transform(src_crs, dst_crs, xs, ys, zs)


def transform_geom(
        src_crs, dst_crs, geom,
        antimeridian_cutting=False, antimeridian_offset=10.0, precision=-1):
    """Return transformed geometry."""
    return _transform_geom(
        src_crs, dst_crs, geom,
        antimeridian_cutting, antimeridian_offset, precision)


def reproject(
        source, destination,
        src_transform=None, src_crs=None,
        dst_transform=None, dst_crs=None,
        resampling=RESAMPLING.nearest,
        **kwargs):
    """Reproject a source raster to a destination.

    If the source and destination are ndarrays, coordinate reference
    system definitions and affine transformation parameters are required
    for reprojection.

    If the source and destination are rasterio Bands, shorthand for
    bands of datasets on disk, the coordinate reference systems and
    transforms will be read from the appropriate datasets.
    """
    if src_transform:
        src_transform = guard_transform(src_transform).to_gdal()
    if dst_transform:
        dst_transform = guard_transform(dst_transform).to_gdal()

    _reproject(
        source, destination,
        src_transform, src_crs,
        dst_transform, dst_crs,
        resampling, **kwargs)

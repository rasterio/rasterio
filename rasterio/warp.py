"""Raster warping and reprojection"""

from rasterio._warp import _reproject, RESAMPLING
from rasterio.transform import guard_transform


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


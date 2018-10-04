"""Raster warping and reprojection."""


from __future__ import absolute_import
from __future__ import division

from math import ceil, floor

from affine import Affine
import numpy as np

import rasterio
from rasterio._base import _transform
from rasterio._warp import (
    _transform_geom, _reproject, _calculate_default_transform)
from rasterio.enums import Resampling
from rasterio.env import ensure_env, GDALVersion, require_gdal_version
from rasterio.errors import GDALBehaviorChangeException
from rasterio.transform import array_bounds

# Gauss (7) is not supported for warp
SUPPORTED_RESAMPLING = [r for r in Resampling if r.value < 7]
GDAL2_RESAMPLING = [r for r in Resampling if r.value > 7 and r.value <= 12]
if GDALVersion.runtime().at_least('2.0'):
    SUPPORTED_RESAMPLING.extend(GDAL2_RESAMPLING)


@ensure_env
def transform(src_crs, dst_crs, xs, ys, zs=None):

    """Transform vectors from source to target coordinate reference system.

    Transform vectors of x, y and optionally z from source
    coordinate reference system into target.

    Parameters
    ------------
    src_crs: CRS or dict
        Source coordinate reference system, as a rasterio CRS object.
        Example: CRS({'init': 'EPSG:4326'})
    dst_crs: CRS or dict
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


@ensure_env
@require_gdal_version('2.1', param='antimeridian_cutting', values=[False],
                      is_max_version=True,
                      reason="Antimeridian cutting is always enabled on "
                             "GDAL >= 2.2")
def transform_geom(
        src_crs,
        dst_crs,
        geom,
        antimeridian_cutting=True,
        antimeridian_offset=10.0,
        precision=-1):
    """Transform geometry from source coordinate reference system into target.

    Parameters
    ------------
    src_crs: CRS or dict
        Source coordinate reference system, in rasterio dict format.
        Example: CRS({'init': 'EPSG:4326'})
    dst_crs: CRS or dict
        Target coordinate reference system.
    geom: GeoJSON like dict object
    antimeridian_cutting: bool, optional
        If True, cut geometries at the antimeridian, otherwise geometries
        will not be cut (default).  If False and GDAL is 2.2.0 or newer
        an exception is raised.  Antimeridian cutting is always on as of
        GDAL 2.2.0 but this could produce an unexpected geometry.
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


def transform_bounds(
        src_crs,
        dst_crs,
        left,
        bottom,
        right,
        top,
        densify_pts=21):
    """Transform bounds from src_crs to dst_crs.

    Optionally densifying the edges (to account for nonlinear transformations
    along these edges) and extracting the outermost bounds.

    Note: this does not account for the antimeridian.

    Parameters
    ----------
    src_crs: CRS or dict
        Source coordinate reference system, in rasterio dict format.
        Example: CRS({'init': 'EPSG:4326'})
    dst_crs: CRS or dict
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
                bottom + np.arange(0, densify_pts + 2, dtype=np.float64) *
                ((top - bottom) * densify_factor)
            )

        for y in (bottom, top):
            in_xs.extend(
                left + np.arange(1, densify_pts + 1, dtype=np.float64) *
                ((right - left) * densify_factor)
            )
            in_ys.extend([y] * densify_pts)

    else:
        in_xs = [left, left, right, right]
        in_ys = [bottom, top, bottom, top]

    xs, ys = transform(src_crs, dst_crs, in_xs, in_ys)
    return (min(xs), min(ys), max(xs), max(ys))


@ensure_env
@require_gdal_version('2.0', param='resampling', values=GDAL2_RESAMPLING)
def reproject(source, destination=None, src_transform=None, gcps=None,
              src_crs=None, src_nodata=None, dst_transform=None, dst_crs=None,
              dst_nodata=None, src_alpha=0, dst_alpha=0,
              resampling=Resampling.nearest, num_threads=1,
              init_dest_nodata=True, warp_mem_limit=0, **kwargs):
    """Reproject a source raster to a destination raster.

    If the source and destination are ndarrays, coordinate reference
    system definitions and affine transformation parameters or ground
    control points (gcps) are required for reprojection.

    If the source and destination are rasterio Bands, shorthand for
    bands of datasets on disk, the coordinate reference systems and
    transforms or GCPs will be read from the appropriate datasets.

    Parameters
    ------------
    source, destination: ndarray or Band
        The source and destination are 2 or 3-D ndarrays, or a single
        or multiple Rasterio Band object. The dimensionality of source
        and destination must match, i.e., for multiband reprojection
        the lengths of the first axes of the source and destination
        must be the same.
    src_transform: affine.Affine(), optional
        Source affine transformation. Required if source and
        destination are ndarrays. Will be derived from source if it is
        a rasterio Band. An error will be raised if this parameter is
        defined together with gcps.
    gcps: sequence of GroundControlPoint, optional
        Ground control points for the source. An error will be raised
        if this parameter is defined together with src_transform.
    src_crs: CRS or dict, optional
        Source coordinate reference system, in rasterio dict format.
        Required if source and destination are ndarrays.
        Will be derived from source if it is a rasterio Band.
        Example: CRS({'init': 'EPSG:4326'})
    src_nodata: int or float, optional
        The source nodata value.Pixels with this value will not be
        used for interpolation. If not set, it will be default to the
        nodata value of the source image if a masked ndarray or
        rasterio band, if available.
    dst_transform: affine.Affine(), optional
        Target affine transformation. Required if source and
        destination are ndarrays. Will be derived from target if it is
        a rasterio Band.
    dst_crs: CRS or dict, optional
        Target coordinate reference system. Required if source and
        destination are ndarrays. Will be derived from target if it
        is a rasterio Band.
    dst_nodata: int or float, optional
        The nodata value used to initialize the destination; it will
        remain in all areas not covered by the reprojected source.
        Defaults to the nodata value of the destination image (if set),
        the value of src_nodata, or 0 (GDAL default).
    src_alpha : int, optional
        Index of a band to use as the alpha band when warping.
    dst_alpha : int, optional
        Index of a band to use as the alpha band when warping.
    resampling: int
        Resampling method to use.  One of the following:
            Resampling.nearest,
            Resampling.bilinear,
            Resampling.cubic,
            Resampling.cubic_spline,
            Resampling.lanczos,
            Resampling.average,
            Resampling.mode,
            Resampling.max (GDAL >= 2.2),
            Resampling.min (GDAL >= 2.2),
            Resampling.med (GDAL >= 2.2),
            Resampling.q1 (GDAL >= 2.2),
            Resampling.q3 (GDAL >= 2.2)
        An exception will be raised for a method not supported by the running
        version of GDAL.
    num_threads : int, optional
        The number of warp worker threads. Default: 1.
    init_dest_nodata: bool
        Flag to specify initialization of nodata in destination;
        prevents overwrite of previous warps. Defaults to True.
    warp_mem_limit : int, optional
        The warp operation memory limit in MB. Larger values allow the
        warp operation to be carried out in fewer chunks. The amount of
        memory required to warp a 3-band uint8 2000 row x 2000 col
        raster to a destination of the same size is approximately
        56 MB. The default (0) means 64 MB with GDAL 2.2.
    kwargs:  dict, optional
        Additional arguments passed to transformation function.

    Returns
    ---------
    out: None
        Output is written to destination.
    """

    # Only one type of georeferencing is permitted.
    if src_transform and gcps:
        raise ValueError("src_transform and gcps parameters may not"
                         "be used together.")

    # Guard against invalid or unsupported resampling algorithms.
    try:
        if resampling == 7:
            raise ValueError("Gauss resampling is not supported")

        Resampling(resampling)

    except ValueError:
        raise ValueError(
            "resampling must be one of: {0}".format(", ".join(
                ['Resampling.{0}'.format(r.name) for r in
                 SUPPORTED_RESAMPLING])))

    # calculate the destination transform if not provided
    if dst_transform is None and (destination is None or isinstance(destination, np.ndarray)):
        if isinstance(source, np.ndarray):
            if source.ndim == 3:
                src_count, src_height, src_width = source.shape
            else:
                src_count = 1
                src_height, src_width = source.shape
            src_bounds = array_bounds(src_height, src_width, src_transform)
        else:
            src_rdr, src_bidx, _, src_shape = source
            src_bounds = src_rdr.bounds()
            src_crs = src_rdr.crs
            src_count = len(src_bidx)
            src_height, src_width = src_shape

        dst_height = None
        dst_width = None
        dst_count = src_count
        if destination is not None:
            if isinstance(destination, np.ndarray):
                if destination.ndim == 3:
                    dst_count, dst_height, dst_width = destination.shape
                else:
                    dst_count = 1
                    dst_height, dst_width = destination.shape

        dst_transform, dst_width, dst_height = _calculate_default_transform(
            src_crs, dst_crs, src_width, src_height,
            **src_bounds,
            gcps=gcps, dst_width=dst_width, dst_height=dst_height)

        if destination is None:
            destination = np.empty((dst_count, dst_height, dst_width), dtype=source.dtype)

    # Call the function in our extension module.
    _reproject(
        source, destination, src_transform=src_transform, gcps=gcps,
        src_crs=src_crs, src_nodata=src_nodata, dst_transform=dst_transform,
        dst_crs=dst_crs, dst_nodata=dst_nodata, dst_alpha=dst_alpha,
        src_alpha=src_alpha, resampling=resampling,
        init_dest_nodata=init_dest_nodata, num_threads=num_threads,
        warp_mem_limit=warp_mem_limit, **kwargs)

    return destination, dst_transform


def aligned_target(transform, width, height, resolution):
    """Aligns target to specified resolution

    Parameters
    ----------
    transform : Affine
        Input affine transformation matrix
    width, height: int
        Input dimensions
    resolution: tuple (x resolution, y resolution) or float
        Target resolution, in units of target coordinate reference
        system.

    Returns
    -------
    transform: Affine
        Output affine transformation matrix
    width, height: int
        Output dimensions

    """
    if isinstance(resolution, (float, int)):
        res = (float(resolution), float(resolution))
    else:
        res = resolution

    xmin = transform.xoff
    ymin = transform.yoff + height * transform.e
    xmax = transform.xoff + width * transform.a
    ymax = transform.yoff

    xmin = floor(xmin / res[0]) * res[0]
    xmax = ceil(xmax / res[0]) * res[0]
    ymin = floor(ymin / res[1]) * res[1]
    ymax = ceil(ymax / res[1]) * res[1]
    dst_transform = Affine(res[0], 0, xmin, 0, -res[1], ymax)
    dst_width = max(int(ceil((xmax - xmin) / res[0])), 1)
    dst_height = max(int(ceil((ymax - ymin) / res[1])), 1)

    return dst_transform, dst_width, dst_height


@ensure_env
def calculate_default_transform(
        src_crs, dst_crs, width, height, left=None, bottom=None, right=None,
        top=None, gcps=None, resolution=None, dst_width=None, dst_height=None):
    """Output dimensions and transform for a reprojection.

    Source and destination coordinate reference systems and output
    width and height are the first four, required, parameters. Source
    georeferencing can be specified using either ground control points
    (gcps) or spatial bounds (left, bottom, right, top). These two
    forms of georeferencing are mutually exclusive.

    The destination transform is anchored at the left, top coordinate.

    Destination width and height (and resolution if not provided), are
    calculated using GDAL's method for suggest warp output.

    Parameters
    ----------
    src_crs: CRS or dict
        Source coordinate reference system, in rasterio dict format.
        Example: CRS({'init': 'EPSG:4326'})
    dst_crs: CRS or dict
        Target coordinate reference system.
    width, height: int
        Source raster width and height.
    left, bottom, right, top: float, optional
        Bounding coordinates in src_crs, from the bounds property of a
        raster. Required unless using gcps.
    gcps: sequence of GroundControlPoint, optional
        Instead of a bounding box for the source, a sequence of ground
        control points may be provided.
    resolution: tuple (x resolution, y resolution) or float, optional
        Target resolution, in units of target coordinate reference
        system.
    dst_width, dst_height: int, optional
        Output file size in pixels and lines. Cannot be used together
        with resolution.

    Returns
    -------
    transform: Affine
        Output affine transformation matrix
    width, height: int
        Output dimensions

    Notes
    -----
    Some behavior of this function is determined by the
    CHECK_WITH_INVERT_PROJ environment variable:

        YES: constrain output raster to extents that can be inverted
             avoids visual artifacts and coordinate discontinuties.
        NO:  reproject coordinates beyond valid bound limits
    """
    if any(x is not None for x in (left, bottom, right, top)) and gcps:
        raise ValueError("Bounding values and ground control points may not"
                         "be used together.")

    if any(x is None for x in (left, bottom, right, top)) and not gcps:
        raise ValueError("Either four bounding values or ground control points"
                         "must be specified")
    
    if (dst_width is None) != (dst_height is None):
        raise ValueError("Either dst_width and dst_height must be specified "
                         "or none of them.")

    if all(x is not None for x in (dst_width, dst_height)):
        dimensions = (dst_width, dst_height)
    else:
        dimensions = None

    if resolution and dimensions:
        raise ValueError("Resolution cannot be used with dst_width and dst_height.")

    dst_affine, dst_width, dst_height = _calculate_default_transform(
        src_crs, dst_crs, width, height, left, bottom, right, top, gcps)

    # If resolution is specified, Keep upper-left anchored
    # adjust the transform resolutions
    # adjust the width/height by the ratio of estimated:specified res (ceil'd)
    if resolution:
        # resolutions argument into tuple
        try:
            res = (float(resolution), float(resolution))
        except TypeError:
            res = (resolution[0], resolution[0]) \
                if len(resolution) == 1 else resolution[0:2]

        # Assume yres is provided as positive,
        # needs to be negative for north-up affine
        xres = res[0]
        yres = -res[1]

        xratio = dst_affine.a / xres
        yratio = dst_affine.e / yres

        dst_affine = Affine(xres, dst_affine.b, dst_affine.c,
                            dst_affine.d, yres, dst_affine.f)

        dst_width = ceil(dst_width * xratio)
        dst_height = ceil(dst_height * yratio)
    
    if dimensions:
        xratio = dst_width / dimensions[0]
        yratio = dst_height / dimensions[1]

        dst_width = dimensions[0]
        dst_height = dimensions[1]
        
        dst_affine = Affine(dst_affine.a * xratio, dst_affine.b, dst_affine.c,
                            dst_affine.d, dst_affine.e * yratio, dst_affine.f)

    return dst_affine, dst_width, dst_height

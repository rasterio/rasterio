"""Mask the area outside of the input shapes with no data."""


from __future__ import absolute_import

import warnings

import rasterio
from rasterio.features import geometry_mask


def mask(raster, shapes, nodata=None, crop=False, all_touched=False,
         invert=False):
    """Mask the area outside of the input shapes with nodata.

    For all regions in the input raster outside of the regions defined by
    `shapes`, sets any data present to nodata.

    Parameters
    ----------
    raster: rasterio RasterReader object
        Raster to which the mask will be applied.
    shapes: list of polygons
        Polygons are GeoJSON-like dicts specifying the boundaries of features
        in the raster to be kept. All data outside of specified polygons
        will be set to nodata.
    nodata: int or float (opt)
        Value representing nodata within each raster band. If not set,
        defaults to the nodata value for the input raster. If there is no
        set nodata value for the raster, it defaults to 0.
    crop: bool (opt)
        Whether to crop the raster to the extent of the data. Defaults to
        False.
    all_touched: bool (opt)
        Use all pixels touched by features. If False (default), use only
        pixels whose center is within the polygon or that are selected by
        Bresenhams line algorithm.
    invert: bool (opt)
        If True, mask will be True for pixels that overlap shapes.
        False by default.

    Returns
    -------
    masked: numpy ndarray
        Data contained in raster after applying the mask.
    out_transform: affine object
        Information for mapping pixel coordinates in `masked` to another
        coordinate system.
    """
    if crop and invert:
        raise ValueError("crop and invert cannot both be True.")
    if nodata is None:
        if raster.nodata is not None:
            nodata = raster.nodata
        else:
            nodata = 0

    all_bounds = [rasterio.features.bounds(shape) for shape in shapes]
    minxs, minys, maxxs, maxys = zip(*all_bounds)
    mask_bounds = (min(minxs), min(minys), max(maxxs), max(maxys))

    invert_y = raster.transform.e > 0
    source_bounds = raster.bounds
    if invert_y:
        source_bounds = [source_bounds[0], source_bounds[3],
                         source_bounds[2], source_bounds[1]]
    if rasterio.coords.disjoint_bounds(source_bounds, mask_bounds):
        if crop:
            raise ValueError("Input shapes do not overlap raster.")
        else:
            warnings.warn("GeoJSON outside bounds of existing output " +
                          "raster. Are they in different coordinate " +
                          "reference systems?")
    if invert_y:
        mask_bounds = [mask_bounds[0], mask_bounds[3],
                       mask_bounds[2], mask_bounds[1]]
    if crop:
        window = raster.window(*mask_bounds)
        out_transform = raster.window_transform(window)
    else:
        window = None
        out_transform = raster.transform

    out_image = raster.read(window=window, masked=True)
    out_shape = out_image.shape[1:]

    shape_mask = geometry_mask(shapes, transform=out_transform, invert=invert,
                               out_shape=out_shape, all_touched=all_touched)
    out_image.mask = out_image.mask | shape_mask
    out_image.fill_value = nodata

    for i in range(raster.count):
        out_image[i] = out_image[i].filled(nodata)

    return out_image, out_transform

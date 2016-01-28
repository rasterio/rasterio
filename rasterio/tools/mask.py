from __future__ import absolute_import

import rasterio

def mask(raster, shapes, nodatavals=None, crop=True):
    """
    For all regions in the input raster outside of the regions defined by
    `shapes`, sets any data present to nodata.

    Parameters
    ----------
    source: rasterio RasterReader object
        Raster to which the mask will be applied.
    shapes: generator of (polygon, value)
        Polygons are GeoJSON-like dicts specifying the boundaries of features
        in the raster to be kept. All data outside of specified polygons
        will be set to nodata.
    nodatavals: list (opt)
        Value representing nodata within each raster band. If not set,
        defaults to the nodatavals for the input raster. If those values
        are not set, defaults to 0.
    crop: bool (opt)
        Whether to crop the raster to the extent of the data. Defaults to True.

    Returns
    -------
    masked: numpy ndarray
        Data contained in raster after applying the mask.
    out_transform: affine object
        Information for mapping pixel coordinates in `masked` to another
        coordinate system.
    """

    # I'm not sure how good this no data handling will be generally
    if nodatavals is None:
        if raster.nodata is not None:
            nodatavals = raster.nodatavals
        else:
            nodatavals = [0] * raster.count

    # consume shapes twice, so convert to list
    shapes = list(shapes)
    all_bounds = [rasterio.features.bounds(shape[0]) for shape in shapes]
    minxs, minys, maxxs, maxys = zip(*all_bounds)
    mask_bounds = (min(minxs), min(minys), max(maxxs), max(maxys))

    if rasterio.coords.disjoint_bounds(raster.bounds, mask_bounds):
        raise ValueError("Input shapes do not overlap raster.")

    if crop:
        out_bounds = mask_bounds
    else:
        out_bounds = raster.bounds
    window = raster.window(*out_bounds)
    out_transform = raster.window_transform(window)
    masked = raster.read(window=window)
    out_shape = masked.shape[1:]

    shape_mask = rasterio.features.rasterize(shapes, transform=out_transform,
                                             out_shape=out_shape)
    shape_mask = shape_mask.astype("bool")
    for i in range(raster.count):
        masked[i, ~shape_mask] = nodatavals[i]

    return masked, out_transform

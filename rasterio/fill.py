import rasterio
from rasterio._fill import _fillnodata

def fillnodata(image, mask=None, max_search_distance=100.0,
    smoothing_iterations=0):
    """
    Fill selected raster regions by interpolation from the edges.

    This algorithm will interpolate values for all designated nodata pixels
    (marked by zeros in `mask`). For each pixel a four direction conic search
    is done to find values to interpolate from (using inverse distance
    weighting). Once all values are interpolated, zero or more smoothing
    iterations (3x3 average filters on interpolated pixels) are applied to
    smooth out artifacts.
    
    This algorithm is generally suitable for interpolating missing regions of
    fairly continuously varying rasters (such as elevation models for
    instance). It is also suitable for filling small holes and cracks in more
    irregularly varying images (like aerial photos). It is generally not so
    great for interpolating a raster from sparse point data.
    
    Parameters
    ----------
    image : numpy ndarray
        The band to be modified in place
    mask : numpy ndarray
        A mask band indicating which pixels to interpolate. Pixels to
        interpolate into are indicated by the value 0. Values of 1 indicate
        areas to use during interpolation. Must be same shape as image.
    max_search_distance : float, optional
        The maxmimum number of pixels to search in all directions to find
        values to interpolate from. The default is 100.
    smoothing_iterations : integer, optional
        The number of 3x3 smoothing filter passes to run. The default is 0.
    
    Returns
    -------
    out : numpy ndarray
        The interpolated raster array
    """
    max_search_distance = float(max_search_distance)
    smoothing_iterations = int(smoothing_iterations)
    with rasterio.drivers():
        ret = _fillnodata(image, mask, max_search_distance, smoothing_iterations)
    return ret

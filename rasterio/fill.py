import rasterio
from rasterio._fill import _fillnodata

def fillnodata(image, mask=None, max_search_distance=100.0,
    smoothing_iterations=0):
    """
    Fill nodata pixels by interpolation from the edges
    
    Parameters
    ----------
    image : numpy ndarray
        The band to be modified in place
    mask : numpy ndarray
        A mask band indicating pixels to be interpolated (zero valud)
    max_search_distance : float, optional
        The maxmimum number of pixels to search in all directions to find
        values to interpolate from. The default is 100.
    smoothing_iterations : integer, optional
        The number of 3x3 smoothing filter passes to run. The default is 0.
    """
    max_search_distance = float(max_search_distance)
    smoothing_iterations = int(smoothing_iterations)
    with rasterio.drivers():
        ret = _fillnodata(image, mask, max_search_distance, smoothing_iterations)

"""Functions for working with features in a raster dataset."""

import rasterio
from rasterio._features import polygonize

def shapes(image, transform=None):
    """Yields a (shape, image_value) pair for each feature in the image.
    
    The shapes are GeoJSON-like dicts and the image values are ints.
    
    Features are found using a connected-component labeling algorithm.
    """
    if image.dtype.type != rasterio.ubyte:
        raise ValueError("Image must be dtype uint8/ubyte")

    for s, v in polygonize(image, transform):
        yield s, v


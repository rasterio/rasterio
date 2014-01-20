"""Functions for working with features in a raster dataset."""

import rasterio
from rasterio._features import _shapes, _sieve

def shapes(image, transform=None):
    """Yields a (shape, image_value) pair for each feature in the image.
    
    The shapes are GeoJSON-like dicts and the image values are ints.
    
    Features are found using a connected-component labeling algorithm.
    """
    if image.dtype.type != rasterio.ubyte:
        raise ValueError("Image must be dtype uint8/ubyte")

    for s, v in _shapes(image, transform):
        yield s, v

def sieve(image, size, connectivity=4, output=None):
    return _sieve(image, size, connectivity)


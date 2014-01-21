"""Functions for working with features in a raster dataset."""

import rasterio
from rasterio._features import _shapes, _sieve


def shapes(image, transform=None):
    """Yields a (shape, image_value) pair for each feature in the image.
    
    The shapes are GeoJSON-like dicts and the image values are ints.
    
    Features are found using a connected-component labeling algorithm.

    The image must be of unsigned 8-bit integer (rasterio.byte or
    numpy.uint8) data type.
    """
    if image.dtype.type != rasterio.ubyte:
        raise ValueError("Image must be dtype uint8/ubyte")

    with rasterio.drivers():
        for s, v in _shapes(image, transform):
            yield s, v


def sieve(image, size, connectivity=4, output=None):
    """Returns a copy of the image, but with smaller features removed.

    Features smaller than the specified size have their pixel value
    replaced by that of the largest neighboring features.
    
    The image must be of unsigned 8-bit integer (rasterio.byte or
    numpy.uint8) data type.
    """
    if image.dtype.type != rasterio.ubyte:
        raise ValueError("Image must be dtype uint8/ubyte")

    with rasterio.drivers():
        return _sieve(image, size, connectivity)


"""Functions for working with features in a raster dataset."""

import json

import numpy
import rasterio
from rasterio._features import _shapes, _sieve, _rasterize


def shapes(image, mask=None, connectivity=4, transform=None):
    """Yields a (shape, image_value) pair for each feature in the image.
    
    The shapes are GeoJSON-like dicts and the image values are ints.
    
    Features are found using a connected-component labeling algorithm.

    The image must be of unsigned 8-bit integer (rasterio.byte or
    numpy.uint8) data type. If a mask is provided, pixels for which the
    mask is `True` will be excluded from feature generation.
    """
    if image.dtype.type != rasterio.ubyte:
        raise ValueError("Image must be dtype uint8/ubyte")

    if mask is not None and mask.dtype.type != rasterio.bool_:
        raise ValueError("Mask must be dtype rasterio.bool_")

    with rasterio.drivers():
        for s, v in _shapes(image, mask, connectivity, transform):
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

    if output is not None and output.dtype.type != rasterio.ubyte:
        raise ValueError("Output must be dtype uint8/ubyte")

    with rasterio.drivers():
        return _sieve(image, size, connectivity)


def rasterize(
        shapes, 
        out_shape=None, fill=0, output=None, transform=None, 
        all_touched=False):
    """Returns an image array with points, lines, or polygons burned in.

    A different value may be specified for each shape.  The shapes may
    be georeferenced or may have image coordinates. An existing image
    array may be provided, or one may be created. By default, the center
    of image elements determines whether they are updated, but all
    touched elements may be optionally updated.

    :param shapes: an iterator over Fiona style geometry objects (with
    a default value of 255) or an iterator over (geometry, value) pairs.
    Values must be unsigned integer type (uint8).

    :param transform: GDAL style geotransform to be applied to the
    image.

    :param out_shape: shape of created image array
    :param fill: fill value for created image array
    :param output: alternatively, an existing image array

    :param all_touched: if True, will rasterize all pixels touched, 
    otherwise will use GDAL default method.
    """

    geoms = []
    for index, entry in enumerate(shapes):
        if isinstance(entry, (tuple, list)):
            geometry, value = entry
            if not isinstance(value, int) or value > 255 or value < 0:
                raise ValueError(
                    "Shape number %i, value '%s' is not uint8/ubyte" % (
                        index, value))
            geoms.append((geometry, value))
        else:
            geoms.append((entry, 255))
    
    if out_shape is not None:
        out = numpy.empty(out_shape, dtype=rasterio.ubyte)
        out.fill(fill)
    elif output is not None:
        if output.dtype.type != rasterio.ubyte:
            raise ValueError("Output image must be dtype uint8/ubyte")
        out = output
    else:
        raise ValueError("An output image must be provided or specified")
    
    with rasterio.drivers():
        _rasterize(geoms, out, transform, all_touched)
    
    return out


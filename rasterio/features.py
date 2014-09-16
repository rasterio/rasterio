"""Functions for working with features in a raster dataset."""

import json
import logging
import time
import warnings

import numpy as np

import rasterio
from rasterio._features import _shapes, _sieve, _rasterize
from rasterio.transform import IDENTITY, guard_transform


log = logging.getLogger('rasterio')
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())


def shapes(image, mask=None, connectivity=4, transform=IDENTITY):
    """Yields a (shape, image_value) pair for each feature in the image.
    
    The shapes are GeoJSON-like dicts and the image values are ints.
    
    Features are found using a connected-component labeling algorithm.

    The image must be of unsigned 8-bit integer (rasterio.byte or
    numpy.uint8) data type. If a mask is provided, pixels for which the
    mask is `False` will be excluded from feature generation.
    """
    if np.dtype(image.dtype) != np.dtype(rasterio.ubyte):
        raise ValueError("Image must be dtype uint8/ubyte")

    if mask is not None and np.dtype(mask.dtype) != np.dtype(rasterio.bool_):
        raise ValueError("Mask must be dtype rasterio.bool_")

    if connectivity not in (4, 8):
        raise ValueError("Connectivity Option must be 4 or 8")

    transform = guard_transform(transform)

    with rasterio.drivers():
        for s, v in _shapes(image, mask, connectivity, transform.to_gdal()):
            yield s, v


def sieve(image, size, connectivity=4, output=None):
    """Returns a copy of the image, but with smaller features removed.

    Features smaller than the specified size have their pixel value
    replaced by that of the largest neighboring features.
    
    The image must be of unsigned 8-bit integer (rasterio.byte or
    numpy.uint8) data type.
    """
    if np.dtype(image.dtype) != np.dtype(rasterio.ubyte):
        raise ValueError("Image must be dtype uint8/ubyte")

    if output is not None and (
            np.dtype(output.dtype) != np.dtype(rasterio.ubyte)):
        raise ValueError("Output must be dtype uint8/ubyte")

    with rasterio.drivers():
        return _sieve(image, size, connectivity)


def rasterize(
        shapes, 
        out_shape=None, fill=0, output=None,
        transform=IDENTITY,
        all_touched=False,
        default_value=255):
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
    :param default_value: value burned in for shapes if not provided as part of shapes.  Must be unsigned integer type (uint8).
    """

    if not isinstance(default_value, int) or (
            default_value > 255 or default_value < 0):
        raise ValueError("default_value %s is not uint8/ubyte" % default_value)

    def shape_source():
        """A generator that screens out non-geometric objects and does
        its best to make sure that no NULLs get through to 
        GDALRasterizeGeometries."""
        for index, item in enumerate(shapes):
            try:
                
                if isinstance(item, (tuple, list)):
                    geom, value = item
                    # TODO: relax this for other data types.
                    if not isinstance(value, int) or value > 255 or value < 0:
                        raise ValueError(
                            "Shape number %i, value '%s' is not uint8/ubyte" % (
                                index, value))
                else:
                    geom = item
                    value = default_value
                geom = getattr(geom, '__geo_interface__', None) or geom
                if (not isinstance(geom, dict) or 
                    'type' not in geom or 'coordinates' not in geom):
                    raise ValueError(
                        "Object %r at index %d is not a geometric object" %
                        (geom, index))
                yield geom, value
            except Exception:
                log.exception("Exception caught, skipping shape %d", index)

    if out_shape is not None:
        out = np.empty(out_shape, dtype=rasterio.ubyte)
        out.fill(fill)
    elif output is not None:
        if np.dtype(output.dtype) != np.dtype(rasterio.ubyte):
            raise ValueError("Output image must be dtype uint8/ubyte")
        out = output
    else:
        raise ValueError("An output image must be provided or specified")
    
    transform = guard_transform(transform)

    with rasterio.drivers():
        _rasterize(shape_source(), out, transform.to_gdal(), all_touched)
    
    return out


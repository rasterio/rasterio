import logging
import sys

import numpy

import rasterio
import rasterio.features as ftrz

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_shapes():
    """Access to shapes of labeled features"""
    image = numpy.zeros((20, 20), dtype=rasterio.ubyte)
    image[5:15,5:15] = 127
    with rasterio.drivers():
        shapes = ftrz.shapes(image)
        shape, val = next(shapes)
        assert shape['type'] == 'Polygon'
        assert len(shape['coordinates']) == 2 # exterior and hole
        assert val == 0
        shape, val = next(shapes)
        assert shape['type'] == 'Polygon'
        assert len(shape['coordinates']) == 1 # no hole
        assert val == 127
        try:
            shape, val = next(shapes)
        except StopIteration:
            assert True
        else:
            assert False

def test_shapes_internal_driver_manager():
    """Access to shapes of labeled features"""
    image = numpy.zeros((20, 20), dtype=rasterio.ubyte)
    image[5:15,5:15] = 127
    shapes = ftrz.shapes(image)
    shape, val = next(shapes)
    assert shape['type'] == 'Polygon'


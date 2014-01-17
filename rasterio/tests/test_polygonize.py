import logging
import pprint
import sys

import numpy

import rasterio
import rasterio._features as ftrz

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_polygonize():
    image = numpy.zeros((20, 20), dtype=rasterio.ubyte)
    image[5:15,5:15] = 127
    features = ftrz.polygonize(image)
    f0 = next(features)
    assert f0['id'] == '0'
    assert f0['properties']['pix_val'] == 0
    assert len(f0['geometry']['coordinates']) == 2 # exterior and hole
    f1 = next(features)
    assert f1['id'] == '1'
    assert f1['properties']['pix_val'] == 127
    assert len(f1['geometry']['coordinates']) == 1 # no hole
    try:
        f3 = next(features)
    except StopIteration:
        assert True
    else:
        assert False


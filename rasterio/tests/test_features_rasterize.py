import logging
import sys
import numpy
import pytest
import rasterio
from rasterio.features import shapes, rasterize

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_rasterize_geometries():
    rows = cols = 10
    transform = [0, 1, 0, 0, 0, 1]
    geometry = {'type':'Polygon','coordinates':[[(2,2),(2,4.25),(4.25,4.25),(4.25,2),(2,2)]]}

    with rasterio.drivers():
        # we expect a subset of the pixels using default mode
        result = rasterize([geometry], out_shape=(rows, cols), transform=transform)
        truth = numpy.zeros((rows, cols))
        truth[2:4, 2:4] = 255
        assert (result == truth).min() == True

        # we expect all touched pixels
        result = rasterize([geometry], out_shape=(rows, cols), transform=transform, all_touched=True)
        truth = numpy.zeros((rows, cols))
        truth[2:5, 2:5] = 255
        assert (result == truth).min() == True

        # we expect the pixel value to match the one we pass in
        value = 5
        result = rasterize([(geometry, value)], out_shape=(rows, cols), transform=transform)
        truth = numpy.zeros((rows, cols))
        truth[2:4, 2:4] = value
        assert (result == truth).min() == True
        
        # Check the fill.
        # we expect the pixel value to match the one we pass in
        value = 5
        result = rasterize([(geometry, value)], out_shape=(rows, cols), fill=1, transform=transform)
        truth = numpy.ones((rows, cols))
        truth[2:4, 2:4] = value
        assert (result == truth).min() == True

        # we expect a ValueError if pixel value is not in 8 bit unsigned range
        value = 500
        with pytest.raises(ValueError):
            rasterize([(geometry, value)], out_shape=(rows, cols), transform=transform)


def test_rasterize_geometries_symmetric():
    """Make sure that rasterize is symmetric with shapes"""
    rows = cols = 10
    transform = [0, 1, 0, 0, 0, 1]
    truth = numpy.zeros((rows, cols), dtype=rasterio.ubyte)
    truth[2:5, 2:5] = 1
    with rasterio.drivers():
        s = shapes(truth, transform=transform)
        result = rasterize(s, out_shape=(rows, cols), transform=transform)
        assert (result == truth).min() == True

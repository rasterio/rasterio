import logging
import sys
import numpy
import pytest
import rasterio
from rasterio.features import shapes, rasterize_geometries

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_rasterize_geometries():
    rows = cols = 10
    transform = [0, 1, 0, 0, 0, 1]
    geometry = {'type':'Polygon','coordinates':[[(2,2),(2,4.25),(4.25,4.25),(4.25,2),(2,2)]]}

    with rasterio.drivers():
        # we expect a subset of the pixels using default mode
        result = rasterize_geometries([geometry], rows, cols, transform)
        truth = numpy.zeros((rows, cols))
        truth[2:4, 2:4] = 1
        assert (result == truth).min() == True

        # we expect all touched pixels
        result = rasterize_geometries([geometry], rows, cols, transform, all_touched=True)
        truth = numpy.zeros((rows, cols))
        truth[2:5, 2:5] = 1
        assert (result == truth).min() == True

        # we expect the pixel value to match the one we pass in
        value = 5
        result = rasterize_geometries([(geometry, value)], rows, cols, transform)
        truth = numpy.zeros((rows, cols))
        truth[2:4, 2:4] = value
        assert (result == truth).min() == True

        # we expect a ValueError if pixel value is not in 8 bit unsigned range
        value = 500
        with pytest.raises(ValueError):
            rasterize_geometries([(geometry, value)], rows, cols, transform)


def test_rasterize_geometries_symmetric():
    """Make sure that rasterize is symmetric with shapes"""
    rows = cols = 10
    transform = [0, 1, 0, 0, 0, 1]
    truth = numpy.zeros((rows, cols), dtype=rasterio.ubyte)
    truth[2:5, 2:5] = 1
    with rasterio.drivers():
        s = shapes(truth, transform=transform)
        result = rasterize_geometries(s, rows, cols, transform=transform)
        assert (result == truth).min() == True

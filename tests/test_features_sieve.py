import logging
import sys

import numpy

import rasterio
import rasterio.features as ftrz

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_sieve():
    """Test sieving a 10x10 feature from an ndarray."""
    image = numpy.zeros((20, 20), dtype=rasterio.ubyte)
    image[5:15,5:15] = 127
    # There should be some True pixels.
    assert image.any()
    # An attempt to sieve out features smaller than 100 should not change the
    # image.
    with rasterio.drivers():
        sieved_image = ftrz.sieve(image, 100)
        assert (
            list(map(list, numpy.where(sieved_image==127))) == 
            list(map(list, numpy.where(image==127))))
    # Setting the size to 100 should leave us an empty, False image.
    with rasterio.drivers():
        sieved_image = ftrz.sieve(image, 101)
        assert not sieved_image.any()

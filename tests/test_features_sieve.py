import logging
import sys
import numpy
import pytest

import rasterio
import rasterio.features as ftrz


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_sieve():
    """Test sieving a 10x10 feature from an ndarray."""

    image = numpy.zeros((20, 20), dtype=rasterio.ubyte)
    image[5:15, 5:15] = 1

    # An attempt to sieve out features smaller than 100 should not change the
    # image.
    with rasterio.drivers():
        sieved_image = ftrz.sieve(image, 100)
        assert numpy.array_equal(sieved_image, image)

    # Setting the size to 100 should leave us an empty, False image.
    with rasterio.drivers():
        sieved_image = ftrz.sieve(image, 101)
        assert not sieved_image.any()


def test_sieve_connectivity():
    """Test proper behavior of connectivity"""

    image = numpy.zeros((20, 20), dtype=rasterio.ubyte)
    image[5:15:2, 5:15] = 1
    image[6, 4] = 1
    image[8, 15] = 1
    image[10, 4] = 1
    image[12, 15] = 1

    # Diagonals not connected, all become small features that will be removed
    sieved_image = ftrz.sieve(image, 54, connectivity=4)
    assert not sieved_image.any()

    # Diagonals connected, everything is retained
    sieved_image = ftrz.sieve(image, 54, connectivity=8)
    assert numpy.array_equal(sieved_image, image)


def test_sieve_output():
    """Test proper behavior of output image, if passed into sieve"""

    with rasterio.drivers():
        shape = (20, 20)
        image = numpy.zeros(shape, dtype=rasterio.ubyte)
        image[5:15, 5:15] = 1

        # Output should match returned array
        output = numpy.zeros_like(image)
        output [1:3, 1:3] = 5
        sieved_image = ftrz.sieve(image, 100, output=output)
        assert numpy.array_equal(output, sieved_image)

        # Output of different dtype should fail
        output = numpy.zeros(shape, dtype=rasterio.int32)
        with pytest.raises(ValueError):
            ftrz.sieve(image, 100, output)


def test_sieve_mask():
    """Test proper behavior of mask image, if passed int sieve"""

    with rasterio.drivers():
        shape = (20, 20)
        image = numpy.zeros(shape, dtype=rasterio.ubyte)
        image[5:15, 5:15] = 1
        image[1:3, 1:3] = 2

        # Blank mask has no effect, only areas smaller than size will be removed
        mask = numpy.ones(shape, dtype=rasterio.bool_)
        sieved_image = ftrz.sieve(image, 100, mask=mask)
        truth = numpy.zeros_like(image)
        truth[5:15, 5:15] = 1
        assert numpy.array_equal(sieved_image, truth)

        # Only areas within the overlap of the mask and values will be kept
        mask = numpy.ones(shape, dtype=rasterio.bool_)
        mask[7:10, 7:10] = False
        sieved_image = ftrz.sieve(image, 100, mask=mask)
        truth = numpy.zeros_like(image)
        truth[7:10, 7:10] = 1
        assert numpy.array_equal(sieved_image, truth)

        # mask of other type than rasterio.bool_ should fail
        mask = numpy.zeros(shape, dtype=rasterio.uint8)
        with pytest.raises(ValueError):
            ftrz.sieve(image, 100, mask=mask)


def test_dtypes():
    """Test dtype support for sieve"""

    rows = cols = 10
    with rasterio.drivers():
        supported_types = (
            ('int16', -32768),
            ('int32', -2147483648),
            ('uint8', 255),
            ('uint16', 65535)
        )

        for dtype, test_value in supported_types:
            image = numpy.zeros((rows, cols), dtype=dtype)
            image[2:5, 2:5] = test_value

            # Sieve should return the original image
            sieved_image = ftrz.sieve(image, 2)
            assert numpy.array_equal(image, sieved_image)
            assert numpy.dtype(sieved_image.dtype).name == dtype

            # Sieve should return a blank image
            sieved_image = ftrz.sieve(image, 10)
            assert numpy.array_equal(numpy.zeros_like(image), sieved_image)
            assert numpy.dtype(sieved_image.dtype).name == dtype

        # Unsupported types should all raise exceptions
        unsupported_types = (
            ('int8', -127),
            ('uint32', 4294967295),
            ('int64', 20439845334323),
            ('float16', -9343.232),
            ('float32', 1.434532),
            ('float64', -98332.133422114)
        )

        for dtype, test_value in unsupported_types:
            with pytest.raises(ValueError):
                image = numpy.zeros((rows, cols), dtype=dtype)
                image[2:5, 2:5] = test_value
                sieved_image = ftrz.sieve(image, 2)

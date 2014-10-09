import logging
import sys
import numpy
import pytest

import rasterio
import rasterio.features as ftrz


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_shapes():
    """Test creation of shapes from pixel values"""

    image = numpy.zeros((20, 20), dtype=rasterio.ubyte)
    image[5:15, 5:15] = 127
    with rasterio.drivers():
        shapes = ftrz.shapes(image)
        shape, val = next(shapes)
        assert shape['type'] == 'Polygon'
        assert len(shape['coordinates']) == 2  # exterior and hole
        assert val == 0
        shape, val = next(shapes)
        assert shape['type'] == 'Polygon'
        assert len(shape['coordinates']) == 1  # no hole
        assert val == 127
        try:
            shape, val = next(shapes)
        except StopIteration:
            assert True
        else:
            assert False


def test_shapes_band_shortcut():
    """Test rasterio bands as input to shapes"""

    with rasterio.drivers():
        with rasterio.open('tests/data/shade.tif') as src:
            shapes = ftrz.shapes(rasterio.band(src, 1))
            shape, val = next(shapes)
            assert shape['type'] == 'Polygon'
            assert len(shape['coordinates']) == 1
            assert val == 255


def test_shapes_internal_driver_manager():
    """Make sure this works if driver is managed outside this test"""

    image = numpy.zeros((20, 20), dtype=rasterio.ubyte)
    image[5:15, 5:15] = 127
    shapes = ftrz.shapes(image)
    shape, val = next(shapes)
    assert shape['type'] == 'Polygon'


def test_shapes_connectivity():
    """Test connectivity options"""

    image = numpy.zeros((20, 20), dtype=rasterio.ubyte)
    image[5:11, 5:11] = 1
    image[11, 11] = 1

    shapes = ftrz.shapes(image, connectivity=8)
    shape, val = next(shapes)
    assert len(shape['coordinates'][0]) == 9
    # Note: geometry is not technically valid at this point, it has a self
    # intersection at 11,11


def test_shapes_dtype():
    """Test image data type handling"""

    rows = cols = 10
    with rasterio.drivers():
        supported_types = (
            ('int16', -32768),
            ('int32', -2147483648),
            ('uint8', 255),
            ('uint16', 65535),
            ('float32', 1.434532)
        )

        for dtype, test_value in supported_types:
            image = numpy.zeros((rows, cols), dtype=dtype)
            image[2:5, 2:5] = test_value

            shapes = ftrz.shapes(image)
            shape, value = next(shapes)
            if dtype == 'float32':
                assert round(value, 6) == round(test_value, 6)
            else:
                assert value == test_value

        # Unsupported types should all raise exceptions
        unsupported_types = (
            ('int8', -127),
            ('uint32', 4294967295),
            ('int64', 20439845334323),
            ('float16', -9343.232),
            ('float64', -98332.133422114)
        )

        for dtype, test_value in unsupported_types:
            with pytest.raises(ValueError):
                image = numpy.zeros((rows, cols), dtype=dtype)
                image[2:5, 2:5] = test_value
                shapes = ftrz.shapes(image)
                shape, value = next(shapes)

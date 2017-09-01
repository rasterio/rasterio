"""Unittests for rasterio.mask"""


import rasterio
from rasterio.mask import mask as mask_tool

import numpy
import pytest


def test_mask(basic_image_2x2, basic_image_file, basic_geometry):
    """Pixels outside the geometry are masked to nodata (0)"""

    geometries = [basic_geometry]

    with rasterio.open(basic_image_file, "r") as src:
        masked, transform = mask_tool(src, geometries)

    assert numpy.array_equal(masked[0], basic_image_2x2)


def test_mask_invert(basic_image, basic_image_file, basic_geometry):
    """Pixels inside the geometry are masked to nodata (0)"""

    geometries = [basic_geometry]
    basic_image[2:4, 2:4] = 0

    with rasterio.open(basic_image_file, "r") as src:
        masked, transform = mask_tool(src, geometries, invert=True)

    assert numpy.array_equal(masked[0], basic_image)


def test_nodata(basic_image_2x2, basic_image_file, basic_geometry):
    """All pixels outside geometry should be masked out as 3"""

    nodata = 3
    geometries = [basic_geometry]

    basic_image_2x2[basic_image_2x2 == 0] = nodata

    with rasterio.open(basic_image_file, "r") as src:
        masked, transform = mask_tool(src, geometries, nodata=nodata)

    assert numpy.array_equal(masked[0], basic_image_2x2)


def test_all_touched(basic_image, basic_image_file, basic_geometry):
    """All pixels touched by geometry should be masked out as 3"""

    nodata = 3
    geometries = [basic_geometry]

    with rasterio.open(basic_image_file, "r") as src:
        masked, transform = mask_tool(src, geometries, nodata=nodata,
                                      invert=True, all_touched=True)

    assert numpy.array_equal(masked[0], basic_image * nodata)


def test_crop(basic_image_2x2, basic_image_file, basic_geometry):
    """Output should be cropped to extent of geometry"""

    geometries = [basic_geometry]
    with rasterio.open(basic_image_file, "r") as src:
        masked, transform = mask_tool(src, geometries, crop=True)

    assert masked.shape == (1, 3, 3)
    assert numpy.array_equal(masked[0], basic_image_2x2[2:5, 2:5])


def test_crop_all_touched(basic_image, basic_image_file, basic_geometry):
    """Output should be cropped to extent of data"""

    geometries = [basic_geometry]

    with rasterio.open(basic_image_file, "r") as src:
        masked, transform = mask_tool(src, geometries, crop=True,
                                      all_touched=True)

    assert masked.shape == (1, 3, 3)
    assert numpy.array_equal(masked[0], basic_image[2:5, 2:5])


@pytest.mark.xfail()
# TODO: This pad funcionality is not working properly
def test_pad(basic_image_2x2, basic_image_file, basic_geometry):
    """Output should be cropped to extent of data"""

    geometries = [basic_geometry]
    with rasterio.open(basic_image_file, "r") as src:
        masked, transform = mask_tool(src, geometries, crop=True, pad=True)

    assert masked.shape == (1, 4, 4)
    assert numpy.array_equal(masked[0], basic_image_2x2[2:5, 2:5])


def test_return_type(basic_image_file, basic_geometry):
    """Output array should be an ndarray, not MaskedArray"""

    geometries = [basic_geometry]
    with rasterio.open(basic_image_file, "r") as src:
        masked, transform = mask_tool(src, geometries)
    assert(type(masked) == numpy.ndarray)
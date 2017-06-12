"""Unittests for rasterio.mask"""

from packaging.version import parse
import pytest

import rasterio
from rasterio.mask import mask as mask_tool


# Custom markers.
xfail_pixel_sensitive_gdal22 = pytest.mark.xfail(
    parse(rasterio.__gdal_version__) < parse('2.2'),
    reason="This test is sensitive to pixel values and requires GDAL 2.2+")


def test_nodata(basic_image_file, basic_geometry):
    nodata_val = 0
    geometries = [basic_geometry]
    with rasterio.open(basic_image_file, "r") as src:
        masked, transform = mask_tool(src, geometries, crop=False,
                                      nodata=nodata_val, invert=True)
    assert(masked.data.all() == nodata_val)


def test_no_nodata(basic_image_file, basic_geometry):
    default_nodata_val = 0
    geometries = [basic_geometry]
    with rasterio.open(basic_image_file, "r") as src:
        masked, transform = mask_tool(src, geometries, crop=False, invert=True)
    assert(masked.data.all() == default_nodata_val)


@xfail_pixel_sensitive_gdal22
def test_crop(basic_image, basic_image_file, basic_geometry):
    geometries = [basic_geometry]
    with rasterio.open(basic_image_file, "r") as src:
        masked, transform = mask_tool(src, geometries, crop=True, pad=False)

    image = basic_image
    image[4, :] = 0
    image[:, 4] = 0

    assert masked.shape == (1, 3, 3)
    assert (masked[0] == image[2:5, 2:5]).all()


@xfail_pixel_sensitive_gdal22
def test_crop_all_touched(basic_image, basic_image_file, basic_geometry):
    geometries = [basic_geometry]
    with rasterio.open(basic_image_file, "r") as src:
        masked, transform = mask_tool(src, geometries, crop=True,
                                      all_touched=True)

    assert masked.shape == (1, 3, 3)
    assert (masked[0] == basic_image[2:5, 2:5]).all()


def test_crop_and_invert(basic_image_file, basic_geometry):
    geometries = [basic_geometry]
    with rasterio.open(basic_image_file) as src:
        with pytest.raises(ValueError):
            masked, transform = mask_tool(src, geometries,
                                          crop=True, invert=True)

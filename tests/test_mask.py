"""Tests of the mask module"""

import json

import numpy as np
import pytest
from affine import Affine

import rasterio
from rasterio.mask import raster_geometry_mask, mask


def test_raster_geometrymask(basic_image_2x2, basic_image_file, basic_geometry):
    """Pixels inside the geometry are False in the mask"""

    geometries = [basic_geometry]

    with rasterio.open(basic_image_file) as src:
        geometrymask, transform, window = raster_geometry_mask(src, geometries)

    assert np.array_equal(geometrymask, (basic_image_2x2 == 0))
    assert transform == Affine.identity()
    assert window is None


def test_raster_geometrymask_invert(basic_image_2x2, basic_image_file, basic_geometry):
    """Pixels inside the geometry are True in the mask"""

    geometries = [basic_geometry]

    with rasterio.open(basic_image_file) as src:
        geometrymask, transform, window = raster_geometry_mask(src, geometries,
                                                            invert=True)

    assert np.array_equal(geometrymask, basic_image_2x2)
    assert transform == Affine.identity()


def test_raster_geometrymask_all_touched(basic_image, basic_image_file,
                                      basic_geometry):
    """Pixels inside the geometry are False in the mask"""

    geometries = [basic_geometry]

    with rasterio.open(basic_image_file) as src:
        geometrymask, transform, window = raster_geometry_mask(src, geometries,
                                                            all_touched=True)

    assert np.array_equal(geometrymask, (basic_image == 0))
    assert transform == Affine.identity()


def test_raster_geometrymask_crop(basic_image_2x2, basic_image_file,
                               basic_geometry):
    """Mask returned will be cropped to extent of geometry, and transform
    is transposed 2 down and 2 over"""

    geometries = [basic_geometry]

    with rasterio.open(basic_image_file) as src:
        geometrymask, transform, window = raster_geometry_mask(src, geometries,
                                                            crop=True)

    image = basic_image_2x2[2:5, 2:5] == 0  # invert because invert=False

    assert geometrymask.shape == (3, 3)
    assert np.array_equal(geometrymask, image)
    assert transform == Affine(1, 0, 2, 0, 1, 2)
    assert window is not None and window.flatten() == (2, 2, 3, 3)


def test_raster_geometrymask_crop_invert(basic_image_file, basic_geometry):
    """crop and invert cannot be combined"""

    geometries = [basic_geometry]

    with rasterio.open(basic_image_file) as src:
        with pytest.raises(ValueError):
            raster_geometry_mask(src, geometries, crop=True, invert=True)


def test_raster_geometrymask_crop_all_touched(basic_image, basic_image_file,
                                           basic_geometry):
    """Mask returned will be cropped to extent of geometry, and transform
    is transposed 2 down and 2 over"""

    geometries = [basic_geometry]

    with rasterio.open(basic_image_file) as src:
        geometrymask, transform, window = raster_geometry_mask(src, geometries,
                                                            crop=True,
                                                            all_touched=True)

    image = basic_image[2:5, 2:5] == 0  # invert because invert=False

    assert geometrymask.shape == (3, 3)
    assert np.array_equal(geometrymask, image)
    assert transform == Affine(1, 0, 2, 0, 1, 2)
    assert window is not None and window.flatten() == (2, 2, 3, 3)


def test_raster_geometrymask_crop_pad(basic_image_2x2, basic_image_file,
                                   basic_geometry):
    """Mask returned will be cropped to extent of geometry plus 1/2 pixel on
    all sides, and transform is transposed 1 down and 1 over"""

    geometries = [basic_geometry]

    with rasterio.open(basic_image_file) as src:
        geometrymask, transform, window = raster_geometry_mask(src, geometries,
                                                            crop=True, pad=True)

    image = basic_image_2x2[1:5, 1:5] == 0  # invert because invert=False

    assert geometrymask.shape == (4, 4)
    assert np.array_equal(geometrymask, image)
    assert transform == Affine(1, 0, 1, 0, 1, 1)
    assert window is not None and window.flatten() == (1, 1, 4, 4)


def test_raster_geometrymask_no_overlap(path_rgb_byte_tif, basic_geometry):
    """If there is no overlap, a warning should be raised"""

    with rasterio.open(path_rgb_byte_tif) as src:
        with pytest.warns(UserWarning) as warning:
            raster_geometry_mask(src, [basic_geometry])

            assert 'outside bounds of raster' in warning[0].message.args[0]


def test_raster_geometrymask_crop_no_overlap(path_rgb_byte_tif, basic_geometry):
    """If there is no overlap with crop=True, an Exception should be raised"""

    with rasterio.open(path_rgb_byte_tif) as src:
        with pytest.raises(ValueError) as excinfo:
            raster_geometry_mask(src, [basic_geometry], crop=True)

            assert 'shapes do not overlap raster' in repr(excinfo)



def test_mask(basic_image_2x2, basic_image_file, basic_geometry):
    """Pixels outside the geometry are masked to nodata (0)"""

    geometries = [basic_geometry]

    with rasterio.open(basic_image_file) as src:
        masked, transform = mask(src, geometries)

    assert np.array_equal(masked[0], basic_image_2x2)
    assert (type(masked) == np.ndarray)


def test_mask_invert(basic_image, basic_image_file, basic_geometry):
    """Pixels inside the geometry are masked to nodata (0)"""

    geometries = [basic_geometry]
    basic_image[2:4, 2:4] = 0

    with rasterio.open(basic_image_file) as src:
        masked, transform = mask(src, geometries, invert=True)

    assert np.array_equal(masked[0], basic_image)


def test_mask_nodata(basic_image_2x2, basic_image_file, basic_geometry):
    """All pixels outside geometry should be masked out as 3"""

    nodata = 3
    geometries = [basic_geometry]

    basic_image_2x2[basic_image_2x2 == 0] = nodata

    with rasterio.open(basic_image_file) as src:
        masked, transform = mask(src, geometries, nodata=nodata)

    assert np.array_equal(masked[0], basic_image_2x2)


def test_mask_all_touched(basic_image, basic_image_file, basic_geometry):
    """All pixels touched by geometry should be masked out as 3"""

    nodata = 3
    geometries = [basic_geometry]

    with rasterio.open(basic_image_file) as src:
        masked, transform = mask(src, geometries, nodata=nodata,
                                      invert=True, all_touched=True)

    assert np.array_equal(masked[0], basic_image * nodata)


def test_mask_crop(basic_image_2x2, basic_image_file, basic_geometry):
    """Output should be cropped to extent of geometry"""

    geometries = [basic_geometry]
    with rasterio.open(basic_image_file) as src:
        masked, transform = mask(src, geometries, crop=True)

    assert masked.shape == (1, 3, 3)
    assert np.array_equal(masked[0], basic_image_2x2[2:5, 2:5])


def test_mask_crop_all_touched(basic_image, basic_image_file, basic_geometry):
    """Output should be cropped to extent of data"""

    geometries = [basic_geometry]

    with rasterio.open(basic_image_file) as src:
        masked, transform = mask(src, geometries, crop=True,
                                      all_touched=True)

    assert masked.shape == (1, 3, 3)
    assert np.array_equal(masked[0], basic_image[2:5, 2:5])


def test_mask_pad(basic_image_2x2, basic_image_file, basic_geometry):
    """Output should be cropped to extent of data"""

    geometries = [basic_geometry]
    with rasterio.open(basic_image_file) as src:
        masked, transform = mask(src, geometries, crop=True, pad=True)

    assert masked.shape == (1, 4, 4)
    assert np.array_equal(masked[0], basic_image_2x2[1:5, 1:5])


def test_mask_filled(basic_image, basic_image_2x2, basic_image_file,
                     basic_geometry):
    """Should be returned as numpy.ma.MaskedArray if filled is False"""

    geometries = [basic_geometry]

    with rasterio.open(basic_image_file) as src:
        masked, transform = mask(src, geometries, filled=False)

    image = np.ma.MaskedArray(basic_image, mask=basic_image_2x2==0)

    assert (type(masked) == np.ma.MaskedArray)
    assert np.array_equal(masked[0].mask, image.mask)
    assert np.array_equal(masked[0], image)


def test_rgb_footprint_mask(path_rgb_byte_tif, path_rgb_byte_jsons):
    """Mask out the RGB.byte.tif image using its footprint"""
    with open(path_rgb_byte_jsons) as f:
        shapes = [json.loads(line)['geometry'] for line in f]
    with rasterio.open(path_rgb_byte_tif) as src:
        masked, masked_transform = rasterio.mask.mask(src, shapes, invert=True)
    assert masked.any()

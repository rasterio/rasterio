"""Unittests for deprecated features"""


import affine
import pytest

import rasterio


def test_open_affine_and_transform(path_rgb_byte_tif):
    with pytest.raises(ValueError):
        with rasterio.open(
                path_rgb_byte_tif,
                affine=affine.Affine.identity(),
                transform=affine.Affine.identity()) as src:
            pass


def test_open_transform_not_Affine(path_rgb_byte_tif):
    with pytest.raises(TypeError):
        with rasterio.open(
                path_rgb_byte_tif,
                transform=tuple(affine.Affine.identity())) as src:
            pass


def test_affine_warning(path_rgb_byte_tif):
    with pytest.warns(RuntimeWarning):
        with rasterio.open(
                path_rgb_byte_tif,
                affine=affine.Affine.identity()) as src:
            pass

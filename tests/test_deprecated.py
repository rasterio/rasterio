"""Unittests for deprecated features"""


import affine
import pytest

import rasterio
from rasterio.errors import RasterioDeprecationWarning


def test_open_transform_gdal_geotransform(path_rgb_byte_tif):
    """Passing a GDAL geotransform to rasterio.open(transform=...) should raise
    an exception.
    """
    with pytest.raises(TypeError):
        with rasterio.open(
                path_rgb_byte_tif,
                transform=tuple(affine.Affine.identity())):
            pass


def test_open_affine_kwarg_warning(path_rgb_byte_tif):
    """Passing the 'affine' kwarg to rasterio.open() should raise a warning."""
    with pytest.warns(DeprecationWarning):
        with rasterio.open(
                path_rgb_byte_tif,
                affine=affine.Affine.identity()):
            pass


def test_src_affine_warning(path_rgb_byte_tif):
    """Calling src.affine should raise a warning."""
    with pytest.warns(RasterioDeprecationWarning):
        with rasterio.open(path_rgb_byte_tif) as src:
            assert src.affine == src.transform

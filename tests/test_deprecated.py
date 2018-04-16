"""Unittests for deprecated features"""


import affine
import pytest

import rasterio


def test_open_transform_gdal_geotransform(path_rgb_byte_tif):
    """Passing a GDAL geotransform to rasterio.open(transform=...) should raise
    an exception.
    """
    with pytest.raises(TypeError):
        with rasterio.open(
                path_rgb_byte_tif,
                transform=tuple(affine.Affine.identity())):
            pass

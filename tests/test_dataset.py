"""High level tests for Rasterio's ``GDALDataset`` abstractions."""


import os

import pytest

import rasterio
from rasterio.errors import RasterioIOError


def test_files(path_rgb_byte_tif):
    aux = path_rgb_byte_tif + '.aux.xml'
    with open(aux, 'w'):
        pass
    with rasterio.open(path_rgb_byte_tif) as src:
        assert src.files == (path_rgb_byte_tif, aux)
    os.unlink(aux)


def test_handle_closed(path_rgb_byte_tif):
    """Code that calls ``DatasetBase.handle()`` after it has been closed
    should raise an exception.
    """
    with rasterio.open(path_rgb_byte_tif) as src:
        pass
    with pytest.raises(RasterioIOError):
        src.files

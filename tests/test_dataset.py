"""High level tests for Rasterio's ``GDALDataset`` abstractions."""


import os
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

import pytest

import rasterio
from rasterio.enums import Compression
from rasterio.errors import RasterioIOError


def test_files(data):
    tif = str(data.join('RGB.byte.tif'))
    aux = tif + '.aux.xml'
    with open(aux, 'w'):
        pass
    with rasterio.open(tif) as src:
        assert src.files == [tif, aux]


def test_handle_closed(path_rgb_byte_tif):
    """Code that calls ``DatasetBase.handle()`` after it has been closed
    should raise an exception.
    """
    with rasterio.open(path_rgb_byte_tif) as src:
        pass
    with pytest.raises(RasterioIOError):
        src.files


@pytest.mark.parametrize('tag_value', [item.value for item in Compression])
def test_dataset_compression(path_rgb_byte_tif, tag_value):
    """Compression is found from tags"""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        dataset.tags = MagicMock()
        dataset.tags.return_value = {'COMPRESSION': tag_value}
        assert dataset.compression == Compression(tag_value)

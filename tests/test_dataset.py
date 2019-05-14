"""High level tests for Rasterio's ``GDALDataset`` abstractions."""


import os
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

import pytest

import rasterio
from rasterio.enums import Compression
from rasterio.errors import RasterioIOError, DatasetAttributeError
from rasterio.transform import Affine


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


def test_untiled_dataset_blocksize(tmp_path):
    """Blocksize is not relevant to untiled datasets (see #1689)"""
    pytest.importorskip("pathlib")
    tmp_file = tmp_path / "test.tif"
    with rasterio.open(
            tmp_file, "w", driver="GTiff", count=1, height=13, width=13, dtype="uint8", crs="epsg:3857",
            transform=Affine.identity(), blockxsize=256, blockysize=256) as dataset:
        pass

    with rasterio.open(tmp_file) as dataset:
        assert not dataset.profile["tiled"]
        assert dataset.shape == (13, 13)


def test_tiled_dataset_blocksize_guard(tmp_path):
    """Tiled datasets with dimensions less than blocksize are not permitted"""
    pytest.importorskip("pathlib")
    tmp_file = tmp_path / "test.tif"
    with pytest.raises(ValueError):
        rasterio.open(
            tmp_file, "w", driver="GTiff", count=1, height=13, width=13, dtype="uint8", crs="epsg:3857",
            transform=Affine.identity(), tiled=True, blockxsize=256, blockysize=256)

def test_dataset_readonly_attributes(path_rgb_byte_tif):
    """Attempts to set read-only attributes fail with DatasetAttributeError"""
    with pytest.raises(DatasetAttributeError):
        with rasterio.open(path_rgb_byte_tif) as dataset:
            dataset.crs = "foo"


def test_dataset_readonly_attributes(path_rgb_byte_tif):
    """Attempts to set read-only attributes still fail with NotImplementedError"""
    with pytest.raises(NotImplementedError):
        with rasterio.open(path_rgb_byte_tif) as dataset:
            dataset.crs = "foo"

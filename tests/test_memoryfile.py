"""MemoryFile tests"""

import pytest

import rasterio
from rasterio.io import MemoryFile


@pytest.fixture(scope='function')
def rgb_file_bytes(path_rgb_byte_tif):
    return open(path_rgb_byte_tif, 'rb').read()


def test_initial_bytes(rgb_file_bytes):
    with MemoryFile(rgb_file_bytes) as memfile:
        with memfile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


def test_non_initial_bytes(rgb_file_bytes):
    with MemoryFile() as memfile:
        assert memfile.write(rgb_file_bytes) == len(rgb_file_bytes)
        with memfile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


def test_non_initial_bytearray(rgb_file_bytes):
    with MemoryFile() as memfile:
        assert memfile.write(bytearray(rgb_file_bytes)) == len(rgb_file_bytes)
        with memfile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


def test_no_initial_bytes(path_rgb_byte_tif):
    with rasterio.open(path_rgb_byte_tif) as src:
        data = src.read()
        profile = src.profile

    with MemoryFile() as memfile:
        with memfile.open(**profile) as dst:
            dst.write(data)

        view = memfile.getbuffer()
        assert view.size == 1706290

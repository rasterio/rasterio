"""MemoryFile tests"""

import logging

from packaging.version import parse
import pytest

import rasterio
from rasterio.io import MemoryFile


logging.basicConfig(level=logging.DEBUG)


# Custom markers.
mingdalversion = pytest.mark.skipif(
    parse(rasterio.__gdal_version__) < parse('2.0dev'),
    reason="MemoryFile requires GDAL 2.0")


@pytest.fixture(scope='function')
def rgb_file_bytes(path_rgb_byte_tif):
    return open(path_rgb_byte_tif, 'rb').read()


@mingdalversion
def test_initial_bytes(rgb_file_bytes):
    """MemoryFile contents can initialized from bytes and opened."""
    with MemoryFile(rgb_file_bytes) as memfile:
        with memfile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


@mingdalversion
def test_non_initial_bytes(rgb_file_bytes):
    """MemoryFile contents can be read from bytes and opened."""
    with MemoryFile() as memfile:
        assert memfile.write(rgb_file_bytes) == len(rgb_file_bytes)
        with memfile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


@mingdalversion
def test_non_initial_bytes_in_two(rgb_file_bytes):
    """MemoryFile contents can be read from bytes in two steps and opened."""
    with MemoryFile() as memfile:
        assert memfile.write(rgb_file_bytes[:10]) == 10
        assert memfile.write(rgb_file_bytes[10:]) == len(rgb_file_bytes) - 10
        with memfile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


@mingdalversion
def test_non_initial_bytearray(rgb_file_bytes):
    """MemoryFile contents can be read from bytearray and opened."""
    with MemoryFile() as memfile:
        assert memfile.write(bytearray(rgb_file_bytes)) == len(rgb_file_bytes)
        with memfile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


@pytest.fixture(scope='function')
def rgb_data_and_profile(path_rgb_byte_tif):
    with rasterio.open(path_rgb_byte_tif) as src:
        data = src.read()
        profile = src.profile
    return data, profile


@mingdalversion
def test_no_initial_bytes(rgb_data_and_profile):
    """An empty MemoryFile can be opened and written into."""
    data, profile = rgb_data_and_profile

    with MemoryFile() as memfile:
        with memfile.open(**profile) as dst:
            dst.write(data)
        view = memfile.getbuffer()
        # Exact size of the in-memory GeoTIFF varies with GDAL
        # version and configuration.
        assert view.size > 1000000
        data = bytearray(view)

    with MemoryFile(data) as memfile:
        with memfile.open() as src:
            assert sorted(src.profile.items()) == sorted(profile.items())


@mingdalversion
def test_read(tmpdir, rgb_file_bytes):
    """Reading from a MemoryFile works"""
    with MemoryFile(rgb_file_bytes) as memfile:
        tmptiff = tmpdir.join('test.tif')

        while 1:
            chunk = memfile.read(8192)
            if not chunk:
                break
            tmptiff.write(chunk, 'ab')

    with rasterio.open(str(tmptiff)) as src:
        assert src.count == 3

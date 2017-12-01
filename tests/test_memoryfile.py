"""MemoryFile tests.  MemoryFile requires GDAL 2.0+.
Tests in this file will ONLY run for GDAL >= 2.x"""

from io import BytesIO
import logging
import pytest

import rasterio
from rasterio.io import MemoryFile, ZipMemoryFile
from rasterio.env import GDALVersion

logging.basicConfig(level=logging.DEBUG)


# Skip ENTIRE module if not GDAL >= 2.x.
# pytestmark is a keyword that instructs pytest to skip this module.
pytestmark = pytest.mark.skipif(
    not GDALVersion.runtime().major >= 2,
    reason="MemoryFile requires GDAL 2.x")


@pytest.fixture(scope='session')
def rgb_file_bytes(path_rgb_byte_tif):
    """Get the bytes of our RGB.bytes.tif file"""
    return open(path_rgb_byte_tif, 'rb').read()


@pytest.fixture(scope='session')
def rgb_lzw_file_bytes():
    """Get the bytes of our RGB.bytes.tif file"""
    return open('tests/data/rgb_lzw.tif', 'rb').read()


@pytest.fixture(scope='function')
def rgb_file_object(path_rgb_byte_tif):
    """Get RGB.bytes.tif file opened in 'rb' mode"""
    return open(path_rgb_byte_tif, 'rb')


@pytest.fixture(scope='session')
def rgb_data_and_profile(path_rgb_byte_tif):
    with rasterio.open(path_rgb_byte_tif) as src:
        data = src.read()
        profile = src.profile
    return data, profile


def test_initial_not_bytes():
    """Creating a MemoryFile from not bytes fails."""
    with pytest.raises(TypeError):
        MemoryFile(u'lolwut')


def test_initial_bytes(rgb_file_bytes):
    """MemoryFile contents can initialized from bytes and opened."""
    with MemoryFile(rgb_file_bytes) as memfile:
        with memfile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


def test_initial_lzw_bytes(rgb_lzw_file_bytes):
    """MemoryFile contents can initialized from bytes and opened."""
    with MemoryFile(rgb_lzw_file_bytes) as memfile:
        with memfile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


def test_initial_file_object(rgb_file_object):
    """MemoryFile contents can initialized from bytes and opened."""
    with MemoryFile(rgb_file_object) as memfile:
        with memfile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


def test_closed():
    """A closed MemoryFile can not be opened"""
    with MemoryFile() as memfile:
        pass
    with pytest.raises(IOError):
        memfile.open()


def test_non_initial_bytes(rgb_file_bytes):
    """MemoryFile contents can be read from bytes and opened."""
    with MemoryFile() as memfile:
        assert memfile.write(rgb_file_bytes) == len(rgb_file_bytes)
        with memfile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


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


def test_non_initial_bytearray(rgb_file_bytes):
    """MemoryFile contents can be read from bytearray and opened."""
    with MemoryFile() as memfile:
        assert memfile.write(bytearray(rgb_file_bytes)) == len(rgb_file_bytes)
        with memfile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


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


def test_file_object_read(rgb_file_object):
    """An example of reading from a file object"""
    with rasterio.open(rgb_file_object) as src:
        assert src.driver == 'GTiff'
        assert src.count == 3
        assert src.dtypes == ('uint8', 'uint8', 'uint8')
        assert src.read().shape == (3, 718, 791)


def test_file_object_read_variant(rgb_file_bytes):
    """An example of reading from a MemoryFile object"""
    with rasterio.open(MemoryFile(rgb_file_bytes)) as src:
        assert src.driver == 'GTiff'
        assert src.count == 3
        assert src.dtypes == ('uint8', 'uint8', 'uint8')
        assert src.read().shape == (3, 718, 791)


def test_file_object_read_variant2(rgb_file_bytes):
    """An example of reading from a BytesIO object"""
    with rasterio.open(BytesIO(rgb_file_bytes)) as src:
        assert src.driver == 'GTiff'
        assert src.count == 3
        assert src.dtypes == ('uint8', 'uint8', 'uint8')
        assert src.read().shape == (3, 718, 791)


def test_test_file_object_write(tmpdir, rgb_data_and_profile):
    """An example of writing to a file object"""
    data, profile = rgb_data_and_profile
    with tmpdir.join('test.tif').open('wb') as fout:
        with rasterio.open(fout, 'w', **profile) as dst:
            dst.write(data)

    with rasterio.open(str(tmpdir.join('test.tif'))) as src:
        assert src.driver == 'GTiff'
        assert src.count == 3
        assert src.dtypes == ('uint8', 'uint8', 'uint8')
        assert src.read().shape == (3, 718, 791)


def test_nonpersistemt_memfile_fail_example(rgb_data_and_profile):
    """An example of writing to a file object"""
    data, profile = rgb_data_and_profile
    with BytesIO() as fout:
        with rasterio.open(fout, 'w', **profile) as dst:
            dst.write(data)

        # This fails because the MemoryFile created in open() is
        # gone.
        rasterio.open(fout)


def test_zip_closed():
    """A closed ZipMemoryFile can not be opened"""
    with ZipMemoryFile() as zipmemfile:
        pass
    with pytest.raises(IOError):
        zipmemfile.open('foo')


def test_zip_file_object_read(path_zip_file):
    """An example of reading from a zip file object"""
    with open(path_zip_file, 'rb') as zip_file_object:
        with ZipMemoryFile(zip_file_object) as zipmemfile:
            with zipmemfile.open('white-gemini-iv.vrt') as src:
                assert src.driver == 'VRT'
                assert src.count == 3
                assert src.dtypes == ('uint8', 'uint8', 'uint8')
                assert src.read().shape == (3, 768, 1024)

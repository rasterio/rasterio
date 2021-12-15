"""FilePath tests.  MemoryFile requires GDAL 2.0+.
Tests in this file will ONLY run for GDAL >= 3.x"""

from io import BytesIO
import os.path

import pytest

import rasterio
from rasterio.enums import MaskFlags
from rasterio.shutil import copyfiles

try:
    from rasterio.io import FilePath
except ImportError:
    pytest.skip("FilePath is not available for GDAL <3.0", allow_module_level=True)


@pytest.fixture(scope='function')
def rgb_lzw_file_object(path_rgb_lzw_byte_tif):
    """Get the open file of our RGB.bytes.tif file."""
    return open(path_rgb_lzw_byte_tif, 'rb')


@pytest.fixture(scope='function')
def rgb_file_object(path_rgb_byte_tif):
    """Get RGB.bytes.tif file opened in 'rb' mode"""
    return open(path_rgb_byte_tif, 'rb')


def test_initial_empty():
    with pytest.raises(TypeError):
        FilePath()


def test_initial_not_file_str():
    """Creating from not file-like fails."""
    with pytest.raises(TypeError):
        FilePath(u'lolwut')


def test_initial_not_file_bytes():
    """Creating from not file-like fails."""
    with pytest.raises(TypeError):
        FilePath(b'lolwut')


def test_initial_bytes(rgb_file_object):
    """FilePath contents can initialized from bytes and opened."""
    with FilePath(rgb_file_object) as vsifile:
        with vsifile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


def test_initial_lzw_bytes(rgb_lzw_file_object):
    """FilePath contents can initialized from bytes and opened."""
    with FilePath(rgb_lzw_file_object) as vsifile:
        with vsifile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


def test_initial_file_object(rgb_file_object):
    """FilePath contents can initialized from bytes and opened."""
    with FilePath(rgb_file_object) as vsifile:
        with vsifile.open() as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)


def test_closed(rgb_file_object):
    """A closed FilePath can not be opened."""
    with FilePath(rgb_file_object) as vsifile:
        pass
    with pytest.raises(IOError):
        vsifile.open()


def test_file_object_read(rgb_file_object):
    """An example of reading from a file object"""
    with rasterio.open(rgb_file_object) as src:
        assert src.driver == 'GTiff'
        assert src.count == 3
        assert src.dtypes == ('uint8', 'uint8', 'uint8')
        assert src.read().shape == (3, 718, 791)


def test_file_object_read_variant(rgb_file_object):
    """An example of reading from a FilePath object"""
    with rasterio.open(FilePath(rgb_file_object)) as src:
        assert src.driver == 'GTiff'
        assert src.count == 3
        assert src.dtypes == ('uint8', 'uint8', 'uint8')
        assert src.read().shape == (3, 718, 791)


def test_file_object_read_variant2(rgb_file_object):
    """An example of reading from a BytesIO object version of a file's contents."""
    with rasterio.open(BytesIO(rgb_file_object.read())) as src:
        assert src.driver == 'GTiff'
        assert src.count == 3
        assert src.dtypes == ('uint8', 'uint8', 'uint8')
        assert src.read().shape == (3, 718, 791)


def test_vrt_vsifile(data_dir, path_white_gemini_iv_vrt):
    """Successfully read an in-memory VRT"""
    with open(path_white_gemini_iv_vrt) as vrtfile:
        source = vrtfile.read()
        source = source.replace('<SourceFilename relativeToVRT="1">389225main_sw_1965_1024.jpg</SourceFilename>', '<SourceFilename relativeToVRT="0">{}/389225main_sw_1965_1024.jpg</SourceFilename>'.format(data_dir))
        source = BytesIO(source.encode('utf-8'))

    with FilePath(source) as vsifile:
        with vsifile.open() as src:
            assert src.driver == 'VRT'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 768, 1024)


@pytest.mark.xfail(reason="Copying is not supported by FilePath")
def test_vsifile_copyfiles(path_rgb_msk_byte_tif):
    """Multiple files can be copied to a FilePath using copyfiles"""
    with rasterio.open(path_rgb_msk_byte_tif) as src:
        src_basename = os.path.basename(src.name)
        with FilePath(dirname="foo", filename=src_basename) as vsifile:
            copyfiles(src.name, vsifile.name)
            with vsifile.open() as rgb2:
                assert sorted(rgb2.files) == sorted(['/vsimem/foo/{}'.format(src_basename), '/vsimem/foo/{}.msk'.format(src_basename)])


@pytest.mark.xfail(reason="FilePath does not implement '.files' property properly.")
def test_multi_vsifile(path_rgb_msk_byte_tif):
    """Multiple files can be copied to a FilePath using copyfiles"""
    with open(path_rgb_msk_byte_tif, 'rb') as tif_fp, open(path_rgb_msk_byte_tif + '.msk', 'rb') as msk_fp:
        with FilePath(tif_fp, dirname="bar", filename='foo.tif') as tifvsifile, \
                FilePath(msk_fp, dirname="bar", filename='foo.tif.msk') as mskvsifile:
            with tifvsifile.open() as src:
                assert sorted(os.path.basename(fn) for fn in src.files) == sorted(['foo.tif', 'foo.tif.msk'])
                assert src.mask_flag_enums == ([MaskFlags.per_dataset],) * 3


def _open_geotiff(file_path):
    with open(file_path, 'rb') as file_obj:
        with rasterio.open(file_obj) as dataset:
            dataset.read()


def test_concurrent(path_rgb_byte_tif, path_rgb_lzw_byte_tif, path_cogeo_tif, path_alpha_tif):
    """Test multiple threads opening multiple files at the same time."""
    from concurrent.futures import ThreadPoolExecutor
    tifs = [path_rgb_byte_tif, path_rgb_lzw_byte_tif, path_cogeo_tif, path_alpha_tif] * 4
    with ThreadPoolExecutor(max_workers=8) as exe:
        list(exe.map(_open_geotiff, tifs, timeout=5))

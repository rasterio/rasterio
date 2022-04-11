"""MemoryFile tests.  MemoryFile requires GDAL 2.0+.
Tests in this file will ONLY run for GDAL >= 2.x"""

from io import BytesIO
import logging
import os.path

from affine import Affine
import numpy
import pytest

import rasterio
from rasterio.io import MemoryFile, ZipMemoryFile
from rasterio.enums import MaskFlags
from rasterio.env import GDALVersion
from rasterio.shutil import copyfiles


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
def rgb_lzw_file_bytes(path_rgb_lzw_byte_tif):
    """Get the bytes of our RGB.bytes.tif file"""
    return open(path_rgb_lzw_byte_tif, 'rb').read()


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


def test_initial_empty():
    with MemoryFile() as memfile:
        assert len(memfile) == 0
        assert len(memfile.getbuffer()) == 0
        assert memfile.tell() == 0


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
    with pytest.raises(OSError):
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


def test_non_initial_bytes_in_two_reverse(rgb_file_bytes):
    """MemoryFile contents can be read from bytes in two steps, tail first, and opened.
    Demonstrates fix of #1926."""
    with MemoryFile() as memfile:
        memfile.seek(600000)
        assert memfile.write(rgb_file_bytes[600000:]) == len(rgb_file_bytes) - 600000
        memfile.seek(0)
        assert memfile.write(rgb_file_bytes[:600000]) == 600000
        with memfile.open() as src:
            assert src.driver == "GTiff"
            assert src.count == 3
            assert src.dtypes == ("uint8", "uint8", "uint8")
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
        # NB: bytes(view) doesn't return what you'd expect with python 2.7.
        data = bytes(bytearray(view))

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


def test_file_object_read_filepath(monkeypatch, request, capfd, rgb_file_object):
    """Opening a file object with FilePath returns a dataset with no attached MemoryFile."""
    with rasterio.open(rgb_file_object) as src:
        assert src.driver == 'GTiff'
        assert src.count == 3
        assert src.dtypes == ('uint8', 'uint8', 'uint8')
        assert src.read().shape == (3, 718, 791)


def test_file_object_read_memfile(monkeypatch, request, capfd, rgb_file_object):
    """Opening a file object without FilePath returns a dataset with attached MemoryFile."""
    monkeypatch.setattr(rasterio, "have_vsi_plugin", False)
    with rasterio.Env() as env:
        with rasterio.open(rgb_file_object) as src:
            assert src.driver == 'GTiff'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 718, 791)

        # Exiting src causes the attached MemoryFile context to be
        # exited and the temporary in-memory file is deleted.
        env._dump_open_datasets()
        captured = capfd.readouterr()
        assert "/vsimem/{}".format(request.node.name) not in captured.err


def test_issue2360_no_with(monkeypatch, request, capfd, rgb_file_object):
    """Opening a file object without FilePath returns a dataset with attached MemoryFile."""
    monkeypatch.setattr(rasterio, "have_vsi_plugin", False)
    with rasterio.Env() as env:
        src = rasterio.open(rgb_file_object)
        assert src.driver == 'GTiff'
        assert src.count == 3
        assert src.dtypes == ('uint8', 'uint8', 'uint8')
        assert src.read().shape == (3, 718, 791)

        env._dump_open_datasets()
        captured = capfd.readouterr()
        assert "/vsimem/{}".format(request.node.name) in captured.err

        # Closing src causes the attached MemoryFile context to be
        # exited and the temporary in-memory file is deleted.
        src.close()
        env._dump_open_datasets()
        captured = capfd.readouterr()
        assert "/vsimem/{}".format(request.node.name) not in captured.err


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


def test_zip_closed():
    """A closed ZipMemoryFile can not be opened"""
    with ZipMemoryFile() as zipmemfile:
        pass
    with pytest.raises(OSError):
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


def test_vrt_memfile(data_dir, path_white_gemini_iv_vrt):
    """Successfully read an in-memory VRT"""
    with open(path_white_gemini_iv_vrt) as vrtfile:
        source = vrtfile.read()
        source = source.replace('<SourceFilename relativeToVRT="1">389225main_sw_1965_1024.jpg</SourceFilename>', '<SourceFilename relativeToVRT="0">{}/389225main_sw_1965_1024.jpg</SourceFilename>'.format(data_dir))

    with MemoryFile(source.encode('utf-8'), ext='vrt') as memfile:
        with memfile.open() as src:
            assert src.driver == 'VRT'
            assert src.count == 3
            assert src.dtypes == ('uint8', 'uint8', 'uint8')
            assert src.read().shape == (3, 768, 1024)


def test_write_plus_mode():
    with MemoryFile() as memfile:
        with memfile.open(driver='GTiff', dtype='uint8', count=3, height=32, width=32, crs='epsg:3226', transform=Affine.identity() * Affine.scale(0.5, -0.5)) as dst:
            dst.write(numpy.full((32, 32), 255, dtype='uint8'), 1)
            dst.write(numpy.full((32, 32), 204, dtype='uint8'), 2)
            dst.write(numpy.full((32, 32), 153, dtype='uint8'), 3)
            data = dst.read()
            assert (data[0] == 255).all()
            assert (data[1] == 204).all()
            assert (data[2] == 153).all()


def test_write_plus_model_jpeg():
    with rasterio.Env(), MemoryFile() as memfile:
        with memfile.open(driver='JPEG', dtype='uint8', count=3, height=32, width=32, crs='epsg:3226', transform=Affine.identity() * Affine.scale(0.5, -0.5)) as dst:
            dst.write(numpy.full((32, 32), 255, dtype='uint8'), 1)
            dst.write(numpy.full((32, 32), 204, dtype='uint8'), 2)
            dst.write(numpy.full((32, 32), 153, dtype='uint8'), 3)
            data = dst.read()
            assert (data[0] == 255).all()
            assert (data[1] == 204).all()
            assert (data[2] == 153).all()


def test_memfile_copyfiles(path_rgb_msk_byte_tif):
    """Multiple files can be copied to a MemoryFile using copyfiles"""
    with rasterio.open(path_rgb_msk_byte_tif) as src:
        src_basename = os.path.basename(src.name)
        with MemoryFile(dirname="foo", filename=src_basename) as memfile:
            copyfiles(src.name, memfile.name)
            with memfile.open() as rgb2:
                assert sorted(rgb2.files) == sorted(['/vsimem/foo/{}'.format(src_basename), '/vsimem/foo/{}.msk'.format(src_basename)])


def test_multi_memfile(path_rgb_msk_byte_tif):
    """Multiple files can be copied to a MemoryFile using copyfiles"""
    with open(path_rgb_msk_byte_tif, 'rb') as tif_fp:
        tif_bytes = tif_fp.read()
    with open(path_rgb_msk_byte_tif + '.msk', 'rb') as msk_fp:
        msk_bytes = msk_fp.read()

    with MemoryFile(tif_bytes, dirname="bar", filename='foo.tif') as tifmemfile, MemoryFile(msk_bytes, dirname="bar", filename='foo.tif.msk') as mskmemfile:
        with tifmemfile.open() as src:
            assert sorted(os.path.basename(fn) for fn in src.files) == sorted(['foo.tif', 'foo.tif.msk'])
            assert src.mask_flag_enums == ([MaskFlags.per_dataset],) * 3


def test_memory_file_gdal_error_message(capsys):
    """No weird error messages should be seen, see #1659"""
    memfile = MemoryFile()
    data = numpy.array([[1,2,3,4],[5,6,7,8],[9,10,11,12],[13,14,15,16]]).astype('uint8')
    west_bound = 0; north_bound = 2; cellsize=0.5; nodata = -9999; driver='AAIGrid';
    dtype = data.dtype
    shape = data.shape
    transform = rasterio.transform.from_origin(west_bound, north_bound, cellsize, cellsize)
    dataset = memfile.open(driver=driver, width=shape[1], height=shape[0], transform=transform, count=1, dtype=dtype, nodata=nodata, crs='epsg:3226')
    dataset.write(data, 1)
    dataset.close()
    captured = capsys.readouterr()
    assert "ERROR 4" not in captured.err
    assert "ERROR 4" not in captured.out


def test_write_plus_mode_requires_width():
    """Width is required"""
    with MemoryFile() as memfile:
        with pytest.raises(TypeError):
            memfile.open(driver='GTiff', dtype='uint8', count=3, height=32, crs='epsg:3226', transform=Affine.identity() * Affine.scale(0.5, -0.5))


def test_write_plus_mode_blockxsize_requires_width():
    """Width is required"""
    with MemoryFile() as memfile:
        with pytest.raises(TypeError):
            memfile.open(driver='GTiff', dtype='uint8', count=3, height=32, crs='epsg:3226', transform=Affine.identity() * Affine.scale(0.5, -0.5), blockxsize=128)


def test_write_rpcs_to_memfile(path_rgb_byte_rpc_vrt):
    """Ensure we can write rpcs to a new MemoryFile"""
    with rasterio.open(path_rgb_byte_rpc_vrt) as src:
        profile = src.profile.copy()
        with MemoryFile() as memfile:
            with memfile.open(**profile) as dst:
                assert dst.rpcs is None
                dst.rpcs = src.rpcs
                assert dst.rpcs

import logging
import sys

import pytest

import rasterio
from rasterio.profiles import default_gtiff_profile
from rasterio.vfs import parse_path, vsi_path


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_parse_path_with_vfs():
    """Correctly parse path with legacy vfs parameter"""
    assert parse_path('foo.tif', vfs='zip://tests/data/files.zip') == (
        'foo.tif', 'tests/data/files.zip', 'zip')


def test_parse_path_zip():
    """Correctly parse zip scheme URL"""
    assert parse_path('zip://tests/data/files.zip!foo.tif') == (
        'foo.tif', 'tests/data/files.zip', 'zip')


def test_parse_path_file_scheme():
    """Correctly parse file:// URL"""
    assert parse_path('file://foo.tif') == (
        'foo.tif', None, 'file')


def test_parse_path_file():
    """Correctly parse an ordinary filesystem path"""
    assert parse_path('/foo.tif') == (
        '/foo.tif', None, '')


def test_parse_gdal():
    """GDAL dataset identifiers fall through properly"""
    assert parse_path('GDAL:filepath:varname') == (
        'GDAL:filepath:varname', None, None)


def test_vsi_path_scheme():
    """Correctly make a vsi path"""
    assert vsi_path(
        'foo.tif', 'tests/data/files.zip', 'zip') == '/vsizip/tests/data/files.zip/foo.tif'


def test_vsi_path_file():
    """Correctly make and ordinary file path from a file path"""
    assert vsi_path(
        'foo.tif', None, 'file') == 'foo.tif'


def test_read_vfs_zip():
    with rasterio.open(
            'zip://tests/data/files.zip!/RGB.byte.tif') as src:
        assert src.name == 'zip://tests/data/files.zip!/RGB.byte.tif'
        assert src.count == 3


def test_read_vfs_file():
    with rasterio.open(
            'file://tests/data/RGB.byte.tif') as src:
        assert src.name == 'file://tests/data/RGB.byte.tif'
        assert src.count == 3

def test_read_vfs_zip_cmp_array():
    with rasterio.open(
            'zip://tests/data/files.zip!/RGB.byte.tif') as src:
        zip_arr = src.read()

    with rasterio.open(
            'file://tests/data/RGB.byte.tif') as src:
        file_arr = src.read()

    assert zip_arr.dumps() == file_arr.dumps()


def test_read_vfs_none():
    with rasterio.open(
            'tests/data/RGB.byte.tif') as src:
        assert src.name == 'tests/data/RGB.byte.tif'
        assert src.count == 3


@pytest.mark.parametrize('mode', ['r+', 'w'])
def test_update_vfs(tmpdir, mode):
    """VFS datasets can not be created or updated"""
    profile = default_gtiff_profile.copy()
    profile.update(count=1, width=1, height=1)
    with pytest.raises(TypeError):
        rasterio.open('zip://{0}'.format(tmpdir), mode, **profile)


def test_parse_path_accept_get_params():
    # See https://github.com/mapbox/rasterio/issues/1121
    assert parse_path('http://example.com/index?a=1') == (
        'example.com/index?a=1', None, 'http')

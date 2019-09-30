"""Tests of rasterio.path"""

import sys

import pytest

import rasterio
from rasterio.path import parse_path, vsi_path, ParsedPath, UnparsedPath


def test_parsed_path_name():
    """A parsed path's name property is correct"""
    assert ParsedPath('bar.tif', 'foo.zip', 'zip').name == 'zip://foo.zip!bar.tif'


def test_parsed_path_name_no_archive():
    """A parsed path's name property is correct"""
    assert ParsedPath('bar.tif', None, 'file').name == 'file://bar.tif'


def test_parsed_path_name_no_scheme():
    """A parsed path's name property is correct"""
    assert ParsedPath('bar.tif', None, None).name == 'bar.tif'


def test_unparsed_path_name():
    """An unparsed path's name property is correct"""
    assert UnparsedPath('/vsifoo/bar/tif').name == '/vsifoo/bar/tif'


@pytest.mark.parametrize('scheme', ['s3', 'ftp', 'http', 'https', 'zip+s3'])
def test_parsed_path_remote(scheme):
    """A parsed path is remote"""
    assert ParsedPath('example.com/foo.tif', None, scheme).is_remote


@pytest.mark.parametrize('scheme', [None, '', 'zip', 'tar', 'file', 'zip+file'])
def test_parsed_path_file_local(scheme):
    """A parsed path is remote"""
    assert ParsedPath('foo.tif', None, scheme).is_local


def test_parse_path_zip():
    """Correctly parse zip scheme URL"""
    parsed = parse_path('zip://tests/data/files.zip!foo.tif')
    assert parsed.path == 'foo.tif'
    assert parsed.archive == 'tests/data/files.zip'
    assert parsed.scheme == 'zip'


def test_parse_path_zip_and_file():
    """Correctly parse zip+file scheme URL"""
    parsed = parse_path('zip+file://tests/data/files.zip!foo.tif')
    assert parsed.path == 'foo.tif'
    assert parsed.archive == 'tests/data/files.zip'
    assert parsed.scheme == 'zip+file'


def test_parse_path_file_scheme():
    """Correctly parse file:// URL"""
    parsed = parse_path('file://foo.tif')
    assert parsed.path == 'foo.tif'
    assert parsed.archive is None
    assert parsed.scheme == 'file'


def test_parse_path_file():
    """Correctly parse an ordinary filesystem path"""
    parsed = parse_path('/foo.tif')
    assert parsed.path == '/foo.tif'


def test_parse_gdal_vsi():
    """GDAL dataset identifiers fall through properly"""
    assert parse_path('/vsifoo/bar').path == '/vsifoo/bar'


def test_parse_gdal():
    """GDAL dataset identifiers fall through properly"""
    assert parse_path('GDAL:filepath:varname').path == 'GDAL:filepath:varname'


def test_parse_windows_path(monkeypatch):
    """Return Windows paths unparsed"""
    monkeypatch.setattr(sys, 'platform', 'win32')
    assert parse_path(r'C:\\foo.tif').path == r'C:\\foo.tif'


def test_vsi_path_scheme():
    """Correctly make a vsi path"""
    assert vsi_path(ParsedPath('/foo.tif', 'tests/data/files.zip', 'zip')) == '/vsizip/tests/data/files.zip/foo.tif'


def test_vsi_path_file():
    """Correctly make and ordinary file path from a file path"""
    assert vsi_path(ParsedPath('foo.tif', None, 'file')) == 'foo.tif'


def test_vsi_path_curl():
    """Correctly make and ordinary file path from a https path"""
    assert vsi_path(ParsedPath('example.com/foo.tif', None, 'https')) == '/vsicurl/https://example.com/foo.tif'


def test_vsi_path_unparsed():
    """Correctly make GDAL filename from unparsed path"""
    assert vsi_path(UnparsedPath("foo")) == "foo"


def test_vsi_path_error():
    """Raise ValuError if argument is not a path"""
    with pytest.raises(ValueError):
        vsi_path("foo")


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


def test_parse_path_accept_get_params():
    # See https://github.com/mapbox/rasterio/issues/1121
    parsed = parse_path('http://example.com/index?a=1')
    assert isinstance(parsed, ParsedPath)
    assert parsed.path == 'example.com/index?a=1'
    assert parsed.archive is None
    assert parsed.scheme == 'http'


def test_vsi_path_zip():
    """A zip:// URLs vsi path is correct (see #1377)"""
    url = 'zip:///path/to/zip/some.zip!path/to/file.txt'
    assert vsi_path(parse_path(url)) == '/vsizip//path/to/zip/some.zip/path/to/file.txt'


def test_vsi_path_zip_plus_https():
    """A zip+https:// URLs vsi path is correct (see #1151)"""
    url = 'zip+https://example.com/foo.zip!bar.tif'
    assert vsi_path(parse_path(url)) == '/vsizip/vsicurl/https://example.com/foo.zip/bar.tif'

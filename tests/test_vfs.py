import pytest

from rasterio.errors import RasterioDeprecationWarning
from rasterio.vfs import parse_path, vsi_path


def test_vsi_path():
    """Warn deprecation of old vsi_path"""
    with pytest.warns(RasterioDeprecationWarning):
        assert vsi_path('/foo.tif', 'tests/data/files.zip', 'zip') == '/vsizip/tests/data/files.zip/foo.tif'


def test_vsi_unparsed_path():
    """Warn deprecation of old vsi_path"""
    with pytest.warns(RasterioDeprecationWarning):
        assert vsi_path('foo.tif', None, None) == 'foo.tif'


def test_parse_path():
    """Warn deprecation of old parse_path"""
    with pytest.warns(RasterioDeprecationWarning):
        assert parse_path('foo.tif') == ('foo.tif', None, None)


def test_parse_path_with_vfs():
    """Warn deprecation of old parse_path"""
    with pytest.warns(RasterioDeprecationWarning):
        assert parse_path('foo.tif', vfs='zip://tests/data/files.zip') == ('foo.tif', 'tests/data/files.zip', 'zip')


def test_parse_path_vsi():
    """Warn deprecation of old parse_path"""
    with pytest.warns(RasterioDeprecationWarning):
        assert parse_path('/vsifoo/bar.tif') == ('/vsifoo/bar.tif', None, None)

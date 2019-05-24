"""Tests of _env util module"""

import pytest

from rasterio._env import GDALDataFinder, PROJDataFinder

from .conftest import gdal_version, requires_gdal_lt_3


@pytest.fixture
def mock_wheel(tmpdir):
    """A fake rasterio wheel"""
    moduledir = tmpdir.mkdir("rasterio")
    moduledir.ensure("__init__.py")
    moduledir.ensure("_env.py")
    moduledir.ensure("gdal_data/pcs.csv")
    moduledir.ensure("proj_data/epsg")
    return moduledir


@pytest.fixture
def mock_fhs(tmpdir):
    """A fake FHS system"""
    tmpdir.ensure("share/gdal/pcs.csv")
    tmpdir.ensure("share/proj/epsg")
    return tmpdir


@pytest.fixture
def mock_debian(tmpdir):
    """A fake Debian multi-install system"""
    tmpdir.ensure("share/gdal/1.11/pcs.csv")
    tmpdir.ensure("share/gdal/2.0/pcs.csv")
    tmpdir.ensure("share/gdal/2.1/pcs.csv")
    tmpdir.ensure("share/gdal/2.2/pcs.csv")
    tmpdir.ensure("share/gdal/2.3/pcs.csv")
    tmpdir.ensure("share/gdal/2.4/pcs.csv")
    tmpdir.ensure("share/gdal/2.5/pcs.csv")
    tmpdir.ensure("share/proj/epsg")
    return tmpdir


def test_search_wheel_gdal_data_failure(tmpdir):
    """Fail to find GDAL data in a non-wheel"""
    finder = GDALDataFinder()
    assert not finder.search_wheel(str(tmpdir))


def test_search_wheel_gdal_data(mock_wheel):
    """Find GDAL data in a wheel"""
    finder = GDALDataFinder()
    assert finder.search_wheel(str(mock_wheel.join("_env.py"))) == str(mock_wheel.join("gdal_data"))


def test_search_prefix_gdal_data_failure(tmpdir):
    """Fail to find GDAL data in a bogus prefix"""
    finder = GDALDataFinder()
    assert not finder.search_prefix(str(tmpdir))


def test_search_prefix_gdal_data(mock_fhs):
    """Find GDAL data under prefix"""
    finder = GDALDataFinder()
    assert finder.search_prefix(str(mock_fhs)) == str(mock_fhs.join("share").join("gdal"))


def test_search_debian_gdal_data_failure(tmpdir):
    """Fail to find GDAL data in a bogus Debian location"""
    finder = GDALDataFinder()
    assert not finder.search_debian(str(tmpdir))


@requires_gdal_lt_3
def test_search_debian_gdal_data(mock_debian):
    """Find GDAL data under Debian locations"""
    finder = GDALDataFinder()
    assert finder.search_debian(str(mock_debian)) == str(mock_debian.join("share").join("gdal").join("{}".format(str(gdal_version))))


def test_search_gdal_data_wheel(mock_wheel):
    finder = GDALDataFinder()
    assert finder.search(str(mock_wheel.join("_env.py"))) == str(mock_wheel.join("gdal_data"))


def test_search_gdal_data_fhs(mock_fhs):
    finder = GDALDataFinder()
    assert finder.search(str(mock_fhs)) == str(mock_fhs.join("share").join("gdal"))


@requires_gdal_lt_3
def test_search_gdal_data_debian(mock_debian):
    """Find GDAL data under Debian locations"""
    finder = GDALDataFinder()
    assert finder.search(str(mock_debian)) == str(mock_debian.join("share").join("gdal").join("{}".format(str(gdal_version))))


def test_search_wheel_proj_data_failure(tmpdir):
    """Fail to find GDAL data in a non-wheel"""
    finder = PROJDataFinder()
    assert not finder.search_wheel(str(tmpdir))


def test_search_wheel_proj_data(mock_wheel):
    """Find GDAL data in a wheel"""
    finder = PROJDataFinder()
    assert finder.search_wheel(str(mock_wheel.join("_env.py"))) == str(mock_wheel.join("proj_data"))


def test_search_prefix_proj_data_failure(tmpdir):
    """Fail to find GDAL data in a bogus prefix"""
    finder = PROJDataFinder()
    assert not finder.search_prefix(str(tmpdir))


def test_search_prefix_proj_data(mock_fhs):
    """Find GDAL data under prefix"""
    finder = PROJDataFinder()
    assert finder.search_prefix(str(mock_fhs)) == str(mock_fhs.join("share").join("proj"))


def test_search_proj_data_wheel(mock_wheel):
    finder = PROJDataFinder()
    assert finder.search(str(mock_wheel.join("_env.py"))) == str(mock_wheel.join("proj_data"))


def test_search_proj_data_fhs(mock_fhs):
    finder = PROJDataFinder()
    assert finder.search(str(mock_fhs)) == str(mock_fhs.join("share").join("proj"))

import pytest

from rasterio._version import get_gdal_version_info, get_geos_version, get_proj_version


@pytest.mark.parametrize(
    "key",
    [
        "--version",
        "doesnotexist",
        "VERSION_NUM",
    ],
)
def test_get_gdal_version_info(key):
    assert isinstance(get_gdal_version_info(key), str)


def test_get_proj_version():
    proj_version = get_proj_version()
    assert isinstance(proj_version, tuple)
    assert len(proj_version) == 3
    for version in proj_version:
        assert isinstance(version, int)


def test_get_geos_version():
    geos_version = get_geos_version()
    assert isinstance(geos_version, tuple)
    assert len(geos_version) == 3
    for version in geos_version:
        assert isinstance(version, int)

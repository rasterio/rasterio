"""Tests of overview counting and creation."""

import pytest

import rasterio
from rasterio.enums import Resampling
from rasterio.env import GDALVersion
from rasterio.errors import OverviewCreationError


gdal_version = GDALVersion()


def test_count_overviews_zero(data):
    inputfile = str(data.join('RGB.byte.tif'))
    with rasterio.open(inputfile) as src:
        assert src.overviews(1) == []
        assert src.overviews(2) == []
        assert src.overviews(3) == []


def test_build_overviews_one(data):
    inputfile = str(data.join('RGB.byte.tif'))
    with rasterio.open(inputfile, 'r+') as src:
        overview_factors = [2]
        src.build_overviews(overview_factors, resampling=Resampling.nearest)
        assert src.overviews(1) == [2]
        assert src.overviews(2) == [2]
        assert src.overviews(3) == [2]


def test_build_overviews_two(data):
    inputfile = str(data.join('RGB.byte.tif'))
    with rasterio.open(inputfile, 'r+') as src:
        overview_factors = [2, 4]
        src.build_overviews(overview_factors, resampling=Resampling.nearest)
        assert src.overviews(1) == [2, 4]
        assert src.overviews(2) == [2, 4]
        assert src.overviews(3) == [2, 4]


@pytest.mark.xfail(
    gdal_version < GDALVersion.parse('2.0'),
    reason="Bilinear resampling not supported by GDAL < 2.0")
def test_build_overviews_bilinear(data):
    inputfile = str(data.join('RGB.byte.tif'))
    with rasterio.open(inputfile, 'r+') as src:
        overview_factors = [2, 4]
        src.build_overviews(overview_factors, resampling=Resampling.bilinear)
        assert src.overviews(1) == [2, 4]
        assert src.overviews(2) == [2, 4]
        assert src.overviews(3) == [2, 4]


def test_build_overviews_average(data):
    inputfile = str(data.join('RGB.byte.tif'))
    with rasterio.open(inputfile, 'r+') as src:
        overview_factors = [2, 4]
        src.build_overviews(overview_factors, resampling=Resampling.average)
        assert src.overviews(1) == [2, 4]
        assert src.overviews(2) == [2, 4]
        assert src.overviews(3) == [2, 4]


def test_build_overviews_gauss(data):
    inputfile = str(data.join('RGB.byte.tif'))
    with rasterio.open(inputfile, 'r+') as src:
        overview_factors = [2, 4]
        src.build_overviews(overview_factors, resampling=Resampling.gauss)
        assert src.overviews(1) == [2, 4]
        assert src.overviews(2) == [2, 4]
        assert src.overviews(3) == [2, 4]


def test_test_unsupported_algo(data):
    inputfile = str(data.join('RGB.byte.tif'))
    with pytest.raises(ValueError):
        with rasterio.open(inputfile, 'r+') as src:
            overview_factors = [2, 4]
            src.build_overviews(overview_factors, resampling=Resampling.q1)


def test_issue1333(data):
    """Fail if asked to create more than one 1x1 overview"""
    inputfile = str(data.join('RGB.byte.tif'))
    with pytest.raises(OverviewCreationError):
        with rasterio.open(inputfile, 'r+') as src:
            overview_factors = [1024, 2048]
            src.build_overviews(
                overview_factors, resampling=Resampling.average)


def test_build_overviews_new_file(tmpdir, path_rgb_byte_tif):
    """Confirm fix of #1497"""
    dst_file = str(tmpdir.join('test.tif'))
    with rasterio.open(path_rgb_byte_tif) as src:
        with rasterio.open(dst_file, 'w', **src.profile) as dst:
            dst.write(src.read())
            overview_factors = [2, 4]
            dst.build_overviews(
                overview_factors, resampling=Resampling.nearest)

    with rasterio.open(dst_file, overview_level=1) as src:
        data = src.read()
        assert data.any()

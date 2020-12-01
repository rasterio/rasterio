"""Tests of overview counting and creation."""
import math

import numpy as np
import pytest

from .conftest import requires_gdal2, requires_gdal33

import rasterio
from rasterio.enums import Resampling
from rasterio.env import GDALVersion
from rasterio.errors import OverviewCreationError


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
    GDALVersion.runtime() < GDALVersion.parse("2.0"),
    reason="Bilinear resampling not supported by GDAL < 2.0",
)
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


@requires_gdal2
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


@requires_gdal33
def test_ignore_overviews(data):
    """open dataset with OVERVIEW_LEVEL=-1, overviews should be ignored"""
    inputfile = str(data.join('RGB.byte.tif'))
    with rasterio.open(inputfile, 'r+') as src:
        src.build_overviews([2], resampling=Resampling.nearest)

    with rasterio.open(inputfile, OVERVIEW_LEVEL=-1) as src:
        assert src.overviews(1) == []
        assert src.overviews(2) == []
        assert src.overviews(3) == []


@requires_gdal33
def test_decimated_no_use_overview(red_green):
    """Force ignore existing overviews when performing decimated read"""
    # Corrupt overview of red file
    green_ovr = red_green.join("green.tif.ovr")
    green_ovr.rename(red_green.join("red.tif.ovr"))
    assert not green_ovr.exists()
    # Read the corrupted red overview
    with rasterio.open(str(red_green.join("red.tif.ovr"))) as ovr:
        ovr_data = ovr.read()
        ovr_shape = ovr_data.shape
        assert (ovr_data[1] == 204).all()
    # Perform decimated read and ensure no use of file overview (different from corrupted)
    with rasterio.open(str(red_green.join("red.tif")), OVERVIEW_LEVEL=-1) as src:
        decimated_data = src.read(out_shape=ovr_shape)
        assert not np.array_equal(ovr_data, decimated_data)

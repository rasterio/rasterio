"""Tests of overview counting and creation."""

import logging
import sys

import pytest

import rasterio
from rasterio.enums import Resampling

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


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

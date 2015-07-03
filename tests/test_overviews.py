"""Tests of overview counting and creation."""

import logging
import sys

from click.testing import CliRunner

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_count_overviews(data):
    inputfile = str(data.join('RGB.byte.tif'))
    with rasterio.open(inputfile) as dst:
        assert dst.overview_count == 0

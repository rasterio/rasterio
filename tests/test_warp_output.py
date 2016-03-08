import logging
import sys
import pytest
from affine import Affine
import numpy

import rasterio
from rasterio import crs
from rasterio.warp import (
    reproject, Resampling, transform_geom, transform, transform_bounds,
    calculate_default_transform)
from rasterio._warp import _calculate_default_transform


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


#DST_TRANSFORM = Affine.from_gdal(-8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0)


def test_default_transform_dateline_to_dateline():
    """Test new impl"""
    with rasterio.drivers():
        transform, w, h = _calculate_default_transform(
            crs.from_epsg(4326), crs.from_epsg(3857), 360, 150, -180.0, -75.0, 180.0, 75.0)
        assert (transform, w, h) == calculate_default_transform(
            crs.from_epsg(4326), crs.from_epsg(3857), 360, 150, -180.0, -75.0, 180.0, 75.0)

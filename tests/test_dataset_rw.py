"""Tests of r+ and w+ modes"""

import numpy as np
import pytest

import rasterio
from rasterio.errors import RasterioDeprecationWarning
from rasterio.profiles import DefaultGTiffProfile


def test_read_wplus_mode(tmpdir):
    """A dataset opened in 'w+' mode can be read"""
    path = tmpdir.join('test.tif')
    profile = DefaultGTiffProfile(count=1, width=300, height=300)

    with rasterio.open(str(path), "w+", **profile) as dst:

        dst.write(255 * np.ones((1, 300, 300), dtype='uint8'))

        assert (dst.read() == 255).all()

        dst.write(3 * np.ones((1, 300, 300), dtype='uint8'))

        assert (dst.read() == 3).all()


def test_read_w_mode_warning(tmpdir):
    """Get a deprecation warning when reading from dataset opened in "w" mode"""
    path = tmpdir.join('test.tif')
    profile = DefaultGTiffProfile(count=1, width=300, height=300)

    with rasterio.open(str(path), "w", **profile) as dst:

        dst.write(255 * np.ones((1, 300, 300), dtype='uint8'))

        with pytest.warns(RasterioDeprecationWarning):
            assert (dst.read() == 255).all()

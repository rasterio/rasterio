"""Tests of r+ and w+ modes"""

import numpy as np

import rasterio
from rasterio.profiles import default_gtiff_profile


def test_read_w_mode(tmpdir):
    """A dataset opened in 'w+' mode can be read"""
    path = tmpdir.join('test.tif')
    profile = default_gtiff_profile
    profile.update(count=1, width=300, height=300)

    with rasterio.open(str(path), 'w', **profile) as dst:

        dst.write(255 * np.ones((1, 300, 300), dtype='uint8'))

        assert (dst.read() == 255).all()

        dst.write(3 * np.ones((1, 300, 300), dtype='uint8'))

        assert (dst.read() == 3).all()

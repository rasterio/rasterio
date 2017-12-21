"""Test of boundless reads"""

import numpy

import rasterio
from rasterio.windows import Window


def test_pixel_fidelity(path_rgb_byte_tif):
    """Boundless read doesn't change pixels"""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        rgb = dataset.read()
        rgb_padded = dataset.read(window=Window(-100, -100, dataset.width + 200, dataset.height + 200), boundless=True)

    assert numpy.all(rgb == rgb_padded[:, 100:-100, 100:-100])

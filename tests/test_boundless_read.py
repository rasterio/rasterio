"""Test of boundless reads"""

from hypothesis import given
import hypothesis.strategies as st
import numpy

import rasterio
from rasterio.windows import Window


@given(st.integers(min_value=0, max_value=700))
def test_outer_boundless_pixel_fidelity(size):
    """An outer boundless read doesn't change pixels"""
    path_rgb_byte_tif = 'tests/data/RGB.byte.tif'
    with rasterio.open(path_rgb_byte_tif) as dataset:
        rgb = dataset.read()
        rgb_padded = dataset.read(window=Window(-size, -size, dataset.width + 2 * size, dataset.height + 2 * size), boundless=True)
        assert rgb_padded.shape == (3, dataset.height + 2 * size, dataset.width + 2 * size)
    assert numpy.all(rgb == rgb_padded[:, size:(-size or None), size:(-size or None)])

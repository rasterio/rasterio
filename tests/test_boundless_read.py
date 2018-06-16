"""Test of boundless reads"""

from hypothesis import given
import hypothesis.strategies as st
import numpy

import rasterio
from rasterio.windows import Window

from .conftest import requires_gdal21


@requires_gdal21(reason="Pixel equality tests require float windows and GDAL 2.1")
@given(col_start=st.integers(min_value=-700, max_value=0),
       row_start=st.integers(min_value=-700, max_value=0),
       col_stop=st.integers(min_value=0, max_value=700),
       row_stop=st.integers(min_value=0, max_value=700))
def test_outer_boundless_pixel_fidelity(
        path_rgb_byte_tif, col_start, row_start, col_stop, row_stop):
    """An outer boundless read doesn't change pixels"""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        width = dataset.width + col_stop - col_start
        height = dataset.height + row_stop - row_start
        window = Window(col_start, row_start, width, height)
        rgb_padded = dataset.read(window=window, boundless=True)
        assert rgb_padded.shape == (dataset.count, height, width)
        rgb = dataset.read()
        assert numpy.all(
            rgb == rgb_padded[:, -row_start:height - row_stop,
                              -col_start:width - col_stop])

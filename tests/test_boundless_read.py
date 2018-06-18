"""Test of boundless reads"""

from hypothesis import given
import hypothesis.strategies as st
import numpy
import pytest

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


def test_image(red_green):
    """Read a red image with black background"""
    with rasterio.Env():
        with rasterio.open(str(red_green.join("red.tif"))) as src:
            data = src.read(boundless=True, window=Window(-src.width, -src.height, src.width * 3, src.height * 3))
            image = numpy.moveaxis(data, 0, -1)
            assert image[63, 63, 0] == 0
            assert image[64, 64, 0] == 204


@pytest.mark.xfail(reason="warped vrt doesn't trigger use of overviews yet")
def test_hit_ovr(red_green):
    """Zoomed out read hits the overviews"""
    # GDAL doesn't log overview hits for local files , so we copy the
    # overviews of green.tif over the red overviews and expect to find
    # green pixels below.
    green_ovr = red_green.join("green.tif.ovr")
    green_ovr.rename(red_green.join("red.tif.ovr"))
    assert not green_ovr.exists()

    with rasterio.Env():
        with rasterio.open(str(red_green.join("red.tif"))) as src:
            data = src.read(boundless=True, window=Window(-src.width * 2, -src.height * 2, src.width * 5, src.height * 5))
            image = numpy.moveaxis(data, 0, -1)
            assert image[127, 127, 0] == 0
            assert image[128, 128, 0] == 17
            assert image[128, 128, 1] == 204

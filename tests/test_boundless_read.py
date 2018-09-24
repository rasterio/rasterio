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


def test_hit_ovr(red_green):
    """Zoomed out read hits the overviews"""
    # GDAL doesn't log overview hits for local files , so we copy the
    # overviews of green.tif over the red overviews and expect to find
    # green pixels below.
    green_ovr = red_green.join("green.tif.ovr")
    green_ovr.rename(red_green.join("red.tif.ovr"))
    assert not green_ovr.exists()
    with rasterio.open(str(red_green.join("red.tif.ovr"))) as ovr:
        data = ovr.read()
        assert (data[1] == 204).all()

    with rasterio.Env():
        with rasterio.open(str(red_green.join("red.tif"))) as src:
            data = src.read(out_shape=(3, 32, 32))
            image = numpy.moveaxis(data, 0, -1)
            assert image[0, 0, 0] == 17
            assert image[0, 0, 1] == 204


def test_boundless_mask_not_all_valid():
    """Confirm resolution of issue #1449"""
    with rasterio.open("tests/data/red.tif") as src:
        masked = src.read(1, boundless=True, masked=True, window=Window(-1, -1, 66, 66))
    assert not masked.mask.all()
    assert masked.mask[:, 0].all()
    assert masked.mask[:, -1].all()
    assert masked.mask[0, :].all()
    assert masked.mask[-1, :].all()


def test_boundless_fill_value():
    """Confirm resolution of issue #1471"""
    with rasterio.open("tests/data/red.tif") as src:
        filled = src.read(1, boundless=True, fill_value=5, window=Window(-1, -1, 66, 66))
    assert (filled[:, 0] == 5).all()
    assert (filled[:, -1] == 5).all()
    assert (filled[0, :] == 5).all()
    assert (filled[-1, :] == 5).all()


def test_boundless_fill_value_overview_masks():
    """Confirm a more general resolution to issue #1471"""
    with rasterio.open("tests/data/cogeo.tif") as src:
        data = src.read(1, boundless=True, window=Window(-300, -335, 1000, 1000), fill_value=5, out_shape=(512, 512))
    assert (data[:, 0] == 5).all()


def test_boundless_masked_fill_value_overview_masks():
    """Confirm a more general resolution to issue #1471"""
    with rasterio.open("tests/data/cogeo.tif") as src:
        data = src.read(1, masked=True, boundless=True, window=Window(-300, -335, 1000, 1000), fill_value=5, out_shape=(512, 512))
    assert data.fill_value == 5
    assert data.mask[:, 0].all()

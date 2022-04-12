"""Test of boundless reads"""

from affine import Affine
import shutil
from hypothesis import example, given
import hypothesis.strategies as st
import numpy
from numpy.testing import assert_almost_equal
import pytest

import rasterio
from rasterio.io import MemoryFile
from rasterio.windows import Window

from .conftest import requires_gdal21, gdal_version


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
            rgb
            == rgb_padded[
                :, -row_start : height - row_stop, -col_start : width - col_stop
            ]
        )


@pytest.mark.xfail(reason="The bug reported in gh-2382")
@given(height=st.integers(min_value=500, max_value=20000))
@example(height=9508)
def test_issue2382(height):
    data_array = numpy.arange(height, dtype="f4").reshape((height, 1))

    with MemoryFile() as memfile:
        with memfile.open(
            driver='GTiff',
            count=1,
            height=height,
            width=1,
            dtype=data_array.dtype,
            transform=Affine(1.0, 0.0, 0, 0.0, -1.0, 0),
        ) as dataset:
            dataset.write(data_array[numpy.newaxis, ...])

        with memfile.open(driver='GTiff') as dataset:
            # read first column, rows 0-388
            a = dataset.read(
                1,
                window=Window(col_off=0, row_off=0, width=1, height=388),
                boundless=True,
                fill_value=-9999,
            )[:, 0]
            assert_almost_equal(a, numpy.arange(388))

            b = dataset.read(
                1,
                window=Window(col_off=0, row_off=-12, width=1, height=400),
                boundless=True,
                fill_value=-9999,
            )[:, 0]
            # the expected result is 12 * -9999 and then the same as above
            assert_almost_equal(b, numpy.concatenate([[-9999] * 12, a]))


@pytest.mark.xfail(reason="Likely the bug reported in gh-2382")
@requires_gdal21(reason="Pixel equality tests require float windows and GDAL 2.1")
@given(
    col_start=st.integers(min_value=-700, max_value=0),
    row_start=st.integers(min_value=-700, max_value=0),
    col_stop=st.integers(min_value=0, max_value=700),
    row_stop=st.integers(min_value=0, max_value=700),
)
def test_outer_upper_left_boundless_pixel_fidelity(
    path_rgb_byte_tif, col_start, row_start, col_stop, row_stop
):
    """A partially outer boundless read doesn't change pixels"""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        width = dataset.width - col_stop - col_start
        height = dataset.height - row_stop - row_start
        window = Window(col_start, row_start, width, height)
        rgb_boundless = dataset.read(window=window, boundless=True)
        assert rgb_boundless.shape == (dataset.count, height, width)
        rgb = dataset.read()
        assert numpy.all(
            rgb[:, 0 : height + row_start, 0 : width + col_start]
            == rgb_boundless[:, -row_start:height, -col_start:width]
        )


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
    shutil.move(green_ovr, red_green.join("red.tif.ovr"))
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


@pytest.mark.xfail(reason="fill_value requires GDAL 3.1.4 or equivalent patches")
def test_boundless_fill_value():
    """Confirm resolution of issue #1471"""
    with rasterio.open("tests/data/red.tif") as src:
        filled = src.read(1, boundless=True, fill_value=5, window=Window(-1, -1, 66, 66))
    assert (filled[:, 0] == 5).all()
    assert (filled[:, -1] == 5).all()
    assert (filled[0, :] == 5).all()
    assert (filled[-1, :] == 5).all()


def test_boundless_masked_special():
    """Confirm resolution of special case in issue #1471"""
    with rasterio.open("tests/data/green.tif") as src:
        masked = src.read(2, boundless=True, masked=True, window=Window(-1, -1, 66, 66))
    assert not masked[:, 0].any()
    assert not masked[:, -1].any()
    assert not masked[0, :].any()
    assert not masked[-1, :].any()


def test_boundless_mask_special():
    """Confirm resolution of special case in issue #1471"""
    with rasterio.open("tests/data/green.tif") as src:
        mask = src.read_masks(2, boundless=True, window=Window(-1, -1, 66, 66))
    assert not mask[:, 0].any()
    assert not mask[:, -1].any()
    assert not mask[0, :].any()
    assert not mask[-1, :].any()


@pytest.mark.xfail(reason="fill_value requires GDAL 3.1.4 or equivalent patches")
def test_boundless_fill_value_overview_masks():
    """Confirm a more general resolution to issue #1471"""
    with rasterio.open("tests/data/cogeo.tif") as src:
        data = src.read(1, boundless=True, window=Window(-300, -335, 1000, 1000), fill_value=5, out_shape=(512, 512))
    assert (data[:, 0] == 5).all()


@pytest.mark.xfail(reason="fill_value requires GDAL 3.1.4 or equivalent patches")
def test_boundless_masked_fill_value_overview_masks():
    """Confirm a more general resolution to issue #1471"""
    with rasterio.open("tests/data/cogeo.tif") as src:
        data = src.read(1, masked=True, boundless=True, window=Window(-300, -335, 1000, 1000), fill_value=5, out_shape=(512, 512))
    assert data.fill_value == 5
    assert data.mask[:, 0].all()


def test_boundless_open_options():
    """Open options are taken into account"""
    with rasterio.open("tests/data/cogeo.tif", overview_level=1) as src:
        data1 = src.read(1, boundless=True)
    with rasterio.open("tests/data/cogeo.tif", overview_level=2) as src:
        data2 = src.read(1, boundless=True)
    assert not numpy.array_equal(data1, data2)

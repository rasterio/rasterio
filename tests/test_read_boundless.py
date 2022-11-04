import logging
import sys

import numpy as np
import pytest

import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window


@pytest.fixture(scope='session')
def rgb_array(path_rgb_byte_tif):
    with rasterio.open(path_rgb_byte_tif) as src:
        return src.read()


@pytest.fixture(scope='function')
def rgb_byte_tif_reader(path_rgb_byte_tif):
    return rasterio.open(path_rgb_byte_tif)


def test_read_boundless_false(rgb_byte_tif_reader, rgb_array):
    """Reading natural window with boundless=False works"""
    with rgb_byte_tif_reader as src:
        data = src.read(boundless=False)
        assert data.shape == rgb_array.shape
        assert data.sum() == rgb_array.sum()


def test_read_boundless_natural_extent(rgb_byte_tif_reader, rgb_array):
    """Reading natural window with boundless=True works"""
    with rgb_byte_tif_reader as src:
        data = src.read(boundless=True)
        assert data.shape == rgb_array.shape
        assert data.sum() == rgb_array.sum()


def test_read_boundless_beyond(rgb_byte_tif_reader):
    """Reading entirely outside the dataset returns no data"""
    with rgb_byte_tif_reader as src:
        data = src.read(window=((-200, -100), (-200, -100)), boundless=True)
        assert data.shape == (3, 100, 100)
        assert not data.any()
        assert (data == 0).all()


def test_read_boundless_beyond_fill_value(rgb_byte_tif_reader):
    """Reading entirely outside the dataset returns the fill value"""
    with rgb_byte_tif_reader as src:
        data = src.read(window=Window(-200, -200, 100, 100), boundless=True,
                        fill_value=1)
        assert data.shape == (3, 100, 100)
        assert (data == 1).all()


def test_read_boundless_beyond2(rgb_byte_tif_reader):
    with rgb_byte_tif_reader as src:
        data = src.read(window=((1000, 1100), (1000, 1100)), boundless=True)
        assert data.shape == (3, 100, 100)
        assert not data.any()


def test_read_boundless_overlap(rgb_byte_tif_reader):
    with rgb_byte_tif_reader as src:
        data = src.read(window=((-200, 200), (-200, 200)), boundless=True)
        assert data.shape == (3, 400, 400)
        assert data.any()
        assert data[0, 399, 399] == 13


def test_read_boundless_resample(rgb_byte_tif_reader):
    with rgb_byte_tif_reader as src:
        out = np.zeros((3, 800, 800), dtype=np.uint8)
        data = src.read(
            out=out,
            window=((-200, 200), (-200, 200)),
            masked=True,
            boundless=True)
        assert data.shape == (3, 800, 800)
        assert data.any()
        assert data[0, 798, 798] == 13


def test_read_boundless_masked_no_overlap(rgb_byte_tif_reader):
    with rgb_byte_tif_reader as src:
        data = src.read(
            window=((-200, -100), (-200, -100)), boundless=True, masked=True)
        assert data.shape == (3, 100, 100)
        assert data.mask.all()


def test_read_boundless_masked_overlap(rgb_byte_tif_reader):
    with rgb_byte_tif_reader as src:
        data = src.read(
            window=((-200, 200), (-200, 200)), boundless=True, masked=True)
        assert data.shape == (3, 400, 400)
        assert data.mask.any()
        assert not data.mask.all()
        assert not data.mask[0, 399, 399]
        assert data.mask[0, 0, 0]


def test_read_boundless_zero_stop(rgb_byte_tif_reader):
    with rgb_byte_tif_reader as src:
        data = src.read(
            window=Window(-200, -200, 200, 200), boundless=True, masked=True)
        assert data.shape == (3, 200, 200)
        assert data.mask.all()


def test_read_boundless_masks_zero_stop(rgb_byte_tif_reader):
    with rgb_byte_tif_reader as src:
        data = src.read_masks(window=((-200, 0), (-200, 0)), boundless=True)
        assert data.shape == (3, 200, 200)
        assert data.min() == data.max() == src.nodata


def test_read_boundless_noshift():
    with rasterio.open('tests/data/rgb4.tif') as src:
        # the read offsets should be determined by start col/row alone
        # when col stop exceeds image width
        c1 = src.read(boundless=True,
                      window=((100, 101), (-1, src.shape[1])))[0, 0, 0:9]
        c2 = src.read(boundless=True,
                      window=((100, 101), (-1, src.shape[1] + 1)))[0, 0, 0:9]
        assert np.array_equal(c1, c2)

        # when row stop exceeds image height
        r1 = src.read(boundless=True,
                      window=((-1, src.shape[0]), (100, 101)))[0, 0, 0:9]
        r2 = src.read(boundless=True,
                      window=((-1, src.shape[0] + 1), (100, 101)))[0, 0, 0:9]
        assert np.array_equal(r1, r2)


def test_msk_read_masks(path_rgb_msk_byte_tif):
    """Boundless read of a source with .msk succeeds

    Success in this case means that we read a mask that has
    invalid pixels around the edges, is appropriately padded,
    and has valid data pixels in the center.
    """
    with rasterio.open(path_rgb_msk_byte_tif) as src:
        msk = src.read_masks(1, boundless=True, window=Window(-200, -200, 1000, 1000), out_shape=((600, 600)))
        # Invalid region is padded correctly.
        assert not msk[0:195,0:195].any()
        # We have the valid data expected in the center.
        assert msk.mean() > 90


@pytest.mark.xfail(reason="GDAL 3.1 skips overviews because of background layer")
def test_issue1982(capfd):
    """See a curl request for overview file"""
    # Note: the underlying GDAL issue has been fixed after 3.1.3. The
    # rasterio 1.1.6 wheels published to PyPI will include a patched
    # 2.4.4 that also fixes the issue.  This test will XPASS in the
    # rasterio-wheels tests.
    with rasterio.Env(CPL_CURL_VERBOSE=True), rasterio.open(
        "https://raw.githubusercontent.com/mapbox/rasterio/main/tests/data/green.tif"
    ) as src:
        image = src.read(
            indexes=[1, 2, 3],
            window=Window(col_off=-32, row_off=-32, width=64, height=64),
            resampling=Resampling.cubic,
            boundless=True,
            out_shape=(3, 10, 10),
            fill_value=42,
        )
    captured = capfd.readouterr()
    assert "green.tif" in captured.err
    assert "green.tif.ovr" in captured.err
    assert (42 == image[:, :3, :]).all()
    assert (42 == image[:, :, :3]).all()

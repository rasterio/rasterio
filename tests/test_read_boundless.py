import logging
import sys

import numpy as np
import pytest

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


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
        data = src.read(window=((-200, -100), (-200, -100)), boundless=True,
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
        assert data[0,399,399] == 13


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
        assert data[0,798,798] == 13


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
        assert data.mask[0,399,399] == False
        assert data.mask[0,0,0] == True


def test_read_boundless_zero_stop(rgb_byte_tif_reader):
    with rgb_byte_tif_reader as src:
        data = src.read(
            window=((-200, 0), (-200, 0)), boundless=True, masked=True)
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


def test_np_warning(recwarn, rgb_byte_tif_reader):
    """Ensure no deprecation warnings
    On np 1.11 and previous versions of rasterio you might see:
        VisibleDeprecationWarning: using a non-integer number
        instead of an integer will result in an error in the future
    """
    import warnings
    warnings.simplefilter('always')
    with rgb_byte_tif_reader as src:
        window = ((-10, 100), (-10, 100))
        src.read(1, window=window, boundless=True)
    assert len(recwarn) == 0

import logging
import sys

import numpy

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_read_boundless_natural_extent():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read(boundless=True)
        assert data.shape == src.shape
        assert abs(data[0].mean() - src.read(1).mean()) < 0.0001
        assert data.any()


def test_read_boundless_beyond():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read(window=((-200, -100), (-200, -100)), boundless=True)
        assert data.shape == (3, 100, 100)
        assert not data.any()


def test_read_boundless_beyond2():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read(window=((1000, 1100), (1000, 1100)), boundless=True)
        assert data.shape == (3, 100, 100)
        assert not data.any()


def test_read_boundless_overlap():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read(window=((-200, 200), (-200, 200)), boundless=True)
        assert data.shape == (3, 400, 400)
        assert data.any()
        assert data[0,399,399] == 13


def test_read_boundless_resample():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        out = numpy.zeros((3, 800, 800), dtype=numpy.uint8)
        data = src.read(
                out=out,
                window=((-200, 200), (-200, 200)),
                masked=True,
                boundless=True)
        assert data.shape == (3, 800, 800)
        assert data.any()
        assert data[0,798,798] == 13


def test_read_boundless_masked_no_overlap():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read(
            window=((-200, -100), (-200, -100)), boundless=True, masked=True)
        assert data.shape == (3, 100, 100)
        assert data.mask.all()


def test_read_boundless_masked_overlap():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read(
            window=((-200, 200), (-200, 200)), boundless=True, masked=True)
        assert data.shape == (3, 400, 400)
        assert data.mask.any()
        assert not data.mask.all()
        assert data.mask[0,399,399] == False
        assert data.mask[0,0,0] == True


def test_read_boundless_zero_stop():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read(
            window=((-200, 0), (-200, 0)), boundless=True, masked=True)
        assert data.shape == (3, 200, 200)
        assert data.mask.all()


def test_read_boundless_masks_zero_stop():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read_masks(window=((-200, 0), (-200, 0)), boundless=True)
        assert data.shape == (3, 200, 200)
        assert data.min() == data.max() == src.nodata

def test_read_boundless_noshift():
    with rasterio.open('tests/data/rgb4.tif') as src:
        # the read offsets should be determined by start col/row alone
        # when col stop exceeds image width
        c1 = src.read(boundless=True,
                      window=((100, 101), (-1, src.shape[2])))[0, 0, 0:9]
        c2 = src.read(boundless=True,
                      window=((100, 101), (-1, src.shape[2] + 1)))[0, 0, 0:9]
        assert numpy.array_equal(c1, c2)

        # when row stop exceeds image height
        r1 = src.read(boundless=True,
                      window=((-1, src.shape[1]), (100, 101)))[0, 0, 0:9]
        r2 = src.read(boundless=True,
                      window=((-1, src.shape[1] + 1), (100, 101)))[0, 0, 0:9]
        assert numpy.array_equal(r1, r2)

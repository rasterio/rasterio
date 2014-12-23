import logging
import sys

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_read_boundless_natural_extent():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read(boundless=True)
        assert data.shape == (3, src.height, src.width)
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


def test_read_boundless():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read(window=((-200, 200), (-200, 200)), boundless=True)
        assert data.shape == (3, 400, 400)
        assert data.any()
        assert data[0,399,399] == 13

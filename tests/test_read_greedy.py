import logging
import sys

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_read_greedy_natural_extent():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read(greedy=True)
        assert data.shape == (3, src.height, src.width)
        assert data.any()

def test_read_greedy_beyond():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read(window=((-200, -100), (-200, -100)), greedy=True)
        assert data.shape == (3, 100, 100)
        assert not data.any()


def test_read_greedy_beyond2():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read(window=((1000, 1100), (1000, 1100)), greedy=True)
        assert data.shape == (3, 100, 100)
        assert not data.any()


def test_read_greedy():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        data = src.read(window=((-200, 200), (-200, 200)), greedy=True)
        assert data.shape == (3, 400, 400)
        assert data.any()
        assert data[0,399,399] == 13

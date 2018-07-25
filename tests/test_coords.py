import rasterio
import numpy as np

def test_bounds():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.bounds == (101985.0, 2611485.0, 339315.0, 2826915.0)

def test_ul():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.xy(0, 0, offset='ul') == (101985.0, 2826915.0)
        assert src.xy(1, 0, offset='ul') == (101985.0, 2826614.95821727)
        assert src.xy(src.height, src.width, offset='ul') == (339315.0, 2611485.0)

def test_res():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert tuple(round(v, 6) for v in src.res) == (300.037927, 300.041783)

def test_rotated_bounds():
    with rasterio.open('tests/data/rotated.tif') as src:
        assert src.res == (20.0, 10.0)
        np.testing.assert_almost_equal(
            src.bounds,
            (100.0, 70.0961894323342, 348.20508075688775, 300.0))

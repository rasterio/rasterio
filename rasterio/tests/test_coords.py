
import rasterio

def test_bounds():
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        assert src.bounds == (101985.0, 2611485.0, 339315.0, 2826915.0)

def test_ul():
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        assert src.ul(0, 0) == (101985.0, 2826915.0)
        assert src.ul(1, 0) == (101985.0, 2826614.95821727)
        assert src.ul(src.height, src.width) == (339315.0, 2611485.0)
        assert tuple(
            round(v, 6) for v in src.ul(~0, ~0)
            ) == (339014.962073, 2611785.041783)

def test_res():
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        assert tuple(round(v, 6) for v in src.res) == (300.037927, 300.041783)

def test_index():
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        assert src.index(101985.0, 2826915.0) == (0, 0)
        assert src.index(101985.0+400.0, 2826915.0) == (0, 1)
        assert src.index(101985.0+400.0, 2826915.0+700.0) == (2, 1)



import rasterio

def test_index():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        assert src.index(left, top) == (0, 0)
        assert src.index(right, top) == (0, src.width)
        assert src.index(right, bottom) == (src.height, src.width)
        assert src.index(left, bottom) == (src.height, 0)

def test_full_window():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.window(*src.bounds) == tuple(zip((0, 0), src.shape))

def test_window_exception():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        left -= 1000.0
        try:
            _ = src.window(left, bottom, right, top)
            assert False
        except ValueError:
            assert True


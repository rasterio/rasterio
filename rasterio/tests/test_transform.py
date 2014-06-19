
import rasterio

def test_window():
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        assert src.window(left, bottom, right, top) == ((0, src.height),
                                                        (0, src.width))
        assert src.window(left, top-src.res[1], left+src.res[0], top) == (
            (0, 1), (0, 1))


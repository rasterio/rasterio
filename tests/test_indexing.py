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
        left, bottom, right, top = src.bounds
        assert src.window(left, bottom, right, top) == tuple(zip((0, 0), src.shape))


def test_window_no_exception():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        left -= 1000.0
        assert src.window(left, bottom, right, top, boundless=True) == (
                (0, src.height), (-4, src.width))


def test_index():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.index(101985.0, 2826915.0) == (0, 0)
        assert src.index(101985.0+400.0, 2826915.0) == (0, 1)
        assert src.index(101985.0+400.0, 2826915.0-700.0) == (2, 1)


def test_window():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        dx, dy = src.res
        eps = 1.0e-8
        assert src.window(
            left+eps, bottom+eps, right-eps, top-eps) == ((0, src.height),
                                                          (0, src.width))
        assert src.index(left+400, top-400) == (1, 1)
        assert src.index(left+dx+eps, top-dy-eps) == (1, 1)
        assert src.window(left, top-400, left+400, top) == ((0, 1), (0, 1))
        assert src.window(left, top-2*dy-eps, left+2*dx+eps, top) == ((0, 2), (0, 2))


def test_window_bounds_roundtrip():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert ((100, 200), (100, 200)) == src.window(
            *src.window_bounds(((100, 200), (100, 200))))

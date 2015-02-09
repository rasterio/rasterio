import rasterio

def test_window():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        assert src.window(left, bottom, right, top) == ((0, src.height),
                                                        (0, src.width))
        assert src.window(left, top-src.res[1], left+src.res[0], top) == (
            (0, 1), (0, 1))


def test_window_transform():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.window_transform(((0, src.height), (0, src.width))) == src.affine
        assert src.window_transform(((0, None), (0, None))) == src.affine
        assert src.window_transform(((None, None), (None, None))) == src.affine
        assert src.window_transform(((None, src.height), (None, src.width))) == src.affine
        assert src.window_transform(((1, None), (1, None))).c == src.bounds.left + src.res[0]
        assert src.window_transform(((-1, None), (-1, None))).c == src.bounds.left - src.res[0]

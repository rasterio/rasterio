import rasterio
from rasterio import transform


def test_window():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        assert src.window(left, bottom, right, top) == ((0, src.height),
                                                        (0, src.width))
        assert src.window(left, top-src.res[1], left+src.res[0], top) == (
            (0, 1), (0, 1))


def test_window_transform():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.window_transform(((0, None), (0, None))) == src.affine
        assert src.window_transform(((None, None), (None, None))) == src.affine
        assert src.window_transform(
                ((1, None), (1, None))).c == src.bounds.left + src.res[0]
        assert src.window_transform(
                ((1, None), (1, None))).f == src.bounds.top - src.res[1]
        assert src.window_transform(
                ((-1, None), (-1, None))).c == src.bounds.left - src.res[0]
        assert src.window_transform(
                ((-1, None), (-1, None))).f == src.bounds.top + src.res[1]


def test_from_origin():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        w, n = src.ul(0, 0)
        xs, ys = src.res
        tr = transform.from_origin(w, n, xs, ys)
        assert [round(v, 7) for v in tr] == [round(v, 7) for v in src.affine]


def test_from_bounds():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        w, s, e, n = src.bounds
        tr = transform.from_bounds(w, s, e, n, src.width, src.height)
        assert [round(v, 7) for v in tr] == [round(v, 7) for v in src.affine]

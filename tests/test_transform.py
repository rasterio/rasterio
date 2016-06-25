from affine import Affine
import pytest
import rasterio
from rasterio import transform


def test_window_transform():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.window_transform(((0, None), (0, None))) == src.transform
        assert src.window_transform(((None, None), (None, None))) == src.transform
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
        assert [round(v, 7) for v in tr] == [round(v, 7) for v in src.transform]


def test_from_bounds():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        w, s, e, n = src.bounds
        tr = transform.from_bounds(w, s, e, n, src.width, src.height)
        assert [round(v, 7) for v in tr] == [round(v, 7) for v in src.transform]


def test_array_bounds():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        w, s, e, n = src.bounds
        height = src.height
        width = src.width
        tr = transform.from_bounds(w, s, e, n, src.width, src.height)
    assert (w, s, e, n) == transform.array_bounds(height, width, tr)


def test_window_bounds():
    with rasterio.open('tests/data/RGB.byte.tif') as src:

        rows = src.height
        cols = src.width

        # Test window for entire DS and each window in the DS
        assert src.window_bounds(((0, rows), (0, cols))) == src.bounds
        for _, window in src.block_windows():
            ds_x_min, ds_y_min, ds_x_max, ds_y_max = src.bounds
            w_x_min, w_y_min, w_x_max, w_y_max = src.window_bounds(window)
            assert ds_x_min <= w_x_min <= w_x_max <= ds_x_max
            assert ds_y_min <= w_y_min <= w_y_max <= ds_y_max

        # Test a small window in each corner, both in and slightly out of bounds
        p = 10
        for window in (
                # In bounds (UL, UR, LL, LR)
                ((0, p), (0, p)),
                ((0, p), (cols - p, p)),
                ((rows - p, p), (0, p)),
                ((rows - p, p), (cols - p, p)),

                # Out of bounds (UL, UR, LL, LR)
                ((-1, p), (-1, p)),
                ((-1, p), (cols - p, p + 1)),
                ((rows - p, p + 1), (-1, p)),
                ((rows - p, p + 1), (cols - p, p + 1))):

            # Alternate formula

            ((row_min, row_max), (col_min, col_max)) = window
            win_aff = src.window_transform(window)

            x_min, y_max = win_aff.c, win_aff.f
            x_max = win_aff.c + (src.res[0] * (col_max - col_min))
            y_min = win_aff.f - (src.res[1] * (row_max - row_min))

            expected = (x_min, y_min, x_max, y_max)
            actual = src.window_bounds(window)

            for e, a in zip(expected, actual):
                assert round(e, 7) == round(a, 7)


def test_affine_roundtrip(tmpdir):
    output = str(tmpdir.join('test.tif'))
    out_affine = Affine(2, 0, 0, 0, -2, 0)

    with rasterio.open(
        output, 'w',
        driver='GTiff',
        count=1,
        dtype=rasterio.uint8,
        width=1,
        height=1,
        transform=out_affine
    ) as out:
        assert out.transform == out_affine

    with rasterio.open(output) as out:
        assert out.transform == out_affine


def test_affine_identity(tmpdir):
    """
    Setting a transform with absolute values equivalent to Affine.identity()
    should result in a warning (not captured here) and read with
    affine that matches Affine.identity().
    """

    output = str(tmpdir.join('test.tif'))
    out_affine = Affine(1, 0, 0, 0, -1, 0)

    with rasterio.open(
        output, 'w',
        driver='GTiff',
        count=1,
        dtype=rasterio.uint8,
        width=1,
        height=1,
        transform=out_affine
    ) as out:
        assert out.transform == out_affine

    with rasterio.open(output) as out:
        assert out.transform == Affine.identity()


def test_from_bounds_two():
    width = 80
    height = 80
    left = -120
    top = 70
    right = -80.5
    bottom = 30.5
    tr = transform.from_bounds(left, bottom, right, top, width, height)
    # pixelwidth, rotation, ULX, rotation, pixelheight, ULY
    expected = Affine(0.49375, 0.0, -120.0, 0.0, -0.49375, 70.0)
    assert [round(v, 7) for v in tr] == [round(v, 7) for v in expected]

    # Round right and bottom
    right = -80
    bottom = 30
    tr = transform.from_bounds(left, bottom, right, top, width, height)
    # pixelwidth, rotation, ULX, rotation, pixelheight, ULY
    expected = Affine(0.5, 0.0, -120.0, 0.0, -0.5, 70.0)
    assert [round(v, 7) for v in tr] == [round(v, 7) for v in expected]


def test_guard_transform_gdal_TypeError(path_rgb_byte_tif):
    """As part of the 1.0 migration, guard_transform() should raise a TypeError
    if a GDAL geotransform is encountered"""

    with rasterio.open(path_rgb_byte_tif) as src:
        aff = src.transform

    with pytest.raises(TypeError):
        transform.guard_transform(aff.to_gdal())


def test_tastes_like_gdal_identity():
    aff = Affine.identity()
    assert not transform.tastes_like_gdal(aff)
    assert transform.tastes_like_gdal(aff.to_gdal())

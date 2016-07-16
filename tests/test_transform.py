import warnings

from affine import Affine
from hypothesis import given, strategies as st
import math
import pytest

import rasterio
from rasterio import transform
from rasterio.transform import xy, rowcol


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


def test_xy():
    aff = Affine(300.0379266750948, 0.0, 101985.0,
                 0.0, -300.041782729805, 2826915.0)
    ul_x, ul_y = aff * (0, 0)
    xoff = aff.a
    yoff = aff.e
    assert xy(aff, 0, 0, offset='ul') == (ul_x, ul_y)
    assert xy(aff, 0, 0, offset='ur') == (ul_x + xoff, ul_y)
    assert xy(aff, 0, 0, offset='ll') == (ul_x, ul_y + yoff)
    expected = (ul_x + xoff, ul_y + yoff)
    assert xy(aff, 0, 0, offset='lr') == expected
    expected = (ul_x + xoff / 2, ul_y + yoff / 2)
    assert xy(aff, 0, 0, offset='center') == expected
    assert xy(aff, 0, 0, offset='lr') == \
        xy(aff, 0, 1, offset='ll') == \
        xy(aff, 1, 1, offset='ul') == \
        xy(aff, 1, 0, offset='ur')


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


def test_rowcol():
    with rasterio.open("tests/data/RGB.byte.tif", 'r') as src:
        aff = src.transform
        left, bottom, right, top = src.bounds
        assert rowcol(aff, left, top) == (0, 0)
        assert rowcol(aff, right, top) == (0, src.width)
        assert rowcol(aff, right, bottom) == (src.height, src.width)
        assert rowcol(aff, left, bottom) == (src.height, 0)


@given(precision=st.integers())
def test_precision_warning(precision, recwarn):
    warnings.simplefilter('always')
    row, col = rowcol(Affine.identity(), 0, 0, precision=precision)
    assert len(recwarn) == 1
    assert recwarn.pop(DeprecationWarning)


@given(row=st.integers(min_value=0, max_value=100),
       col=st.integers(min_value=0, max_value=100),
       pxsz=st.floats(min_value=1.0, max_value=1000.0),
       xoff=st.floats(min_value=0.0, max_value=1000000.0),
       yoff=st.floats(min_value=0.0, max_value=1000000.0))
def test_xy_rowcol_inverse(row, col, pxsz, xoff, yoff):
    """Roundtrip of xy and rowcol for range of inputs"""
    aff = Affine(pxsz, 0.0, xoff, 0.0, -pxsz, yoff)
    assert (row, col) == rowcol(aff, *xy(aff, row, col))


@given(row=st.integers(min_value=0, max_value=100),
       col=st.integers(min_value=0, max_value=100),
       pxsz=st.floats(min_value=1.0, max_value=1000.0),
       xoff=st.floats(min_value=0.0, max_value=1000000.0),
       yoff=st.floats(min_value=0.0, max_value=1000000.0))
def test_xy_rowcol_inverse_ceil(row, col, pxsz, xoff, yoff):
    """Roundtrip of xy and rowcol for range of inputs"""
    aff = Affine(pxsz, 0.0, xoff, 0.0, -pxsz, yoff)
    assert (row + 1, col + 1) == rowcol(aff, *xy(aff, row, col), op=math.ceil)

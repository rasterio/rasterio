from affine import Affine
import pytest
import rasterio
import numpy as np
from collections.abc import Iterable
from rasterio import transform
from rasterio.env import GDALVersion
from rasterio.errors import TransformError
from rasterio.transform import xy, rowcol
from rasterio.windows import Window


gdal_version = GDALVersion.runtime()


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
        w, n = src.xy(0, 0, offset='ul')
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


@pytest.mark.skipif(
    gdal_version.at_least('2.3'),
    reason="Test only applicable to GDAL < 2.3")
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
    # TODO: use pytest's parametrize to make separate tests.
    aff = Affine(300.0379266750948, 0.0, 101985.0,
                 0.0, -300.041782729805, 2826915.0)
    ul_x, ul_y = aff * (0, 0)
    xoff = aff.a
    yoff = aff.e
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

    # Check list inputs.
    assert xy(aff, [0], [0], offset='ul') == ([ul_x], [ul_y])


def test_bogus_offset():
    with pytest.raises(TransformError):
        xy(None, 1, 0, offset='bogus')


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
        assert rowcol(aff, 101985.0, 2826915.0) == (0, 0)

        # Check list inputs.
        assert rowcol(aff, [101985.0 + 400.0], [2826915.0]) == ([0], [1])


def test_xy_rowcol_inverse():
    # TODO this is an ideal candiate for
    # property-based testing with hypothesis
    aff = Affine.identity()
    rows_cols = ([0, 0, 10, 10],
                 [0, 10, 0, 10])
    assert rows_cols == rowcol(aff, *xy(aff, *rows_cols))


def test_from_gcps():
    with rasterio.open("tests/data/white-gemini-iv.vrt", 'r') as src:
        aff = transform.from_gcps(src.gcps[0])
        assert not aff == src.transform
        assert len(aff) == 9
        assert not transform.tastes_like_gdal(aff)

def test_xy_np_primitive():
    aff = Affine.identity()
    assert (1.5, 1.5) == xy(aff, np.int64(1), np.int64(1))

def test_rowcol_np_primitive():
    aff = Affine.identity()
    assert (1, 1) == rowcol(aff, np.int64(1), np.int64(1))

def test_wrap_noniterable():
    j = 1
    it = transform.wrap_noniterable(j)
    assert isinstance(it, Iterable)
    assert it == [1]
    
    j = []
    assert transform.wrap_noniterable(j) is j
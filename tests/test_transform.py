"""Tests of the transform module."""

from array import array
import logging

from affine import Affine
import pytest

import numpy

import rasterio
from rasterio import transform
from rasterio.transform import (
    get_transformer,
    xy, 
    rowcol,
    AffineTransformer,
    GCPTransformer,
    RPCTransformer
)
from rasterio.errors import TransformError
from rasterio.windows import Window
from rasterio.control import GroundControlPoint


def gcps():
    return [
        GroundControlPoint(row=11521.5, col=0.5, x=-123.6185142817931, y=48.99561141948625, z=89.13533782958984, id='217', info=''), 
        GroundControlPoint(row=11521.5, col=7448.5, x=-122.8802747777599, y=48.91210259315549, z=89.13533782958984, id='234', info=''), 
        GroundControlPoint(row=0.5, col=0.5, x=-123.4809665720148, y=49.52809729106944, z=89.13533782958984, id='1', info=''), 
        GroundControlPoint(row=0.5, col=7448.5, x=-122.7345733674704, y=49.44455878004666, z=89.13533782958984, id='18', info='')
    ]


def rpcs():
    with rasterio.open('tests/data/RGB.byte.rpc.vrt') as src:
        return src.rpcs

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


@pytest.mark.parametrize("aff", [Affine.identity()])
@pytest.mark.parametrize(
    "offset, exp_xy",
    [
        ("ur", (1.0, 0.0)),
        ("lr", (1.0, 1.0)),
        ("ll", (0.0, 1.0)),
        ("ul", (0.0, 0.0)),
        ("center", (0.5, 0.5)),
    ],
)
def test_xy_offset(offset, exp_xy, aff):
    """Check offset keyword arg."""
    assert xy(aff, 0, 0, offset=offset) == exp_xy

@pytest.mark.parametrize(
    'dataset,transform_attr,coords,expected',
    [
        (
            'tests/data/RGB.byte.gcp.vrt',
            'gcps',
            [(0, 718), (0, 0), (791, 0), (791, 718), (0, 718)],
            [(-123.40736757459366, 49.52003804469494), (-123.478928146875, 49.5280898698975), (-123.4886516975216, 49.491531881517595), (-123.41709112524026, 49.48348005631504), (-123.40736757459366, 49.52003804469494)]
        ),
        (
            'tests/data/RGB.byte.rpc.vrt',
            'rpcs',
            [(0, 718), (0, 0), (791, 0), (791, 718), (0, 718)],
            [(-123.40939935400114, 49.52030956245316), (-123.47959047080701, 49.52794990575094), (-123.48908104001859, 49.49139437049529), (-123.41894318723928, 49.48375395209516), (-123.40939935400114, 49.52030956245316)]
        )
    ]
)
def test_xy_gcps_rpcs(dataset, transform_attr, coords, expected):
    with rasterio.open(dataset, 'r') as src:
        transform = getattr(src, transform_attr)
        if transform_attr == 'gcps':
            transform = transform[0]
        for coord, truth in zip(coords, expected):
            assert xy(transform, *coord) == pytest.approx(truth)
        # check offset behaviour
        assert xy(transform, 0, 0, offset='lr') == \
               xy(transform, 0, 1, offset='ll') == \
               xy(transform, 1, 1, offset='ul') == \
               xy(transform, 1, 0, offset='ur')


def test_bogus_offset():
    with pytest.raises(TransformError):
        xy(Affine.identity(), 1, 0, offset='bogus')


@pytest.mark.parametrize("aff", [Affine.identity()])
@pytest.mark.parametrize(
    "rows, cols, exp_xy",
    [
        (0, 0, (0.5, 0.5)),
        (0.0, 0.0, (0.5, 0.5)),
        (numpy.int32(0), numpy.int32(0), (0.5, 0.5)),
        (numpy.float32(0), numpy.float32(0), (0.5, 0.5)),
        ([0], [0], ([0.5], [0.5])),
        (array("d", [0.0]), array("d", [0.0]), ([0.5], [0.5])),
        ([numpy.int32(0)], [numpy.int32(0)], ([0.5], [0.5])),
        (numpy.array([0.0]), numpy.array([0.0]), ([0.5], [0.5])),
    ],
)
def test_xy_input(rows, cols, exp_xy, aff):
    """Handle single and iterable inputs of different numerical types."""
    assert xy(aff, rows, cols) == exp_xy


@pytest.mark.parametrize("aff", [Affine.identity()])
@pytest.mark.parametrize("rows, cols", [([0, 1, 2], [0, 1]), ("0", "0")])
def test_invalid_xy_input(rows, cols, aff):
    """Raise on invalid input."""
    with pytest.raises(TransformError):
        xy(aff, rows, cols)


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


@pytest.mark.parametrize(
    "xs, ys, exp_rowcol",
    [
        ([101985.0 + 400.0], [2826915.0], ([0], [1])),
        (array("d", [101985.0 + 400.0]), array("d", [2826915.0]), ([0], [1])),
        (numpy.array([101985.0 + 400.0]), numpy.array([2826915.0]), ([0], [1])),
    ],
)
def test_rowcol_input(xs, ys, exp_rowcol):
    """Handle single and iterable inputs of different numerical types."""
    with rasterio.open("tests/data/RGB.byte.tif", "r") as src:
        aff = src.transform

    assert rowcol(aff, xs, ys) == exp_rowcol


@pytest.mark.parametrize(
    'dataset,transform_attr,coords,expected',
    [
        (
            'tests/data/RGB.byte.gcp.vrt',
            'gcps',
            [(-123.40736757459366, 49.52003804469494), (-123.478928146875, 49.5280898698975), (-123.4886516975216, 49.491531881517595), (-123.41709112524026, 49.48348005631504), (-123.40736757459366, 49.52003804469494)], 
            [(0, 718), (0, 0), (791, 0), (791, 718), (0, 718)]
        ),
        (
            'tests/data/RGB.byte.rpc.vrt',
            'rpcs',
            [(-123.40939935400114, 49.52030956245316), (-123.47959047080701, 49.52794990575094), (-123.48908104001859, 49.49139437049529), (-123.41894318723928, 49.48375395209516), (-123.40939935400114, 49.52030956245316)],
            [(0, 718), (0, 0), (791, 0), (791, 718), (0, 718)]
        )
    ]
)
def test_rowcol_gcps_rpcs(dataset, transform_attr, coords, expected):
    with rasterio.open(dataset, 'r') as src:
        transform = getattr(src, transform_attr)
        if transform_attr == 'gcps':
            transform = transform[0]
        for coord, truth in zip(coords, expected):
            assert rowcol(transform, *coord) == truth


@pytest.mark.parametrize(
    'transform',
    [
        Affine.identity(),
        gcps(),
        rpcs()
    ]
)
def test_xy_rowcol_inverse(transform):
    # TODO this is an ideal candiate for
    # property-based testing with hypothesis
    rows_cols = ([0, 0, 10, 10],
                 [0, 10, 0, 10])
    assert rows_cols == rowcol(transform, *xy(transform, *rows_cols))


@pytest.mark.parametrize("aff", [Affine.identity()])
@pytest.mark.parametrize("xs, ys", [([0, 1, 2], [0, 1]), ("0", "0")])
def test_invalid_rowcol_input(xs, ys, aff):
    """Raise on invalid input."""
    with pytest.raises(TransformError):
        rowcol(aff, xs, ys)


def test_from_gcps():
    with rasterio.open("tests/data/white-gemini-iv.vrt", 'r') as src:
        aff = transform.from_gcps(src.gcps[0])
        assert not aff == src.transform
        assert len(aff) == 9
        assert not transform.tastes_like_gdal(aff)

@pytest.mark.parametrize(
    'transformer_cls,transform', 
    [
        (GCPTransformer,gcps()), 
        (RPCTransformer,rpcs())
    ]
)
def test_transformer_open_closed(transformer_cls, transform):
    # open or closed does not matter for pure Python AffineTransformer
    with transformer_cls(transform) as transformer:
        assert not transformer.closed 
    assert transformer.closed
    with pytest.raises(ValueError):
        transformer.xy(0, 0)

@pytest.mark.parametrize(
    'coords,expected',
    [
        ((0, 1), (1, 0)),
        (([0],[1]), ([1], [0])),
        ((0,[1]), ([1], [0])),
        (([0], 1), ([1], [0])),
        (([0, 1], [2, 3]), ([2, 3],[0, 1])),
        ((0, [1, 2]), ([1, 2], [0, 0])),
        (([0, 1], 2), ([2, 2], [0, 1])),
        (([0], [1, 2]), ([1, 2], [0, 0])),
        (([0, 1], [2]), ([2, 2], [0, 1])),
    ]
)
def test_ensure_arr_input(coords, expected):
    transformer = transform.AffineTransformer(Affine.identity())
    assert transformer.xy(*coords, offset='ul') == expected

def test_ensure_arr_input_same_shape():
    transformer = transform.AffineTransformer(Affine.identity())
    with pytest.raises(TransformError):
        transformer.xy([0, 1, 2], [0, 1])


def test_ensure_arr_input_with_zs():
    assert AffineTransformer._ensure_arr_input(0, 1) == AffineTransformer._ensure_arr_input(0, 1, zs=0)
    assert AffineTransformer._ensure_arr_input(0, [1, 2], zs=3) == ([0, 0], [1, 2], [3, 3])
    assert AffineTransformer._ensure_arr_input([0, 1], 2, zs=3) == ([0, 1], [2, 2], [3, 3])
    assert AffineTransformer._ensure_arr_input(0, 1, zs=[2, 3]) == ([0, 0], [1, 1], [2, 3])
    with pytest.raises(TransformError):
        AffineTransformer._ensure_arr_input(0, [1, 2], zs=[3, 4, 5])


@pytest.mark.parametrize(
    'transformer_cls,transform',
    [
        (AffineTransformer, Affine.identity()),
        (GCPTransformer, gcps()),
        (RPCTransformer, rpcs())
    ]
)
def test_get_transformer(transformer_cls, transform):
    assert isinstance(get_transformer(transform)(), transformer_cls)


def test_rpctransformer_options(caplog):
    with caplog.at_level(logging.DEBUG):
        with RPCTransformer(rpcs(), rpc_max_iterations=1, dummy_option='yes') as transformer:
            assert "RPC_MAX_ITERATIONS" in caplog.text
            assert "DUMMY_OPTION" in caplog.text

@pytest.mark.parametrize(
    'dataset,transform_method,expected',
    [
        ('tests/data/RGB.byte.tif', rasterio.enums.TransformMethod.affine, (102135.01896333754,  2826764.979108635)),
        ('tests/data/RGB.byte.gcp.vrt', rasterio.enums.TransformMethod.gcps, (-123.478928146875, 49.5280898698975)),
        ('tests/data/RGB.byte.rpc.vrt', rasterio.enums.TransformMethod.rpcs, (-123.47959047080701, 49.52794990575094))
    ]
)
def test_dataset_mixins(dataset, transform_method, expected):
    with rasterio.open(dataset) as src:
        assert src.xy(0, 0, transform_method=transform_method) == pytest.approx(expected)
        assert src.index(*expected, transform_method=transform_method) == (0, 0)

def test_2421_rpc_height_ignored():
    transform_method = rasterio.enums.TransformMethod.rpcs
    with rasterio.open("tests/data/RGB.byte.rpc.vrt") as src:
        x1, y1 = src.xy(0, 0, z=0, transform_method=transform_method)
        x2, y2 = src.xy(0, 0, z=2000, transform_method=transform_method)
        assert abs(x2 - x1) > 0
        assert abs(y2 - y1) > 0

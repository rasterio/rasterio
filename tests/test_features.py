from copy import deepcopy
import math
from unittest import mock

from affine import Affine
import numpy as np
import pytest
import shapely.geometry

import rasterio
from rasterio.enums import MergeAlg
from rasterio.errors import WindowError, ShapeSkipWarning
from rasterio.features import (
    bounds, geometry_mask, geometry_window, is_valid_geom, rasterize, sieve,
    shapes)

from .conftest import MockGeoInterface, gdal_version, requires_gdal_lt_35


DEFAULT_SHAPE = (10, 10)


def test_bounds_point():
    g = {'type': 'Point', 'coordinates': [10, 10]}
    assert bounds(g) == (10, 10, 10, 10)
    assert bounds(MockGeoInterface(g)) == (10, 10, 10, 10)


def test_bounds_line():
    g = {'type': 'LineString', 'coordinates': [[0, 0], [10, 10]]}
    assert bounds(g) == (0, 0, 10, 10)
    assert bounds(MockGeoInterface(g)) == (0, 0, 10, 10)


def test_bounds_ring():
    g = {'type': 'LinearRing', 'coordinates': [[0, 0], [10, 10], [10, 0]]}
    assert bounds(g) == (0, 0, 10, 10)
    assert bounds(MockGeoInterface(g)) == (0, 0, 10, 10)


def test_bounds_polygon():
    g = {'type': 'Polygon', 'coordinates': [[[0, 0], [10, 10], [10, 0]]]}
    assert bounds(g) == (0, 0, 10, 10)
    assert bounds(MockGeoInterface(g)) == (0, 0, 10, 10)


def test_bounds_z():
    g = {'type': 'Point', 'coordinates': [10, 10, 10]}
    assert bounds(g) == (10, 10, 10, 10)
    assert bounds(MockGeoInterface(g)) == (10, 10, 10, 10)


@pytest.mark.parametrize('geometry', [
    {'type': 'Polygon'},
    {'type': 'Polygon', 'not_coordinates': []},
    {'type': 'bogus', 'not_coordinates': []},
    {
        'type': 'GeometryCollection',
        'geometries': [
            {'type': 'Point', 'coordinates': [1, 1]},
            {'type': 'LineString', 'not_coordinates': [[-10, -20], [10, 20]]},
        ]
    }
])
def test_bounds_invalid_obj(geometry):
    with pytest.raises(ValueError, match="geometry must be a GeoJSON-like geometry, GeometryCollection, or FeatureCollection"):
        bounds(geometry)


def test_bounds_feature_collection(basic_featurecollection):
    fc = basic_featurecollection
    assert bounds(fc) == bounds(fc['features'][0]) == (2, 2, 4.25, 4.25)


def test_bounds_geometry_collection():
    gc = {
        'type': 'GeometryCollection',
        'geometries': [
            {'type': 'Point', 'coordinates': [1, 1]},
            {'type': 'LineString', 'coordinates': [[-10, -20], [10, 20]]},
            {'type': 'Polygon', 'coordinates': [[[5, 5], [25, 50], [25, 5]]]}
        ]
    }

    assert bounds(gc) == (-10, -20, 25, 50)
    assert bounds(MockGeoInterface(gc)) == (-10, -20, 25, 50)


def test_bounds_existing_bbox(basic_featurecollection):
    """Test with existing bbox in geojson.

    Similar to that produced by rasterio.  Values specifically modified here
    for testing, bboxes are not valid as written.
    """
    fc = basic_featurecollection
    fc['bbox'] = [0, 10, 10, 20]
    fc['features'][0]['bbox'] = [0, 100, 10, 200]

    assert bounds(fc['features'][0]) == (0, 100, 10, 200)
    assert bounds(fc) == (0, 10, 10, 20)


def test_geometry_mask(basic_geometry, basic_image_2x2):
    assert np.array_equal(
        basic_image_2x2 == 0,
        geometry_mask(
            [basic_geometry],
            out_shape=DEFAULT_SHAPE,
            transform=Affine.identity()
        )
    )


def test_geometry_mask_invert(basic_geometry, basic_image_2x2):
    assert np.array_equal(
        basic_image_2x2,
        geometry_mask(
            [basic_geometry],
            out_shape=DEFAULT_SHAPE,
            transform=Affine.identity(),
            invert=True
        )
    )


@pytest.mark.parametrize("geom", [{'type': 'Invalid'}, {'type': 'Point'}, {'type': 'Point', 'coordinates': []}])
def test_geometry_invalid_geom(geom):
    """An invalid geometry should fail"""
    with pytest.raises(ValueError) as exc_info, pytest.warns(ShapeSkipWarning):
        geometry_mask(
            [geom],
            out_shape=DEFAULT_SHAPE,
            transform=Affine.identity())

    assert 'No valid geometry objects found for rasterize' in exc_info.value.args[0]


def test_geometry_mask_invalid_shape(basic_geometry):
    """A width==0 or height==0 should fail with ValueError"""

    for shape in [(0, 0), (1, 0), (0, 1)]:
        with pytest.raises(ValueError) as exc_info:
            geometry_mask(
                [basic_geometry],
                out_shape=shape,
                transform=Affine.identity())

        assert 'must be > 0' in exc_info.value.args[0]


def test_geometry_mask_no_transform(basic_geometry):
    with pytest.raises(TypeError):
        geometry_mask(
            [basic_geometry],
            out_shape=DEFAULT_SHAPE,
            transform=None)


def test_geometry_window_no_pad(basic_image_file, basic_geometry):
    with rasterio.open(basic_image_file) as src:
        window = geometry_window(src, [basic_geometry, basic_geometry])
        assert window.flatten() == (2, 2, 3, 3)


def test_geometry_window_geo_interface(basic_image_file, basic_geometry):
    with rasterio.open(basic_image_file) as src:
        window = geometry_window(src, [MockGeoInterface(basic_geometry)])
        assert window.flatten() == (2, 2, 3, 3)


def test_geometry_window_pixel_precision(basic_image_file):
    """Window offsets should be floor, width and height ceiling"""

    geom2 = {
        'type': 'Polygon',
        'coordinates': [[
            (1.99999, 2),
            (1.99999, 4.0001), (4.0001, 4.0001), (4.0001, 2),
            (1.99999, 2)
        ]]
    }

    with rasterio.open(basic_image_file) as src:
        window = geometry_window(src, [geom2], pixel_precision=6)
        assert window.flatten() == (1, 2, 4, 3)


def test_geometry_window_north_up(path_rgb_byte_tif):
    geometry = {
        'type': 'Polygon',
        'coordinates': [[
            (200000, 2700000),
            (200000, 2750000),
            (250000, 2750000),
            (250000, 2700000),
            (200000, 2700000)
        ]]
    }

    with rasterio.open(path_rgb_byte_tif) as src:
        window = geometry_window(src, [geometry])
    assert window.flatten() == (326, 256, 168, 167)


def test_geometry_window_rotated_boundless():
    """Get the right boundless window for a rotated dataset"""
    sqrt2 = math.sqrt(2.0)
    dataset = mock.MagicMock()
    dataset.transform = (
        Affine.rotation(-45.0)
        * Affine.translation(-sqrt2, sqrt2)
        * Affine.scale(sqrt2 / 2.0, -sqrt2 / 2.0)
    )
    dataset.height = 4.0
    dataset.width = 4.0

    geometry = {
        "type": "Polygon",
        "coordinates": [
            [(-2.0, -2.0), (-2.0, 2.0), (2.0, 2.0), (2.0, -2.0), (-2.0, -2.0),]
        ],
    }

    win = geometry_window(dataset, [geometry, geometry], boundless=True)
    assert win.col_off == pytest.approx(-2.0)
    assert win.row_off == pytest.approx(-2.0)
    assert win.width == pytest.approx(2.0 * dataset.width)
    assert win.height == pytest.approx(2.0 * dataset.height)


def test_geometry_window_pad(basic_image_file, basic_geometry):
    # Note: this dataset's geotransform is not a geographic one.
    # x increases with col, but y also increases with row.
    # It's flipped, not rotated like a south-up world map.
    with rasterio.open(basic_image_file) as src:
        transform = src.transform
        dataset = mock.MagicMock()
        dataset.res = src.res
        dataset.transform = src.transform
        dataset.height = src.height
        dataset.width = src.width
        window = geometry_window(dataset, [basic_geometry], pad_x=0.5, pad_y=0.5)

    assert window.flatten() == (1, 1, 4, 4)


def test_geometry_window_large_shapes(basic_image_file):
    geometry = {
        'type': 'Polygon',
        'coordinates': [[
            (-2000, -2000),
            (-2000, 2000),
            (2000, 2000),
            (2000, -2000),
            (-2000, -2000)
        ]]
    }

    with rasterio.open(basic_image_file) as src:
        window = geometry_window(src, [geometry])
        assert window.flatten() == (0, 0, src.height, src.width)


def test_geometry_window_no_overlap(path_rgb_byte_tif, basic_geometry):
    """Geometries that do not overlap raster raises WindowError"""

    with rasterio.open(path_rgb_byte_tif) as src:
        with pytest.raises(WindowError):
            geometry_window(src, [basic_geometry], north_up=False)


def test_is_valid_geo_interface(geojson_point):
    """Properly formed Point object with geo interface is valid"""
    assert is_valid_geom(MockGeoInterface(geojson_point))


def test_is_valid_geom_point(geojson_point):
    """Properly formed GeoJSON Point is valid"""
    assert is_valid_geom(geojson_point)

    # Empty coordinates are invalid
    geojson_point['coordinates'] = []
    assert not is_valid_geom(geojson_point)


def test_is_valid_geom_multipoint(geojson_multipoint):
    """Properly formed GeoJSON MultiPoint is valid"""
    assert is_valid_geom(geojson_multipoint)

    # Empty iterable is invalid
    geom = deepcopy(geojson_multipoint)
    geom['coordinates'] = []
    assert not is_valid_geom(geom)

    # Empty first coordinate is invalid
    geom = deepcopy(geojson_multipoint)
    geom['coordinates'] = [[]]


def test_is_valid_geom_line(geojson_line):
    """Properly formed GeoJSON LineString is valid"""

    assert is_valid_geom(geojson_line)

    # Empty iterable is invalid
    geom = deepcopy(geojson_line)
    geom['coordinates'] = []
    assert not is_valid_geom(geom)

    # Empty first coordinate is invalid
    geom = deepcopy(geojson_line)
    geom['coordinates'] = [[]]


def test_is_valid_geom_multiline(geojson_line):
    """Properly formed GeoJSON MultiLineString is valid"""

    assert is_valid_geom(geojson_line)

    # Empty iterables are invalid
    geom = deepcopy(geojson_line)
    geom['coordinates'] = []
    assert not is_valid_geom(geom)

    geom = deepcopy(geojson_line)
    geom['coordinates'] = [[]]
    assert not is_valid_geom(geom)

    # Empty first coordinate is invalid
    geom = deepcopy(geojson_line)
    geom['coordinates'] = [[[]]]
    assert not is_valid_geom(geom)


def test_is_valid_geom_polygon(geojson_polygon):
    """Properly formed GeoJSON Polygon is valid"""

    assert is_valid_geom(geojson_polygon)

    # Empty iterables are invalid
    geom = deepcopy(geojson_polygon)
    geom['coordinates'] = []
    assert not is_valid_geom(geom)

    geom = deepcopy(geojson_polygon)
    geom['coordinates'] = [[]]
    assert not is_valid_geom(geom)

    # Empty first coordinate is invalid
    geom = deepcopy(geojson_polygon)
    geom['coordinates'] = [[[]]]
    assert not is_valid_geom(geom)


def test_is_valid_geom_ring(geojson_polygon):
    """Properly formed GeoJSON LinearRing is valid"""
    geojson_ring = deepcopy(geojson_polygon)
    geojson_ring['type'] = 'LinearRing'
    # take first ring from polygon as sample
    geojson_ring['coordinates'] = geojson_ring['coordinates'][0]
    assert is_valid_geom(geojson_ring)

    # Empty iterables are invalid
    geom = deepcopy(geojson_ring)
    geom['coordinates'] = []
    assert not is_valid_geom(geom)

    geom = deepcopy(geojson_ring)
    geom['coordinates'] = [[]]
    assert not is_valid_geom(geom)


def test_is_valid_geom_multipolygon(geojson_multipolygon):
    """Properly formed GeoJSON MultiPolygon is valid"""

    assert is_valid_geom(geojson_multipolygon)

    # Empty iterables are invalid
    geom = deepcopy(geojson_multipolygon)
    geom['coordinates'] = []
    assert not is_valid_geom(geom)

    geom = deepcopy(geojson_multipolygon)
    geom['coordinates'] = [[]]
    assert not is_valid_geom(geom)

    geom = deepcopy(geojson_multipolygon)
    geom['coordinates'] = [[[]]]
    assert not is_valid_geom(geom)

    # Empty first coordinate is invalid
    geom = deepcopy(geojson_multipolygon)
    geom['coordinates'] = [[[[]]]]
    assert not is_valid_geom(geom)


def test_is_valid_geom_geomcollection(geojson_geomcollection):
    """Properly formed GeoJSON GeometryCollection is valid"""

    assert is_valid_geom(geojson_geomcollection)

    # Empty GeometryCollection is invalid
    geom = deepcopy(geojson_geomcollection)
    geom['geometries'] = []
    assert not is_valid_geom(geom)


@pytest.mark.parametrize("geom", [None, 1, "foo", "type", ["type"], {"type": "Invalid"}, {"type": "Point"}])
def test_is_valid_geom_invalid_inputs(geom):
    """Improperly formed GeoJSON objects should fail"""
    assert not is_valid_geom(geom)


def test_rasterize_point(geojson_point):
    expected = np.zeros(shape=DEFAULT_SHAPE, dtype='uint8')
    expected[2, 2] = 1

    assert np.array_equal(
        rasterize([geojson_point], out_shape=DEFAULT_SHAPE),
        expected
    )


def test_rasterize_multipoint(geojson_multipoint):
    expected = np.zeros(shape=DEFAULT_SHAPE, dtype='uint8')
    expected[2, 2] = 1
    expected[4, 4] = 1

    assert np.array_equal(
        rasterize([geojson_multipoint], out_shape=DEFAULT_SHAPE),
        expected
    )


def test_rasterize_line(geojson_line):
    expected = np.zeros(shape=DEFAULT_SHAPE, dtype='uint8')
    expected[2, 2] = 1
    expected[3, 3] = 1
    expected[4, 4] = 1

    assert np.array_equal(
        rasterize([geojson_line], out_shape=DEFAULT_SHAPE),
        expected
    )


def test_rasterize_multiline(geojson_multiline):
    expected = np.zeros(shape=DEFAULT_SHAPE, dtype='uint8')
    expected[2, 2] = 1
    expected[3, 3] = 1
    expected[4, 4] = 1
    expected[0, 0:5] = 1

    assert np.array_equal(
        rasterize([geojson_multiline], out_shape=DEFAULT_SHAPE),
        expected
    )


def test_rasterize_polygon(geojson_polygon, basic_image_2x2):
    assert np.array_equal(
        rasterize([geojson_polygon], out_shape=DEFAULT_SHAPE),
        basic_image_2x2
    )


def test_rasterize_multipolygon(geojson_multipolygon):
    expected = np.zeros(shape=DEFAULT_SHAPE, dtype='uint8')
    expected[0:1, 0:1] = 1
    expected[2:4, 2:4] = 1

    assert np.array_equal(
        rasterize([geojson_multipolygon], out_shape=DEFAULT_SHAPE),
        expected
    )


def test_rasterize_geomcollection(geojson_geomcollection):
    expected = np.zeros(shape=DEFAULT_SHAPE, dtype='uint8')
    expected[0:1, 0:1] = 1
    expected[2:4, 2:4] = 1

    assert np.array_equal(
        rasterize([geojson_geomcollection], out_shape=DEFAULT_SHAPE),
        expected
    )


def test_rasterize_geo_interface(geojson_polygon, basic_image_2x2):
    assert np.array_equal(
        rasterize([MockGeoInterface(geojson_polygon)], out_shape=DEFAULT_SHAPE),
        basic_image_2x2
    )


def test_rasterize_geomcollection_no_hole():
    """
    Make sure that bug reported in
    https://github.com/rasterio/rasterio/issues/1253
    does not recur.  GeometryCollections are flattened to individual parts,
    and should result in no holes where parts overlap.
    """

    geomcollection = {'type': 'GeometryCollection', 'geometries': [
        {'type': 'Polygon',
            'coordinates': (((0, 0), (0, 5), (5, 5), (5, 0), (0, 0)),)},
        {'type': 'Polygon',
            'coordinates': (((2, 2), (2, 7), (7, 7), (7, 2), (2, 2)),)}
    ]}

    expected = rasterize(geomcollection['geometries'], out_shape=DEFAULT_SHAPE)

    assert np.array_equal(
        rasterize([geomcollection], out_shape=DEFAULT_SHAPE),
        expected
    )


def test_rasterize_multipolygon_no_hole():
    """
    Make sure that bug reported in
    https://github.com/rasterio/rasterio/issues/1253
    does not recur.  MultiPolygons are flattened to individual parts,
    and should result in no holes where parts overlap.
    """

    poly1 = (((0, 0), (0, 5), (5, 5), (5, 0), (0, 0)),)
    poly2 = (((2, 2), (2, 7), (7, 7), (7, 2), (2, 2)),)

    polys = [{'type': 'Polygon', 'coordinates': poly1},
             {'type': 'Polygon', 'coordinates': poly2}]

    multipoly = {'type': 'MultiPolygon', 'coordinates': [poly1, poly2]}

    expected = rasterize(polys, out_shape=DEFAULT_SHAPE)

    assert np.array_equal(
        rasterize([multipoly], out_shape=DEFAULT_SHAPE),
        expected
    )


@pytest.mark.parametrize("input", [
    [{'type'}], [{'type': 'Invalid'}], [{'type': 'Point'}], [{'type': 'Point', 'coordinates': []}], [{'type': 'GeometryCollection', 'geometries': []}]])
def test_rasterize_invalid_geom(input):
    """Invalid GeoJSON should fail with exception"""
    with pytest.raises(ValueError), pytest.warns(ShapeSkipWarning):
        rasterize(input, out_shape=DEFAULT_SHAPE)


def test_rasterize_skip_invalid_geom(geojson_polygon, basic_image_2x2):
    """Rasterize operation should succeed for at least one valid geometry
    and should skip any invalid or empty geometries with an error."""

    with pytest.warns(UserWarning, match="Invalid or empty shape"):
        out = rasterize([geojson_polygon, {'type': 'Polygon', 'coordinates': []}], out_shape=DEFAULT_SHAPE)

    assert np.array_equal(out, basic_image_2x2)


def test_rasterize_out_image(basic_geometry, basic_image_2x2):
    """Rasterize operation should succeed for an out image."""
    out = np.zeros(DEFAULT_SHAPE)
    rasterize([basic_geometry], out=out)
    assert np.array_equal(basic_image_2x2, out)


def test_rasterize_int64_out_dtype(basic_geometry):
    """A non-supported data type for out should raise an exception."""
    out = np.zeros(DEFAULT_SHAPE, dtype=np.int64)
    if gdal_version.at_least("3.5"):
        rasterize([basic_geometry], out=out)
    else:
        with pytest.raises(ValueError):
            rasterize([basic_geometry], out=out)


def test_rasterize_shapes_out_dtype_mismatch(basic_geometry):
    """Shape values must be able to fit in data type for out."""
    out = np.zeros(DEFAULT_SHAPE, dtype=np.uint8)
    with pytest.raises(ValueError):
        rasterize([(basic_geometry, 10000000)], out=out)


def test_rasterize_missing_out(basic_geometry):
    """If both out and out_shape are missing, should raise exception."""
    with pytest.raises(ValueError):
        rasterize([basic_geometry], out=None, out_shape=None)


def test_rasterize_missing_shapes():
    """Shapes are required for this operation."""
    with pytest.raises(ValueError) as ex:
        rasterize([], out_shape=DEFAULT_SHAPE)

    assert 'No valid geometry objects' in str(ex.value)


def test_rasterize_invalid_shapes():
    """Invalid shapes should raise an exception rather than be skipped."""
    with pytest.raises(ValueError) as ex, pytest.warns(ShapeSkipWarning):
        rasterize([{'foo': 'bar'}], out_shape=DEFAULT_SHAPE)

    assert 'No valid geometry objects found for rasterize' in str(ex.value)


def test_rasterize_invalid_out_shape(basic_geometry):
    """output array shape must be 2D."""
    with pytest.raises(ValueError) as ex:
        rasterize([basic_geometry], out_shape=(1, 10, 10))
    assert 'Invalid out_shape' in str(ex.value)

    with pytest.raises(ValueError) as ex:
        rasterize([basic_geometry], out_shape=(10,))
    assert 'Invalid out_shape' in str(ex.value)

    for shape in [(0, 0), (1, 0), (0, 1)]:
        with pytest.raises(ValueError) as ex:
            rasterize([basic_geometry], out_shape=shape)
        assert 'must be > 0' in str(ex.value)


def test_rasterize_default_value(basic_geometry, basic_image_2x2):
    """All shapes should rasterize to the default value."""
    default_value = 2
    truth = basic_image_2x2 * default_value

    assert np.array_equal(
        truth,
        rasterize(
            [basic_geometry], out_shape=DEFAULT_SHAPE,
            default_value=default_value
        )
    )


def test_rasterize_default_value_for_none(basic_geometry, basic_image_2x2):
    """All shapes should rasterize to the default value."""
    assert np.all(
        rasterize([(basic_geometry, None)], out_shape=DEFAULT_SHAPE, fill=2) == 2
    )


def test_rasterize_int64_default_value(basic_geometry):
    """A default value that requires an int64 should raise an exception."""
    if gdal_version.at_least("3.5"):
            rasterize(
                [basic_geometry], out_shape=DEFAULT_SHAPE,
                default_value=1000000000000
            )
    else:
        with pytest.raises(ValueError):
            rasterize(
                [basic_geometry], out_shape=DEFAULT_SHAPE,
                default_value=1000000000000
            )


def test_rasterize_fill_value(basic_geometry, basic_image_2x2):
    """All pixels not covered by shapes should be given fill value."""
    default_value = 2
    assert np.array_equal(
        basic_image_2x2 + 1,
        rasterize(
            [basic_geometry], out_shape=DEFAULT_SHAPE, fill=1,
            default_value=default_value
        )
    )


def test_rasterize_invalid_fill_value(basic_geometry):
    """A fill value that requires an int64 should raise an exception."""
    if gdal_version.at_least("3.5"):
        rasterize(
            [basic_geometry], out_shape=DEFAULT_SHAPE, fill=1000000000000,
            default_value=2
        )
    else:
        with pytest.raises(ValueError):
            rasterize(
                [basic_geometry], out_shape=DEFAULT_SHAPE, fill=1000000000000,
                default_value=2
            )


def test_rasterize_fill_value_dtype_mismatch(basic_geometry):
    """A fill value that doesn't match dtype should fail."""
    with pytest.raises(ValueError):
        rasterize(
            [basic_geometry], out_shape=DEFAULT_SHAPE, fill=1000000,
            default_value=2, dtype=np.uint8
        )


def test_rasterize_all_touched(basic_geometry, basic_image):
    assert np.array_equal(
        basic_image,
        rasterize(
            [basic_geometry], out_shape=DEFAULT_SHAPE, all_touched=True
        )
    )


def test_rasterize_merge_alg_add(basic_geometry, basic_image_2x2x2):
    """
    Rasterizing two times the basic_geometry with the "add" merging
    option should output the shape with the value 2
    """
    with rasterio.Env():
        assert np.array_equal(
            basic_image_2x2x2,
            rasterize(
                [basic_geometry, basic_geometry], merge_alg=MergeAlg.add,
                out_shape=DEFAULT_SHAPE)
        )


def test_rasterize_value(basic_geometry, basic_image_2x2):
    """
    All shapes should rasterize to the value passed in a tuple alongside
    each shape
    """
    value = 5
    assert np.array_equal(
        basic_image_2x2 * value,
        rasterize(
            [(basic_geometry, value)], out_shape=DEFAULT_SHAPE
        )
    )


@requires_gdal_lt_35
def test_rasterize_invalid_value(basic_geometry):
    """A shape value that requires an int64 should raise an exception."""
    with pytest.raises(ValueError, match="Values out of range for supported dtypes"):
        rasterize(
            [(basic_geometry, 1000000000000)], out_shape=DEFAULT_SHAPE
        )


@pytest.mark.parametrize(
    "dtype,default_value",
    [
        ("int16", -32768),
        ("int32", -2147483648),
        pytest.param(
            "uint32",
            4294967295,
            marks=pytest.mark.xfail(
                gdal_version.at_least("3.5"), reason="GDAL regression? Works with 3.4.3"
            ),
        ),
        ("uint8", 255),
        ("uint16", 65535),
        ("float32", 1.434532),
        ("float64", -98332.133422114),
    ],
)
def test_rasterize_supported_dtype(dtype, default_value, basic_geometry):
    """Supported data types should return valid results."""
    truth = np.zeros(DEFAULT_SHAPE, dtype=dtype)
    truth[2:4, 2:4] = default_value

    result = rasterize(
        [basic_geometry],
        out_shape=DEFAULT_SHAPE,
        default_value=default_value,
        dtype=dtype,
    )
    assert np.array_equal(result, truth)
    assert np.dtype(result.dtype) == np.dtype(truth.dtype)

    result = rasterize([(basic_geometry, default_value)], out_shape=DEFAULT_SHAPE)
    if np.dtype(dtype).kind == "f":
        assert np.allclose(result, truth)
    else:
        assert np.array_equal(result, truth)
    # Since dtype is auto-detected, it may not match due to upcasting


def test_rasterize_unsupported_dtype(basic_geometry):
    """Unsupported types should all raise exceptions."""
    unsupported_types = (
        ('int8', -127),
        ('float16', -9343.232)
    )
    if not gdal_version.at_least("3.5"):
        unsupported_types += (('int64', 20439845334323),)

    for dtype, default_value in unsupported_types:
        with pytest.raises(ValueError):
            rasterize(
                [basic_geometry],
                out_shape=DEFAULT_SHAPE,
                default_value=default_value,
                dtype=dtype
            )

        with pytest.raises(ValueError):
            rasterize(
                [(basic_geometry, default_value)],
                out_shape=DEFAULT_SHAPE,
                dtype=dtype
            )


def test_rasterize_mismatched_dtype(basic_geometry):
    """Mismatched values and dtypes should raise exceptions."""
    mismatched_types = (('uint8', 3.2423), ('uint8', -2147483648))
    for dtype, default_value in mismatched_types:
        with pytest.raises(ValueError):
            rasterize(
                [basic_geometry],
                out_shape=DEFAULT_SHAPE,
                default_value=default_value,
                dtype=dtype
            )

        with pytest.raises(ValueError):
            rasterize(
                [(basic_geometry, default_value)],
                out_shape=DEFAULT_SHAPE,
                dtype=dtype
            )


def test_rasterize_geometries_symmetric():
    """Make sure that rasterize is symmetric with shapes."""
    transform = (1.0, 0.0, 0.0, 0.0, -1.0, 0.0)
    truth = np.zeros(DEFAULT_SHAPE, dtype=rasterio.ubyte)
    truth[2:5, 2:5] = 1
    s = shapes(truth, transform=transform)
    result = rasterize(s, out_shape=DEFAULT_SHAPE, transform=transform)
    assert np.array_equal(result, truth)


def test_rasterize_internal_driver_manager(basic_geometry):
    """Rasterize should work without explicitly calling driver manager."""
    assert rasterize([basic_geometry], out_shape=DEFAULT_SHAPE).sum() == 4


def test_rasterize_geo_interface_2(geojson_polygon):
    """Objects that implement the geo interface should rasterize properly"""

    class GeoObj:
        @property
        def __geo_interface__(self):
            return geojson_polygon

    assert rasterize([GeoObj()], out_shape=DEFAULT_SHAPE).sum() == 4


def test_rasterize__numpy_coordinates__fail():
    # https://github.com/rasterio/rasterio/issues/2385
    shapes = [
        (
            {
                "type": "LineString",
                "coordinates": np.array(
                    [
                        [425596.0123443, 4932971.35636043],
                        [425598.03434254, 4932966.09916503],
                        [425592.56573176, 4932963.99585319],
                        [425590.54373353, 4932969.2530486],
                        [425596.0123443, 4932971.35636043],
                    ]
                ),
            },
            2,
        ),
        (
            {
                "type": "LineString",
                "coordinates": np.array(
                    [
                        [425582.9243515, 4932973.24623693],
                        [425592.85588065, 4932951.94800393],
                        [425584.24595668, 4932947.93313045],
                        [425574.31442752, 4932969.23136344],
                        [425582.9243515, 4932973.24623693],
                    ]
                ),
            },
            2,
        ),
    ]
    out = rasterio.features.rasterize(shapes=shapes, out_shape=(100, 100))
    assert out.shape == (100, 100)
    # will fail and be filled with 0
    assert (out == 0).all()


def test_shapes(basic_image):
    """Test creation of shapes from pixel values."""
    results = list(shapes(basic_image))

    assert len(results) == 2

    shape, value = results[0]
    assert shape == {
        'coordinates': [
            [(2, 2), (2, 5), (5, 5), (5, 2), (2, 2)]
        ],
        'type': 'Polygon'
    }
    assert value == 1

    shape, value = results[1]
    assert shapely.geometry.shape(shape).area == 91.0
    assert value == 0


def test_shapes_2509(basic_image):
    """Test creation of shapes from pixel values, issue #2509."""
    image_with_strides = np.pad(basic_image, 1)[1:-1, 1:-1]
    np.testing.assert_array_equal(basic_image, image_with_strides)
    assert image_with_strides.__array_interface__["strides"] is not None

    results = list(shapes(image_with_strides))

    assert len(results) == 2

    shape, value = results[0]
    assert shape == {
        'coordinates': [
            [(2, 2), (2, 5), (5, 5), (5, 2), (2, 2)]
        ],
        'type': 'Polygon'
    }
    assert value == 1

    shape, value = results[1]
    assert shapely.geometry.shape(shape).area == 91.0
    assert value == 0


def test_shapes_band(pixelated_image, pixelated_image_file):
    """Shapes from a band should match shapes from an array."""
    truth = list(shapes(pixelated_image))

    with rasterio.open(pixelated_image_file) as src:
        band = rasterio.band(src, 1)
        assert truth == list(shapes(band))

        # Mask band should function, but will mask out some results
        assert truth[0] == list(shapes(band, mask=band))[0]


def test_shapes_connectivity_rook(diagonal_image):
    """
    Diagonals are not connected, so there will be 1 feature per pixel plus
    background.
    """
    assert len(list(shapes(diagonal_image, connectivity=4))) == 12


def test_shapes_connectivity_queen(diagonal_image):
    """
    Diagonals are connected, so there will be 1 feature for all pixels plus
    background.
    """
    assert len(list(shapes(diagonal_image, connectivity=8))) == 2


def test_shapes_connectivity_invalid(diagonal_image):
    """Invalid connectivity should raise exception."""
    with pytest.raises(ValueError):
        assert next(shapes(diagonal_image, connectivity=12))


def test_shapes_mask(basic_image):
    """Only pixels not masked out should be converted to features."""
    mask = np.ones(basic_image.shape, dtype=rasterio.bool_)
    mask[4:5, 4:5] = False

    results = list(shapes(basic_image, mask=mask))

    assert len(results) == 2

    shape, value = results[0]
    assert shape == {
        'coordinates': [
            [(2, 2), (2, 5), (4, 5), (4, 4), (5, 4), (5, 2), (2, 2)]
        ],
        'type': 'Polygon'
    }
    assert value == 1


def test_shapes_masked_array(basic_image):
    """Only pixels not masked out should be converted to features."""
    mask = np.full(basic_image.shape, False, dtype=rasterio.bool_)
    mask[4:5, 4:5] = True

    results = list(shapes(np.ma.masked_array(basic_image, mask=mask)))

    assert len(results) == 2

    shape, value = results[0]
    assert shape == {
        'coordinates': [
            [(2, 2), (2, 5), (4, 5), (4, 4), (5, 4), (5, 2), (2, 2)]
        ],
        'type': 'Polygon'
    }
    assert value == 1


def test_shapes_blank_mask(basic_image):
    """Mask is blank so results should mask shapes without mask."""
    assert np.array_equal(
        list(shapes(
            basic_image,
            mask=np.ones(basic_image.shape, dtype=rasterio.bool_))
        ),
        list(shapes(basic_image))
    )


def test_shapes_invalid_mask_shape(basic_image):
    """A mask that is the wrong shape should fail."""
    with pytest.raises(ValueError):
        next(shapes(
            basic_image,
            mask=np.ones(
                (basic_image.shape[0] + 10, basic_image.shape[1] + 10),
                dtype=rasterio.bool_
            )
        ))


def test_shapes_invalid_mask_dtype(basic_image):
    """A mask that is the wrong dtype should fail."""
    for dtype in ('int8', 'int16', 'int32'):
        with pytest.raises(ValueError):
            next(shapes(
                basic_image,
                mask=np.ones(basic_image.shape, dtype=dtype)
            ))


def test_shapes_supported_dtypes(basic_image):
    """Supported data types should return valid results."""
    supported_types = (
        ('int16', -32768),
        ('int32', -2147483648),
        ('uint8', 255),
        ('uint16', 65535),
        ('float32', 1.434532)
    )

    for dtype, test_value in supported_types:
        shape, value = next(shapes(basic_image.astype(dtype) * test_value))
        assert np.allclose(value, test_value)


def test_shapes_unsupported_dtypes(basic_image):
    """Unsupported data types should raise exceptions."""
    unsupported_types = (
        ('int8', -127),
        ('uint32', 4294967295),
        ('int64', 20439845334323),
        ('float16', -9343.232),
        ('float64', -98332.133422114)
    )

    for dtype, test_value in unsupported_types:
        with pytest.raises(ValueError):
            next(shapes(basic_image.astype(dtype) * test_value))


def test_shapes_internal_driver_manager(basic_image):
    """Shapes should work without explicitly calling driver manager."""
    assert next(shapes(basic_image))[0]['type'] == 'Polygon'


def test_sieve_small(basic_image, pixelated_image):
    """
    Setting the size smaller than or equal to the size of the feature in the
    image should not change the image.
    """
    assert np.array_equal(
        basic_image,
        sieve(pixelated_image, basic_image.sum())
    )


def test_sieve_large(basic_image):
    """
    Setting the size larger than size of feature should leave us an empty image.
    """
    assert not np.any(sieve(basic_image, basic_image.sum() + 1))


def test_sieve_invalid_size(basic_image):
    for invalid_size in (0, 45.1234, basic_image.size + 1):
        with pytest.raises(ValueError):
            sieve(basic_image, invalid_size)


def test_sieve_connectivity_rook(diagonal_image):
    """Diagonals are not connected, so feature is removed."""
    assert not np.any(
        sieve(diagonal_image, diagonal_image.sum(), connectivity=4)
    )


def test_sieve_connectivity_queen(diagonal_image):
    """Diagonals are connected, so feature is retained."""
    assert np.array_equal(
        diagonal_image,
        sieve(diagonal_image, diagonal_image.sum(), connectivity=8)
    )


def test_sieve_connectivity_invalid(basic_image):
    with pytest.raises(ValueError):
        sieve(basic_image, 54, connectivity=12)


def test_sieve_out(basic_image):
    """Output array passed in should match the returned array."""
    output = np.zeros_like(basic_image)
    output[1:3, 1:3] = 5
    sieved_image = sieve(basic_image, basic_image.sum(), out=output)
    assert np.array_equal(basic_image, sieved_image)
    assert np.array_equal(output, sieved_image)


def test_sieve_invalid_out(basic_image):
    """Output with different dtype or shape should fail."""
    with pytest.raises(ValueError):
        sieve(
            basic_image, basic_image.sum(),
            out=np.zeros(basic_image.shape, dtype=rasterio.int32)
        )

    with pytest.raises(ValueError):
        sieve(
            basic_image, basic_image.sum(),
            out=np.zeros(
                (basic_image.shape[0] + 10, basic_image.shape[1] + 10),
                dtype=rasterio.ubyte
            )
        )


def test_sieve_mask(basic_image):
    """
    Only areas within the overlap of mask and input will be kept, so long
    as mask is a bool or uint8 dtype.
    """
    mask = np.ones(basic_image.shape, dtype=rasterio.bool_)
    mask[4:5, 4:5] = False
    truth = basic_image * np.invert(mask)

    sieved_image = sieve(basic_image, basic_image.sum(), mask=mask)
    assert sieved_image.sum() > 0

    assert np.array_equal(
        truth,
        sieved_image
    )

    assert np.array_equal(
        truth.astype(rasterio.uint8),
        sieved_image
    )


def test_sieve_blank_mask(basic_image):
    """A blank mask should have no effect."""
    mask = np.ones(basic_image.shape, dtype=rasterio.bool_)
    assert np.array_equal(
        basic_image,
        sieve(basic_image, basic_image.sum(), mask=mask)
    )


def test_sieve_invalid_mask_shape(basic_image):
    """A mask that is the wrong shape should fail."""
    with pytest.raises(ValueError):
        sieve(
            basic_image, basic_image.sum(),
            mask=np.ones(
                (basic_image.shape[0] + 10, basic_image.shape[1] + 10),
                dtype=rasterio.bool_
            )
        )


def test_sieve_invalid_mask_dtype(basic_image):
    """A mask that is the wrong dtype should fail."""
    for dtype in ('int8', 'int16', 'int32'):
        with pytest.raises(ValueError):
            sieve(
                basic_image, basic_image.sum(),
                mask=np.ones(basic_image.shape, dtype=dtype)
            )


def test_sieve_supported_dtypes(basic_image):
    """Supported data types should return valid results."""
    supported_types = (
        ('int16', -32768),
        ('int32', -2147483648),
        ('uint8', 255),
        ('uint16', 65535)
    )

    for dtype, test_value in supported_types:
        truth = (basic_image).astype(dtype) * test_value
        sieved_image = sieve(truth, basic_image.sum())
        assert np.array_equal(truth, sieved_image)
        assert np.dtype(sieved_image.dtype) == np.dtype(dtype)


def test_sieve_unsupported_dtypes(basic_image):
    """Unsupported data types should raise exceptions."""
    unsupported_types = (
        ('int8', -127),
        ('uint32', 4294967295),
        ('int64', 20439845334323),
        ('float16', -9343.232),
        ('float32', 1.434532),
        ('float64', -98332.133422114)
    )

    for dtype, test_value in unsupported_types:
        with pytest.raises(ValueError):
            sieve(
                (basic_image).astype(dtype) * test_value,
                basic_image.sum()
            )


def test_sieve_band(pixelated_image, pixelated_image_file):
    """Sieving a band from a raster file should match sieve of array."""

    truth = sieve(pixelated_image, 9)

    with rasterio.open(pixelated_image_file) as src:
        band = rasterio.band(src, 1)
        assert np.array_equal(truth, sieve(band, 9))

        # Mask band should also work but will be a no-op
        assert np.array_equal(
            pixelated_image,
            sieve(band, 9, mask=band)
        )


def test_sieve_internal_driver_manager(capfd, basic_image, pixelated_image):
    """Sieve should work without explicitly calling driver manager."""
    assert np.array_equal(
        basic_image,
        sieve(pixelated_image, basic_image.sum())
    )


def test_zz_no_dataset_leaks(capfd):
    with rasterio.Env() as env:
        env._dump_open_datasets()
        captured = capfd.readouterr()
        assert not captured.err

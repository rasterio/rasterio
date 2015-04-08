import logging
import os
import re
import sys

import click
from click.testing import CliRunner

import rasterio
from rasterio.rio import features


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

TEST_FEATURES = """{
    "geometry": {
        "coordinates": [
            [
                [-110, 40],
                [-100, 40],
                [-100, 45],
                [-105, 45],
                [-110, 40]
            ]
        ],
        "type": "Polygon"
    },
    "properties": {
        "val": 15
    },
    "type": "Feature"
}"""


# > rio shapes tests/data/shade.tif --mask --sampling 500 --projected --precision 0
TEST_MERC_FEATURECOLLECTION = """{
    "bbox": [-11858135.0, 4803914.0, -11848351.0, 4813698.0],
    "features": [{
        "bbox": [-11853357.504145855, 4808920.97837715,
                 -11848580.189878704, 4813698.2926443005],
        "geometry": {
            "coordinates": [
                [
                    [-11853357.504145855, 4813698.2926443005],
                    [-11853357.504145855, 4808920.97837715],
                    [-11848580.189878704, 4808920.97837715],
                    [-11848580.189878704, 4813698.2926443005],
                    [-11853357.504145855, 4813698.2926443005]
                ]
            ],
            "type": "Polygon"
        },
        "properties": {
            "val": 2
        },
        "type": "Feature"
    }, {
        "bbox": [-11858134.818413004, 4804143.66411,
                 -11853357.504145855, 4808920.97837715],
        "geometry": {
            "coordinates": [
                [
                    [-11858134.818413004, 4808920.97837715],
                    [-11858134.818413004, 4804143.66411],
                    [-11853357.504145855, 4804143.66411],
                    [-11853357.504145855, 4808920.97837715],
                    [-11858134.818413004, 4808920.97837715]
                ]
            ],
            "type": "Polygon"
        },
        "properties": {
            "val": 3
        },
        "type": "Feature"
    }],
    "type": "FeatureCollection"
}"""


def test_err():
    runner = CliRunner()
    result = runner.invoke(
        features.shapes, ['tests/data/shade.tif', '--bidx', '4'])
    assert result.exit_code == 1


def test_shapes(runner):
    result = runner.invoke(features.shapes, ['tests/data/shade.tif'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 232


def test_shapes_sequence(runner):
    result = runner.invoke(features.shapes, ['tests/data/shade.tif', '--sequence'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 0
    assert result.output.count('"Feature"') == 232


def test_shapes_sequence_rs(runner):
    result = runner.invoke(
        features.shapes, [
            'tests/data/shade.tif',
            '--sequence',
            '--rs'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 0
    assert result.output.count('"Feature"') == 232
    assert result.output.count(u'\u001e') == 232


def test_shapes_with_nodata(runner):
    result = runner.invoke(features.shapes, ['tests/data/shade.tif', '--with-nodata'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 288


def test_shapes_indent(runner):
    result = runner.invoke(features.shapes, ['tests/data/shade.tif', '--indent', '2'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('\n') == 70371


def test_shapes_compact(runner):
    result = runner.invoke(features.shapes, ['tests/data/shade.tif', '--compact'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count(', ') == 0
    assert result.output.count(': ') == 0


def test_shapes_sampling(runner):
    result = runner.invoke(
        features.shapes, ['tests/data/shade.tif', '--sampling', '10'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 124


def test_shapes_precision(runner):
    result = runner.invoke(
        features.shapes, ['tests/data/shade.tif', '--precision', '1'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    # Find no numbers with 2+ decimal places.
    assert re.search(r'\d*\.\d{2,}', result.output) is None


def test_shapes_mask(runner):
    result = runner.invoke(features.shapes, ['tests/data/RGB.byte.tif', '--mask'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 7


def test_shapes_mask_decimated(runner):
    result = runner.invoke(
        features.shapes, 
        ['tests/data/RGB.byte.tif', '--mask', '--sampling', '10'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 1


def test_shapes_band1_as_mask(runner):
    result = runner.invoke(features.shapes,
        ['tests/data/RGB.byte.tif', '--band', '--bidx', '1', '--as-mask'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 9


def test_rasterize_err(tmpdir, runner):
    output = str(tmpdir.join('test.tif'))
    # Test invalid stdin
    result = runner.invoke(features.rasterize, [output], input='BOGUS')
    assert result.exit_code == -1

    # Test invalid GeoJSON
    result = runner.invoke(features.rasterize, [output],
                           input='{"foo": "bar"}')
    assert result.exit_code == 2

    # Test invalid res
    result = runner.invoke(features.rasterize, [output], input=TEST_FEATURES)
    assert result.exit_code == 2

    # Test invalid CRS for bounds
    result = runner.invoke(features.rasterize, [output, '--res', 1],
                           input=TEST_MERC_FEATURECOLLECTION)
    assert result.exit_code == 2

    # Test invalid CRS value
    result = runner.invoke(features.rasterize, [output,
                                                '--res', 1,
                                                '--src_crs', 'BOGUS'],
                           input=TEST_MERC_FEATURECOLLECTION)
    assert result.exit_code == 2


def test_rasterize(tmpdir, runner):
    # Test dimensions
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(features.rasterize,
                           [output, '--dimensions', 20, 10],
                           input=TEST_FEATURES)
    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert out.count == 1
        assert out.meta['width'] == 20
        assert out.meta['height'] == 10
        data = out.read(1, masked=False)
        assert (data == 0).sum() == 55
        assert (data == 1).sum() == 145

    # Test dimensions and bounds
    output = str(tmpdir.join('test2.tif'))
    result = runner.invoke(features.rasterize,
                           [output,
                            '--dimensions', 40, 20,
                            '--bounds', -120, 30, -90, 50
                           ], input=TEST_FEATURES)
    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert out.count == 1
        assert out.meta['width'] == 40
        assert out.meta['height'] == 20
        data = out.read(1, masked=False)
        assert (data == 0).sum() == 748
        assert (data == 1).sum() == 52

    # Test resolution
    output = str(tmpdir.join('test3.tif'))
    result = runner.invoke(features.rasterize,
                           [output, '--res', 0.5], input=TEST_FEATURES)
    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert out.count == 1
        assert out.meta['width'] == 20
        assert out.meta['height'] == 10
        data = out.read(1, masked=False)
        assert (data == 0).sum() == 55
        assert (data == 1).sum() == 145

    # Test that src_crs is written into new output
    output = str(tmpdir.join('test4.tif'))
    result = runner.invoke(features.rasterize,
                           [output,
                            '--dimensions', 20, 10,
                            '--src_crs', 'EPSG:3857'
                           ],
                           input=TEST_MERC_FEATURECOLLECTION)
    assert result.exit_code == 0
    with rasterio.open(output) as out:
        assert out.crs['init'].lower() == 'epsg:3857'


def test_rasterize_existing_output(tmpdir, runner):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(features.rasterize,
                           [output, '--res', 0.5], input=TEST_FEATURES)
    assert result.exit_code == 0
    assert os.path.exists(output)

    geojson = """{
        "geometry": {
            "coordinates": [
                [
                    [-102, 40],
                    [-98, 40],
                    [-98, 45],
                    [-100, 45],
                    [-102, 40]
                ]
            ],
            "type": "Polygon"
        },
        "type": "Feature"
    }"""

    result = runner.invoke(features.rasterize, [output, '--default_value', 2],
                           input=geojson)

    with rasterio.open(output) as out:
        assert out.count == 1
        data = out.read(1, masked=False)
        assert (data == 0).sum() == 55
        assert (data == 1).sum() == 125
        assert (data == 2).sum() == 20

    # Confirm that a different src_crs is rejected, even if a geographic crs
    result = runner.invoke(features.rasterize,
                           [output,
                            '--res', 0.5,
                            '--src_crs', 'EPSG:4269'
                            ], input=TEST_FEATURES)
    assert result.exit_code == 2


def test_rasterize_like(tmpdir, runner):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(features.rasterize,
                           [output, '--like', 'tests/data/shade.tif'],
                           input=TEST_MERC_FEATURECOLLECTION)
    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert out.count == 1
        data = out.read(1, masked=False)
        assert (data == 0).sum() == 548576
        assert (data == 1).sum() == 500000

    # Test invalid like raster
    output = str(tmpdir.join('test2.tif'))
    result = runner.invoke(features.rasterize,
                           [output, '--like', str(tmpdir.join('foo.tif'))], input=TEST_FEATURES)
    assert result.exit_code == 2

    # Test that src_crs different than --like raster crs breaks
    output = str(tmpdir.join('test3.tif'))
    result = runner.invoke(features.rasterize,
                           [output,
                            '--like', 'tests/data/shade.tif',
                            '--src_crs', 'EPSG:4326'],
                           input=TEST_FEATURES)
    assert result.exit_code == 2


def test_rasterize_property_value(tmpdir, runner):
    # Test feature collection property values
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(features.rasterize,
                           [output,
                            '--res', 1000,
                            '--property', 'val',
                            '--src_crs', 'EPSG:3857'
                           ],
                           input=TEST_MERC_FEATURECOLLECTION)
    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert out.count == 1
        data = out.read(1, masked=False)
        assert (data == 0).sum() == 50
        assert (data == 2).sum() == 25
        assert (data == 3).sum() == 25

    # Test feature property values
    output = str(tmpdir.join('test2.tif'))
    result = runner.invoke(features.rasterize,
                           [output, '--res', 0.5, '--property', 'val'],
                           input=TEST_FEATURES)
    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert out.count == 1
        data = out.read(1, masked=False)
        assert (data == 0).sum() == 55
        assert (data == 15).sum() == 145


def test_rasterize_out_of_bounds(tmpdir, runner):
    output = str(tmpdir.join('test.tif'))

    # Test out of bounds of --like raster
    result = runner.invoke(features.rasterize,
                           [output, '--like', 'tests/data/shade.tif'],
                           input=TEST_FEATURES)
    assert result.exit_code == 0
    assert 'outside bounds' in result.output
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        data = out.read_band(1, masked=False)
        assert data.sum() == 0

    # Confirm that this does not fail when out of bounds for existing raster
    result = runner.invoke(features.rasterize, [output], input=TEST_FEATURES)
    assert result.exit_code == 0
    assert 'outside bounds' in result.output

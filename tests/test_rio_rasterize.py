"""Tests for ``$ rio rasterize``."""


import json
import os

import numpy as np

import rasterio
from rasterio.features import rasterize
from rasterio.rio.main import main_group


DEFAULT_SHAPE = (10, 10)


def bbox(*args):
    return ' '.join([str(x) for x in args])


def test_rasterize(tmpdir, runner, basic_feature):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, [
            'rasterize', output, '--dimensions', DEFAULT_SHAPE[0],
            DEFAULT_SHAPE[1]],
        input=json.dumps(basic_feature))

    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert np.allclose(out.bounds, (2, 2, 4.25, 4.25))
        data = out.read(1, masked=False)
        assert data.shape == DEFAULT_SHAPE
        assert np.all(data)


def test_rasterize_file(tmpdir, runner, basic_feature):
    """Confirm fix of #1425"""
    geojson_file = tmpdir.join('input.geojson')
    geojson_file.write(json.dumps(basic_feature))
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, [
            'rasterize', str(geojson_file), output, '--dimensions', DEFAULT_SHAPE[0],
            DEFAULT_SHAPE[1]])

    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert np.allclose(out.bounds, (2, 2, 4.25, 4.25))
        data = out.read(1, masked=False)
        assert data.shape == DEFAULT_SHAPE
        assert np.all(data)


def test_rasterize_bounds(tmpdir, runner, basic_feature, basic_image_2x2):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, [
            'rasterize', output, '--dimensions', DEFAULT_SHAPE[0],
            DEFAULT_SHAPE[1], '--bounds', bbox(0, 10, 10, 0)],
        input=json.dumps(basic_feature))

    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert np.allclose(out.bounds, (0, 10, 10, 0))
        data = out.read(1, masked=False)
        assert np.array_equal(basic_image_2x2, data)
        assert data.shape == DEFAULT_SHAPE


def test_rasterize_resolution(tmpdir, runner, basic_feature):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['rasterize', output, '--res', 0.15],
        input=json.dumps(basic_feature))

    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert np.allclose(out.bounds, (2, 2, 4.25, 4.25))
        data = out.read(1, masked=False)
        assert data.shape == (15, 15)
        assert np.all(data)


def test_rasterize_multiresolution(tmpdir, runner, basic_feature):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['rasterize', output, '--res', 0.15, '--res', 0.15],
        input=json.dumps(basic_feature)
    )

    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert np.allclose(out.bounds, (2, 2, 4.25, 4.25))
        data = out.read(1, masked=False)
        assert data.shape == (15, 15)
        assert np.all(data)


def test_rasterize_src_crs(tmpdir, runner, basic_feature):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, [
            'rasterize', output, '--dimensions', DEFAULT_SHAPE[0],
            DEFAULT_SHAPE[1], '--src-crs', 'EPSG:3857'],
        input=json.dumps(basic_feature))

    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert out.crs.to_epsg() == 3857


def test_rasterize_mismatched_src_crs(tmpdir, runner, basic_feature):
    """
    A --src-crs that is geographic with coordinates that are outside
    world bounds should fail.
    """

    coords = np.array(basic_feature['geometry']['coordinates']) * 100000
    basic_feature['geometry']['coordinates'] = coords.tolist()

    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, [
            'rasterize', output, '--dimensions', DEFAULT_SHAPE[0],
            DEFAULT_SHAPE[1], '--src-crs', 'EPSG:4326'],
        input=json.dumps(basic_feature))

    assert result.exit_code == 2
    assert 'Bounds are beyond the valid extent for EPSG:4326' in result.output


def test_rasterize_invalid_src_crs(tmpdir, runner, basic_feature):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, [
            'rasterize', output, '--dimensions', DEFAULT_SHAPE[0],
            DEFAULT_SHAPE[1], '--src-crs', 'foo:bar'],
        input=json.dumps(basic_feature))

    assert result.exit_code == 2
    assert 'invalid CRS.  Must be an EPSG code.' in result.output


def test_rasterize_existing_output(tmpdir, runner, basic_feature):
    """
    Create a rasterized output, then rasterize additional pixels into it.
    The final result should include rasterized pixels from both
    """

    truth = np.zeros(DEFAULT_SHAPE)
    truth[2:4, 2:4] = 1
    truth[4:6, 4:6] = 1

    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, [
            'rasterize', output,
            '--dimensions', DEFAULT_SHAPE[0], DEFAULT_SHAPE[1],
            '--bounds', bbox(0, 10, 10, 0)],
        input=json.dumps(basic_feature), catch_exceptions=False)

    assert result.exit_code == 0
    assert os.path.exists(output)

    coords = np.array(basic_feature['geometry']['coordinates']) + 2
    basic_feature['geometry']['coordinates'] = coords.tolist()

    result = runner.invoke(
        main_group, [
            'rasterize', '--overwrite', '-o', output, '--dimensions', DEFAULT_SHAPE[0],
            DEFAULT_SHAPE[1]],
        input=json.dumps(basic_feature))

    assert result.exit_code == 0

    with rasterio.open(output) as out:
        assert np.array_equal(truth, out.read(1, masked=False))


def test_rasterize_like_raster(tmpdir, runner, basic_feature, basic_image_2x2,
                               pixelated_image_file):

    output = str(tmpdir.join('test.tif'))

    result = runner.invoke(
        main_group,
        ['rasterize', output, '--like', pixelated_image_file],
        input=json.dumps(basic_feature))

    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert np.array_equal(basic_image_2x2, out.read(1, masked=False))

        with rasterio.open(pixelated_image_file) as src:
            assert out.crs == src.crs
            assert out.bounds == src.bounds
            assert out.transform == src.transform


def test_rasterize_invalid_like_raster(tmpdir, runner, basic_feature):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['rasterize', output, '--like', str(tmpdir.join('foo.tif'))],
        input=json.dumps(basic_feature))

    assert result.exit_code == 2
    assert 'Invalid value for "--like":' in result.output


def test_rasterize_like_raster_src_crs_mismatch(tmpdir, runner, basic_feature,
                                                pixelated_image_file):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['rasterize', output, '--like', pixelated_image_file, '--src-crs', 'EPSG:3857'],
        input=json.dumps(basic_feature))

    assert result.exit_code == 2
    assert 'GeoJSON does not match crs of --like raster' in result.output


def test_rasterize_featurecollection(tmpdir, runner, basic_feature,
                                     pixelated_image_file):
    output = str(tmpdir.join('test.tif'))
    collection = {
        'type': 'FeatureCollection',
        'features': [basic_feature]}
    result = runner.invoke(
        main_group,
        ['rasterize', output, '--like', pixelated_image_file],
        input=json.dumps(collection))
    assert result.exit_code == 0


def test_rasterize_src_crs_mismatch(tmpdir, runner, basic_feature,
                                    pixelated_image_file):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, ['rasterize', output, '--like', pixelated_image_file],
        input=json.dumps(basic_feature))
    assert result.exit_code == 0

    result = runner.invoke(
        main_group, [
            'rasterize', output, '--overwrite', '--src-crs', 'EPSG:3857'],
        input=json.dumps(basic_feature))
    assert result.exit_code == 2
    assert 'GeoJSON does not match crs of existing output raster' in result.output


def test_rasterize_property_value(tmpdir, runner, basic_feature):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, [
            'rasterize', output, '--dimensions', DEFAULT_SHAPE[0],
            DEFAULT_SHAPE[1], '--property', 'val'],
        input=json.dumps(basic_feature))

    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert np.allclose(out.bounds, (2, 2, 4.25, 4.25))
        data = out.read(1, masked=False)
        assert data.shape == DEFAULT_SHAPE
        assert np.all(data == basic_feature['properties']['val'])


def test_rasterize_like_raster_outside_bounds(tmpdir, runner, basic_feature,
                                              pixelated_image_file):
    """
    Rasterizing a feature outside bounds of --like raster should result
    in a blank image
    """

    coords = np.array(basic_feature['geometry']['coordinates']) + 100
    basic_feature['geometry']['coordinates'] = coords.tolist()

    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['rasterize', output, '--like', pixelated_image_file],
        input=json.dumps(basic_feature))

    assert result.exit_code == 0
    assert 'outside bounds' in result.output
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert not np.any(out.read(1, masked=False))


def test_rasterize_invalid_stdin(tmpdir, runner):
    """ Invalid value for stdin should fail with exception """

    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, ['rasterize', output], input='BOGUS')

    assert result.exit_code


def test_rasterize_invalid_geojson(tmpdir, runner):
    """ Invalid GeoJSON should fail with error  """
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, ['rasterize', output], input='{"A": "B"}')

    assert result.exit_code == 2
    assert 'Invalid GeoJSON' in result.output


def test_rasterize_missing_parameters(tmpdir, runner, basic_feature):
    """ At least --res or --dimensions are required """

    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['rasterize', '-o', output],
        input=json.dumps(basic_feature))

    assert result.exit_code == 2
    assert 'pixel dimensions are required' in result.output

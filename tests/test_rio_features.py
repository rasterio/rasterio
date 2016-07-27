import logging
import json
import os
import re
import sys
import warnings

from affine import Affine
import numpy as np

import rasterio
from rasterio.crs import CRS
from rasterio.rio.main import main_group

DEFAULT_SHAPE = (10, 10)

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_mask(runner, tmpdir, basic_feature, basic_image_2x2,
              pixelated_image_file):

    output = str(tmpdir.join('test.tif'))

    result = runner.invoke(
        main_group,
        ['mask', pixelated_image_file, output, '--geojson-mask', '-'],
        input=json.dumps(basic_feature)
    )

    assert result.exit_code == 0
    assert os.path.exists(output)

    with rasterio.open(output) as out:
        assert np.array_equal(
            basic_image_2x2,
            out.read(1, masked=True).filled(0)
        )


def test_mask_all_touched(runner, tmpdir, basic_feature, basic_image,
                          pixelated_image_file):

    output = str(tmpdir.join('test.tif'))

    result = runner.invoke(
        main_group, [
            'mask', pixelated_image_file, output, '--all', '--geojson-mask',
            '-'],
        input=json.dumps(basic_feature)
    )
    assert result.exit_code == 0
    assert os.path.exists(output)

    with rasterio.open(output) as out:
        assert np.array_equal(
            basic_image,
            out.read(1, masked=True).filled(0)
        )


def test_mask_invert(runner, tmpdir, basic_feature, pixelated_image,
                     pixelated_image_file):

    truth = pixelated_image
    truth[2:4, 2:4] = 0

    output = str(tmpdir.join('test.tif'))

    result = runner.invoke(
        main_group, [
            'mask', pixelated_image_file, output, '--invert', '--geojson-mask',
            '-'],
        input=json.dumps(basic_feature))
    assert result.exit_code == 0
    assert os.path.exists(output)

    with rasterio.open(output) as out:
        assert np.array_equal(
            truth,
            out.read(1, masked=True).filled(0))


def test_mask_featurecollection(runner, tmpdir, basic_featurecollection,
                                basic_image_2x2, pixelated_image_file):

    output = str(tmpdir.join('test.tif'))

    result = runner.invoke(
        main_group,
        ['mask', pixelated_image_file, output, '--geojson-mask', '-'],
        input=json.dumps(basic_featurecollection))
    assert result.exit_code == 0
    assert os.path.exists(output)

    with rasterio.open(output) as out:
        assert np.array_equal(
            basic_image_2x2,
            out.read(1, masked=True).filled(0))


def test_mask_out_of_bounds(runner, tmpdir, basic_feature,
                            pixelated_image_file):
    """
    A GeoJSON mask that is outside bounds of raster should result in a
    blank image.
    """

    coords = np.array(basic_feature['geometry']['coordinates']) - 10
    basic_feature['geometry']['coordinates'] = coords.tolist()

    output = str(tmpdir.join('test.tif'))

    result = runner.invoke(
        main_group,
        ['mask', pixelated_image_file, output, '--geojson-mask', '-'],
        input=json.dumps(basic_feature))
    assert result.exit_code == 0
    assert 'outside bounds' in result.output
    assert os.path.exists(output)

    with rasterio.open(output) as out:
        assert not np.any(out.read(1, masked=True).filled(0))


def test_mask_no_geojson(runner, tmpdir, pixelated_image, pixelated_image_file):
    """ Mask without geojson input should simply return same raster as input """

    output = str(tmpdir.join('test.tif'))

    result = runner.invoke(
        main_group,
        ['mask', pixelated_image_file, output])
    assert result.exit_code == 0
    assert os.path.exists(output)

    with rasterio.open(output) as out:
        assert np.array_equal(
            pixelated_image,
            out.read(1, masked=True).filled(0))


def test_mask_invalid_geojson(runner, tmpdir, pixelated_image_file):
    """ Invalid GeoJSON should fail """

    output = str(tmpdir.join('test.tif'))

    # Using invalid JSON
    result = runner.invoke(
        main_group,
        ['mask', pixelated_image_file, output, '--geojson-mask', '-'],
        input='{bogus: value}')
    assert result.exit_code == 2
    assert 'GeoJSON could not be read' in result.output

    # Using invalid GeoJSON
    result = runner.invoke(
        main_group,
        ['mask', pixelated_image_file, output, '--geojson-mask', '-'],
        input='{"bogus": "value"}')
    assert result.exit_code == 2
    assert 'Invalid GeoJSON' in result.output


def test_mask_crop(runner, tmpdir, basic_feature, pixelated_image):
    """
    In order to test --crop option, we need to use a transform more similar to
    a normal raster, with a negative y pixel size.
    """

    image = pixelated_image
    outfilename = str(tmpdir.join('pixelated_image.tif'))
    kwargs = {
        "crs": CRS({'init': 'epsg:4326'}),
        "transform": Affine(1, 0, 0, 0, -1, 0),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": image.shape[1],
        "height": image.shape[0],
        "nodata": 255}
    with rasterio.open(outfilename, 'w', **kwargs) as out:
        out.write(image, indexes=1)

    output = str(tmpdir.join('test.tif'))

    truth = np.zeros((4, 3))
    truth[1:3, 0:2] = 1

    result = runner.invoke(
        main_group,
        ['mask', outfilename, output, '--crop', '--geojson-mask', '-'],
        input=json.dumps(basic_feature))
    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert np.array_equal(
            truth,
            out.read(1, masked=True).filled(0))


def test_mask_crop_inverted_y(runner, tmpdir, basic_feature, pixelated_image_file):
    """
    --crop option should also work if raster has a positive y pixel size
    (e.g., Affine.identity() ).
    """

    output = str(tmpdir.join('test.tif'))

    truth = np.zeros((4, 3))
    truth[1:3, 0:2] = 1

    result = runner.invoke(
        main_group, [
            'mask', pixelated_image_file, output, '--crop',
            '--geojson-mask', '-'],
        input=json.dumps(basic_feature))

    assert result.exit_code == 0
    assert os.path.exists(output)
    with rasterio.open(output) as out:
        assert np.array_equal(
            truth,
            out.read(1, masked=True).filled(0))


def test_mask_crop_out_of_bounds(runner, tmpdir, basic_feature,
                                 pixelated_image_file):
    """
    A GeoJSON mask that is outside bounds of raster should fail with
    --crop option.
    """

    coords = np.array(basic_feature['geometry']['coordinates']) - 10
    basic_feature['geometry']['coordinates'] = coords.tolist()

    output = str(tmpdir.join('test.tif'))

    result = runner.invoke(
        main_group, [
            'mask', pixelated_image_file, output, '--crop',
            '--geojson-mask', '-'],
        input=json.dumps(basic_feature))
    assert result.exit_code == 2
    assert 'not allowed' in result.output


def test_mask_crop_and_invert(runner, tmpdir, basic_feature, pixelated_image,
                              pixelated_image_file):
    """ Adding crop and invert options should ignore invert option """

    output = str(tmpdir.join('test.tif'))

    result = runner.invoke(
        main_group,
        ['mask', pixelated_image_file, output, '--crop', '--invert',
         '--geojson-mask', '-'],
        input=json.dumps(basic_feature))
    assert result.exit_code == 0
    assert 'Invert option ignored' in result.output


def test_shapes(runner, pixelated_image_file):
    result = runner.invoke(main_group, ['shapes', pixelated_image_file])

    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 4
    assert np.allclose(
        json.loads(result.output)['features'][0]['geometry']['coordinates'],
        [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]])


def test_shapes_invalid_bidx(runner, pixelated_image_file):
    result = runner.invoke(
        main_group, ['shapes', pixelated_image_file, '--bidx', 4])

    assert result.exit_code == 1
    # Underlying exception message trapped by shapes


def test_shapes_sequence(runner, pixelated_image_file):
    """
    --sequence option should produce 4 features in series rather than
    inside a feature collection.
    """

    result = runner.invoke(
        main_group, ['shapes', pixelated_image_file, '--sequence'])

    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 0
    assert result.output.count('"Feature"') == 4
    assert result.output.count('\n') == 4


def test_shapes_sequence_rs(runner, pixelated_image_file):
    """ --rs option should use the feature separator character. """

    result = runner.invoke(
        main_group, ['shapes', pixelated_image_file, '--sequence', '--rs'])

    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 0
    assert result.output.count('"Feature"') == 4
    assert result.output.count(u'\u001e') == 4


def test_shapes_with_nodata(runner, pixelated_image, pixelated_image_file):
    """
    An area of nodata should also be represented with a shape when using
    --with-nodata option
    """

    pixelated_image[0:2, 8:10] = 255

    with rasterio.open(pixelated_image_file, 'r+') as out:
        out.write(pixelated_image, indexes=1)

    result = runner.invoke(
        main_group, ['shapes', pixelated_image_file, '--with-nodata'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 5


def test_shapes_indent(runner, pixelated_image_file):
    """
    --indent option should produce lots of newlines and contiguous spaces
    """

    result = runner.invoke(
        main_group, ['shapes', pixelated_image_file, '--indent', 2])

    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 4
    assert result.output.count('\n') == 231
    assert result.output.count('        ') == 180


def test_shapes_compact(runner, pixelated_image_file):
    result = runner.invoke(
        main_group, ['shapes', pixelated_image_file, '--compact'])

    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 4
    assert result.output.count(', ') == 0
    assert result.output.count(': ') == 0


def test_shapes_sampling(runner, pixelated_image_file):
    """ --sampling option should remove the single pixel features """
    result = runner.invoke(
        main_group, ['shapes', pixelated_image_file, '--sampling', 2])

    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 2


def test_shapes_precision(runner, pixelated_image_file):
    """ Output numbers should have no more than 1 decimal place """

    result = runner.invoke(
        main_group, ['shapes', pixelated_image_file, '--precision', 1])

    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 4
    assert re.search(r'\d*\.\d{2,}', result.output) is None


def test_shapes_mask(runner, pixelated_image, pixelated_image_file):
    """ --mask should extract the nodata area of the image """

    pixelated_image[0:5, 0:10] = 255
    pixelated_image[0:10, 0:3] = 255
    pixelated_image[8:10, 8:10] = 255

    with rasterio.open(pixelated_image_file, 'r+') as out:
        out.write(pixelated_image, indexes=1)

    result = runner.invoke(
        main_group, ['shapes', pixelated_image_file, '--mask'])

    print(result.output)
    print(result.exception)

    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 1

    assert np.allclose(
        json.loads(result.output)['features'][0]['geometry']['coordinates'],
        [[[3, 5], [3, 10], [8, 10], [8, 8], [9, 8], [10, 8], [10, 5], [3, 5]]])


def test_shapes_mask_sampling(runner, pixelated_image, pixelated_image_file):
    """
    using --sampling with the mask should snap coordinates to the nearest
    factor of 5
    """
    pixelated_image[0:5, 0:10] = 255
    pixelated_image[0:10, 0:3] = 255
    pixelated_image[8:10, 8:10] = 255

    with rasterio.open(pixelated_image_file, 'r+') as out:
        out.write(pixelated_image, indexes=1)

    result = runner.invoke(
        main_group,
        ['shapes', pixelated_image_file, '--mask', '--sampling', 5])

    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 1

    assert np.allclose(
        json.loads(result.output)['features'][0]['geometry']['coordinates'],
        [[[5, 5], [5, 10], [10, 10], [10, 5], [5, 5]]])


def test_shapes_band1_as_mask(runner, pixelated_image, pixelated_image_file):
    """
    When using --as-mask option, pixel value should not matter, only depends
    on pixels being contiguous.
    """

    pixelated_image[2:3, 2:3] = 4

    with rasterio.open(pixelated_image_file, 'r+') as out:
        out.write(pixelated_image, indexes=1)

    result = runner.invoke(
        main_group,
        ['shapes', pixelated_image_file, '--band', '--bidx', '1', '--as-mask'])

    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 3
    assert np.allclose(
        json.loads(result.output)['features'][1]['geometry']['coordinates'],
        [[[2, 2], [2, 5], [5, 5], [5, 2], [2, 2]]])


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


def test_rasterize_bounds(tmpdir, runner, basic_feature, basic_image_2x2):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, [
            'rasterize', output, '--dimensions', DEFAULT_SHAPE[0],
            DEFAULT_SHAPE[1], '--bounds', 0, 10, 10, 0],
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
        assert out.crs['init'].lower() == 'epsg:3857'


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
            '--bounds', 0, 10, 10, 0],
        input=json.dumps(basic_feature))

    assert result.exit_code == 0
    assert os.path.exists(output)

    coords = np.array(basic_feature['geometry']['coordinates']) + 2
    basic_feature['geometry']['coordinates'] = coords.tolist()

    result = runner.invoke(
        main_group, [
            'rasterize', '-o', output, '--dimensions', DEFAULT_SHAPE[0],
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
            'rasterize', output, '--force-overwrite', '--src-crs', 'EPSG:3857'],
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

    assert result.exit_code == -1


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

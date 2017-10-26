"""Tests for ``$ rio mask``."""


import json
import os

import affine
import numpy as np
from packaging.version import parse
import pytest

import rasterio
from rasterio.crs import CRS
from rasterio.rio.main import main_group


# Custom markers.
xfail_pixel_sensitive_gdal22 = pytest.mark.xfail(
    parse(rasterio.__gdal_version__) < parse('2.2'),
    reason="This test is sensitive to pixel values and requires GDAL 2.2+")


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

    with pytest.warns(UserWarning) as rec:
        result = runner.invoke(
            main_group,
            ['mask', pixelated_image_file, output, '--geojson-mask', '-'],
            input=json.dumps(basic_feature))
    assert result.exit_code == 0
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



@xfail_pixel_sensitive_gdal22
def test_mask_crop(runner, tmpdir, basic_feature, pixelated_image):
    """
    In order to test --crop option, we need to use a transform more similar to
    a normal raster, with a negative y pixel size.
    """

    image = pixelated_image
    outfilename = str(tmpdir.join('pixelated_image.tif'))
    kwargs = {
        "crs": CRS({'init': 'epsg:4326'}),
        "transform": affine.Affine(1, 0, 0, 0, -1, 0),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": image.shape[1],
        "height": image.shape[0],
        "nodata": 255}
    with rasterio.open(outfilename, 'w', **kwargs) as out:
        out.write(image, indexes=1)

    output = str(tmpdir.join('test.tif'))

    truth = np.zeros((3, 3))
    truth[0:2, 0:2] = 1

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


@xfail_pixel_sensitive_gdal22
def test_mask_crop_inverted_y(runner, tmpdir, basic_feature, pixelated_image_file):
    """
    --crop option should also work if raster has a positive y pixel size
    (e.g., Affine.identity() ).
    """

    output = str(tmpdir.join('test.tif'))

    truth = np.zeros((3, 3))
    truth[0:2, 0:2] = 1

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
    assert 'GeoJSON outside the extent' in result.output


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

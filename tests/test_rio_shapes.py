"""Tests for ``$ rio shapes``."""


import json
import re

import numpy as np
import pytest

import rasterio
from rasterio.rio.main import main_group


DEFAULT_SHAPE = (10, 10)


def bbox(*args):
    return ' '.join([str(x) for x in args])


def test_shapes(runner, pixelated_image_file):
    with pytest.warns(None):

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
    with pytest.warns(None):

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
    with pytest.warns(None):

        result = runner.invoke(
            main_group, ['shapes', pixelated_image_file, '--indent', 2])

        assert result.exit_code == 0
        assert result.output.count('"FeatureCollection"') == 1
        assert result.output.count('"Feature"') == 4
        assert result.output.count('\n') == 231
        assert result.output.count('        ') == 180


def test_shapes_compact(runner, pixelated_image_file):
    with pytest.warns(None):

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
    assert re.search(r'\s\d*\.\d{2,}', result.output) is None


def test_shapes_mask(runner, pixelated_image, pixelated_image_file):
    """ --mask should extract the nodata area of the image """

    pixelated_image[0:5, 0:10] = 255
    pixelated_image[0:10, 0:3] = 255
    pixelated_image[8:10, 8:10] = 255

    with rasterio.open(pixelated_image_file, 'r+') as out:
        out.write(pixelated_image, indexes=1)

    with pytest.warns(None):
        result = runner.invoke(
            main_group, ['shapes', pixelated_image_file, '--mask'])
        assert result.exit_code == 0
        assert result.output.count('"FeatureCollection"') == 1
        assert result.output.count('"Feature"') == 1
        assert np.allclose(
            json.loads(result.output)['features'][0]['geometry']['coordinates'],
            [[[3, 5], [3, 10], [8, 10], [8, 8], [9, 8], [10, 8], [10, 5], [3, 5]]])


def test_shapes_mask_sampling(runner, pixelated_image, pixelated_image_file):
    """using --sampling with the mask should snap coordinates to the nearest
    factor of 5
    """
    pixelated_image[0:5, 0:10] = 255
    pixelated_image[0:10, 0:3] = 255
    pixelated_image[8:10, 8:10] = 255

    with rasterio.open(pixelated_image_file, 'r+') as out:
        out.write(pixelated_image, indexes=1)

    with pytest.warns(None):

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

    with pytest.warns(None):
        result = runner.invoke(
            main_group,
            ['shapes', pixelated_image_file, '--band', '--bidx', '1', '--as-mask'])

        assert result.exit_code == 0
        assert result.output.count('"FeatureCollection"') == 1
        assert result.output.count('"Feature"') == 3
        assert np.allclose(
            json.loads(result.output)['features'][1]['geometry']['coordinates'],
            [[[2, 2], [2, 5], [5, 5], [5, 2], [2, 2]]])

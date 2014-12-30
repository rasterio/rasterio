import logging
import re
import sys

import click
from click.testing import CliRunner

from rasterio.rio import features


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_err():
    runner = CliRunner()
    result = runner.invoke(
        features.shapes, ['tests/data/shade.tif', '--bidx', '4'])
    assert result.exit_code == 1


def test_shapes():
    runner = CliRunner()
    result = runner.invoke(features.shapes, ['tests/data/shade.tif'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 232


def test_shapes_sequence():
    runner = CliRunner()
    result = runner.invoke(features.shapes, ['tests/data/shade.tif', '--sequence'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 0
    assert result.output.count('"Feature"') == 232


def test_shapes_sequence_rs():
    runner = CliRunner()
    result = runner.invoke(
        features.shapes, [
            'tests/data/shade.tif',
            '--sequence',
            '--rs'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 0
    assert result.output.count('"Feature"') == 232
    assert result.output.count(u'\u001e') == 232


def test_shapes_with_nodata():
    runner = CliRunner()
    result = runner.invoke(features.shapes, ['tests/data/shade.tif', '--with-nodata'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 288


def test_shapes_indent():
    runner = CliRunner()
    result = runner.invoke(features.shapes, ['tests/data/shade.tif', '--indent', '2'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('\n') == 70139


def test_shapes_compact():
    runner = CliRunner()
    result = runner.invoke(features.shapes, ['tests/data/shade.tif', '--compact'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count(', ') == 0
    assert result.output.count(': ') == 0


def test_shapes_sampling():
    runner = CliRunner()
    result = runner.invoke(
        features.shapes, ['tests/data/shade.tif', '--sampling', '10'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 124


def test_shapes_precision():
    runner = CliRunner()
    result = runner.invoke(
        features.shapes, ['tests/data/shade.tif', '--precision', '1'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    # Find no numbers with 2+ decimal places.
    assert re.search(r'\d*\.\d{2,}', result.output) is None


def test_shapes_mask():
    runner = CliRunner()
    result = runner.invoke(features.shapes, ['tests/data/RGB.byte.tif', '--mask'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 9

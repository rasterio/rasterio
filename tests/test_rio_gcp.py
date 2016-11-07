import json
import logging
import sys

from click.testing import CliRunner
import pytest

from rasterio.rio.main import main_group


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_feature_seq():
    """GeoJSON sequence w/out RS is the default"""
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['gcps', 'tests/data/white-gemini-iv.vrt'])
    assert result.exit_code == 0
    assert result.output.count('"Feature"') == 3
    assert '-78' in result.output

def test_collection():
    """GeoJSON collections can be had, optionally"""
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['gcps', 'tests/data/white-gemini-iv.vrt', '--collection'])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert '-78' in result.output


def test_feature_seq_indent_rs():
    """Indentation of a feature sequence succeeds with ascii RS option"""
    runner = CliRunner()
    result = runner.invoke(
        main_group,
        ['gcps', 'tests/data/white-gemini-iv.vrt', '--indent', '2', '--rs'])
    assert result.exit_code == 0


def test_feature_seq_indent_no_rs():
    """Indentation of a feature sequence fails without ascii RS option"""
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['gcps', 'tests/data/white-gemini-iv.vrt', '--indent', '2'])
    assert result.exit_code == 2


def test_projected():
    """Projected GeoJSON is an option"""
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['gcps', 'tests/data/white-gemini-iv.vrt', '--projected'])
    assert result.exit_code == 0
    assert '-78' not in result.output


def test_feature_precision():
    """Coordinate rounding is an option"""
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['gcps', 'tests/data/white-gemini-iv.vrt', '--projected', '--precision', '1'])
    assert result.exit_code == 0
    assert '116792.0,' in result.output


def test_collection_precision():
    """Coordinate rounding is an option"""
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['gcps', 'tests/data/white-gemini-iv.vrt', '--collection', '--projected', '--precision', '1'])
    assert result.exit_code == 0
    assert '"FeatureCollection"' in result.output
    assert '116792.0,' in result.output


def test_collection_geographic_precision():
    """Unrounded coordinates are an option"""
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['gcps', 'tests/data/white-gemini-iv.vrt', '--collection', '--projected'])
    assert result.exit_code == 0
    assert '"FeatureCollection"' in result.output
    assert '116792.0,' in result.output

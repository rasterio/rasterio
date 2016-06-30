"""Unittests for $ rio blocks"""


import itertools as it
import json
import os
import re

import numpy as np
import six

import rasterio
from rasterio.warp import transform_bounds
from rasterio.rio.main import main_group


def check_features_block_windows(features, src, bidx):

    """Compare GeoJSON features to a datasource's blocks + windows.

    Parameters
    ----------
    features : iter
        GeoJSON features.
    src : RasterReader
        Open input datasource.
    """

    out = []
    iterator = six.moves.zip_longest(features, src.block_windows(bidx=bidx))
    for feat, (block, window) in iterator:

        out.append(np.array_equal(
            json.loads(feat['properties']['block']),
            block))

        out.append(np.array_equal(
            json.loads(feat['properties']['window']),
            window))

    return all(out)


def test_windows(runner, path_rgb_byte_tif):
    result = runner.invoke(main_group, [
        'blocks', path_rgb_byte_tif])
    assert result.exit_code == 0

    fc = json.loads(result.output)

    with rasterio.open(path_rgb_byte_tif) as src:
        num_windows = len(tuple(src.block_windows()))
        assert len(fc['features']) == num_windows
        assert check_features_block_windows(fc['features'], src, bidx=1)


def test_windows_sequence(runner, path_rgb_byte_tif):
    result = runner.invoke(main_group, [
        'blocks',
        path_rgb_byte_tif,
        '--sequence'])
    assert result.exit_code == 0

    features = map(json.loads, result.output.splitlines())

    with rasterio.open(path_rgb_byte_tif) as src:
        assert check_features_block_windows(features, src, bidx=1)


def test_windows_precision(runner, path_rgb_byte_tif):
    result = runner.invoke(main_group, [
        'blocks',
        path_rgb_byte_tif,
        '--precision', 1])
    assert result.exit_code == 0
    assert result.output.count('"FeatureCollection"') == 1
    assert result.output.count('"Feature"') == 240
    assert re.search(r'\d*\.\d{2,}', result.output) is None


def test_windows_indent(runner, path_rgb_byte_tif):
    result = runner.invoke(main_group, [
        'blocks',
        path_rgb_byte_tif,
        '--indent', 4])
    assert result.exit_code == 0

    lines = result.output.splitlines()
    assert result.output.count('"FeatureCollection') == 1
    assert result.output.count('"Feature"') == 240
    assert len(lines) == 7451
    for l in lines:
        if l.strip() not in ('{', '}'):
            assert '    ' in l


def test_windows_compact(runner, path_rgb_byte_tif):
    result = runner.invoke(main_group, [
        'blocks',
        path_rgb_byte_tif,
        '--compact'])
    assert result.exit_code == 0

    assert result.output.count('"FeatureCollection') == 1
    assert result.output.count('"Feature"') == 240
    assert result.output.count('", "') == 0
    assert result.output.count(': ') == 0


def test_windows_exception(runner, path_rgb_byte_tif):
    """Tests the try/except that wraps the command logic.  The input file does
    not have 4 bands.
    """
    result = runner.invoke(main_group, [
        'blocks',
        path_rgb_byte_tif,
        '--bidx', 4])
    assert result.exit_code == 1


def test_windows_projected(runner, path_rgb_byte_tif):
    result = runner.invoke(main_group, [
        'blocks',
        path_rgb_byte_tif,
        '--projected'])
    assert result.exit_code == 0

    fc = json.loads(result.output)

    with rasterio.open(path_rgb_byte_tif) as src:
        assert np.array_equal(fc['bbox'], src.bounds)
        assert check_features_block_windows(fc['features'], src, bidx=1)

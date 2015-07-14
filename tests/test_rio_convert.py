import sys
import os
import logging
import click
from click.testing import CliRunner

import rasterio
from rasterio.rio.translate import convert


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


# Tests: format and type conversion, --format and --dtype

def test_format(tmpdir):
    outputname = str(tmpdir.join('test.jpg'))
    runner = CliRunner()
    result = runner.invoke(
        convert,
        ['tests/data/RGB.byte.tif', outputname, '--format', 'JPEG'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        assert src.driver == 'JPEG'


def test_format_short(tmpdir):
    outputname = str(tmpdir.join('test.jpg'))
    runner = CliRunner()
    result = runner.invoke(
        convert,
        ['tests/data/RGB.byte.tif', outputname, '-f', 'JPEG'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        assert src.driver == 'JPEG'


def test_output_opt(tmpdir):
    outputname = str(tmpdir.join('test.jpg'))
    runner = CliRunner()
    result = runner.invoke(
        convert,
        ['tests/data/RGB.byte.tif', '-o', outputname, '-f', 'JPEG'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        assert src.driver == 'JPEG'


def test_dtype(tmpdir):
    outputname = str(tmpdir.join('test.tif'))
    runner = CliRunner()
    result = runner.invoke(
        convert,
        ['tests/data/RGB.byte.tif', outputname, '--dtype', 'uint16'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        assert src.dtypes == ['uint16']*3


def test_dtype_rescaling_uint8_full(tmpdir):
    outputname = str(tmpdir.join('test.tif'))
    runner = CliRunner()
    result = runner.invoke(
        convert,
        ['tests/data/RGB.byte.tif', outputname, '--scale-linear'])
    assert result.exit_code == 0

    src_stats = [
        {"max": 255.0, "mean": 44.434478650699106, "min": 1.0},
        {"max": 255.0, "mean": 66.02203484105824, "min": 1.0},
        {"max": 255.0, "mean": 71.39316199120559, "min": 1.0}]

    with rasterio.open(outputname) as src:
        for band, expected in zip(src.read(masked=True), src_stats):
            assert round(band.min() - expected['min'], 6) == 0.0
            assert round(band.max() - expected['max'], 6) == 0.0
            assert round(band.mean() - expected['mean'], 6) == 0.0


def test_dtype_rescaling_uint8_half(tmpdir):
    outputname = str(tmpdir.join('test.tif'))
    runner = CliRunner()
    result = runner.invoke(convert, [
        'tests/data/RGB.byte.tif', outputname, '--scale-linear',
        '--dst-scale-points', '0', '127'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        for band in src.read(masked=True):
            assert round(band.min() - 1, 6) == 0.0
            assert round(band.max() - 127, 6) == 0.0


def test_dtype_rescaling_uint16(tmpdir):
    outputname = str(tmpdir.join('test.tif'))
    runner = CliRunner()
    result = runner.invoke(convert, [
        'tests/data/RGB.byte.tif', outputname, '--dtype', 'uint16',
        '--scale-linear', '--dst-scale-points', '0', '10000'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        for band in src.read(masked=True):
            assert round(band.min() - 39, 6) == 0.0
            assert round(band.max() - 10000, 6) == 0.0

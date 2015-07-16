import sys
import os
import logging
import click
from click.testing import CliRunner

import rasterio
from rasterio.rio.convert import convert


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
    """Rescale uint8 [0, 255] to uint8 [0, 255]"""
    outputname = str(tmpdir.join('test.tif'))
    runner = CliRunner()
    result = runner.invoke(
        convert,
        ['tests/data/RGB.byte.tif', outputname, '--scale-ratio', '1.0'])
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
    """Rescale uint8 [0, 255] to uint8 [0, 127]"""
    outputname = str(tmpdir.join('test.tif'))
    runner = CliRunner()
    result = runner.invoke(convert, [
        'tests/data/RGB.byte.tif', outputname, '--scale-ratio', '0.5'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        for band in src.read():
            assert round(band.min() - 0, 6) == 0.0
            assert round(band.max() - 127, 6) == 0.0


def test_dtype_rescaling_uint16(tmpdir):
    """Rescale uint8 [0, 255] to uint16 [0, 4095]"""
    # NB: 255 * 16 is 4080, we don't actually get to 4095.
    outputname = str(tmpdir.join('test.tif'))
    runner = CliRunner()
    result = runner.invoke(convert, [
        'tests/data/RGB.byte.tif', outputname, '--dtype', 'uint16',
        '--scale-ratio', '16'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        for band in src.read():
            assert round(band.min() - 0, 6) == 0.0
            assert round(band.max() - 4080, 6) == 0.0


def test_dtype_rescaling_float64(tmpdir):
    """Rescale uint8 [0, 255] to float64 [-1, 1]"""
    outputname = str(tmpdir.join('test.tif'))
    runner = CliRunner()
    result = runner.invoke(convert, [
        'tests/data/RGB.byte.tif', outputname, '--dtype', 'float64',
        '--scale-ratio', str(2.0/255), '--scale-offset', '-1.0'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        for band in src.read():
            assert round(band.min() + 1.0, 6) == 0.0
            assert round(band.max() - 1.0, 6) == 0.0

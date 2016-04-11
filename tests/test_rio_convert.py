import sys
import os
import logging
import numpy
from click.testing import CliRunner

import rasterio
from rasterio.rio.main import main_group
from rasterio.rio.convert import convert


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

TEST_BBOX = [-11850000, 4804000, -11840000, 4808000]


def test_clip_bounds(runner, tmpdir):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['clip', 'tests/data/shade.tif', output, '--bounds'] + TEST_BBOX)
    assert result.exit_code == 0
    assert os.path.exists(output)

    with rasterio.open(output) as out:
        assert out.shape == (420, 173)


def test_clip_like(runner, tmpdir):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, [
            'clip', 'tests/data/shade.tif', output, '--like',
            'tests/data/shade.tif'])
    assert result.exit_code == 0
    assert os.path.exists(output)

    with rasterio.open('tests/data/shade.tif') as template_ds:
        with rasterio.open(output) as out:
            assert out.shape == template_ds.shape
            assert numpy.allclose(out.bounds, template_ds.bounds)


def test_clip_missing_params(runner, tmpdir):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, ['clip', 'tests/data/shade.tif', output])
    assert result.exit_code == 2
    assert '--bounds or --like required' in result.output


def test_clip_bounds_disjunct(runner, tmpdir):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group,
        ['clip', 'tests/data/shade.tif', output, '--bounds'] + [0, 0, 10, 10])
    assert result.exit_code == 2
    assert '--bounds' in result.output


def test_clip_like_disjunct(runner, tmpdir):
    output = str(tmpdir.join('test.tif'))
    result = runner.invoke(
        main_group, [
            'clip', 'tests/data/shade.tif', output, '--like',
            'tests/data/RGB.byte.tif'])
    assert result.exit_code == 2
    assert '--like' in result.output


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
        assert src.dtypes == tuple(['uint16'] * 3)


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
        '--scale-ratio', str(2.0 / 255), '--scale-offset', '-1.0'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        for band in src.read():
            assert round(band.min() + 1.0, 6) == 0.0
            assert round(band.max() - 1.0, 6) == 0.0


def test_rgb(tmpdir):
    outputname = str(tmpdir.join('test.tif'))
    runner = CliRunner()
    result = runner.invoke(
        convert,
        ['tests/data/RGB.byte.tif', outputname, '--rgb'])
    assert result.exit_code == 0
    with rasterio.open(outputname) as src:
        assert src.colorinterp(1) == rasterio.enums.ColorInterp.red

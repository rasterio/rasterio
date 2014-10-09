import click
from click.testing import CliRunner

import rasterio
from rasterio.rio import bands


def test_photometic_choices():
    assert len(bands.PHOTOMETRIC_CHOICES) == 8


def test_stack(tmpdir):
    outputname = str(tmpdir.join('stacked.tif'))
    runner = CliRunner()
    result = runner.invoke(
        bands.stack,
        ['tests/data/RGB.byte.tif', '-o', outputname],
        catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outputname) as out:
        assert out.count == 3


def test_stack_list(tmpdir):
    outputname = str(tmpdir.join('stacked.tif'))
    runner = CliRunner()
    result = runner.invoke(
        bands.stack,
        ['tests/data/RGB.byte.tif', '--bidx', '1,2,3', '-o', outputname])
    assert result.exit_code == 0
    with rasterio.open(outputname) as out:
        assert out.count == 3


def test_stack_slice(tmpdir):
    outputname = str(tmpdir.join('stacked.tif'))
    runner = CliRunner()
    result = runner.invoke(
        bands.stack, 
        [
            'tests/data/RGB.byte.tif', '--bidx', '..2',
            'tests/data/RGB.byte.tif', '--bidx', '3..',
            '-o', outputname])
    assert result.exit_code == 0
    with rasterio.open(outputname) as out:
        assert out.count == 3


def test_stack_single_slice(tmpdir):
    outputname = str(tmpdir.join('stacked.tif'))
    runner = CliRunner()
    result = runner.invoke(
        bands.stack, 
        [
            'tests/data/RGB.byte.tif', '--bidx', '1',
            'tests/data/RGB.byte.tif', '--bidx', '2..',
            '--photometric', 'rgb',
            '-o', outputname])
    assert result.exit_code == 0
    with rasterio.open(outputname) as out:
        assert out.count == 3


def test_error(tmpdir):
    outputname = str(tmpdir.join('stacked.tif'))
    runner = CliRunner()
    result = runner.invoke(
        bands.stack,
        ['tests/data/RGB.byte.tif', '-o', outputname, '--driver', 'BOGUS'])
    assert result.exit_code == 1

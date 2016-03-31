from click.testing import CliRunner

import rasterio
from rasterio.rio.stack import stack


def test_stack(tmpdir):
    outputname = str(tmpdir.join('stacked.tif'))
    runner = CliRunner()
    result = runner.invoke(
        stack,
        ['tests/data/RGB.byte.tif', outputname],
        catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outputname) as out:
        assert out.count == 3


def test_stack_list(tmpdir):
    outputname = str(tmpdir.join('stacked.tif'))
    runner = CliRunner()
    result = runner.invoke(
        stack,
        ['tests/data/RGB.byte.tif', '--bidx', '1,2,3', outputname])
    assert result.exit_code == 0
    with rasterio.open(outputname) as out:
        assert out.count == 3


def test_stack_slice(tmpdir):
    outputname = str(tmpdir.join('stacked.tif'))
    runner = CliRunner()
    result = runner.invoke(
        stack,
        [
            'tests/data/RGB.byte.tif', '--bidx', '..2',
            'tests/data/RGB.byte.tif', '--bidx', '3..',
            outputname])
    assert result.exit_code == 0
    with rasterio.open(outputname) as out:
        assert out.count == 3


def test_stack_single_slice(tmpdir):
    outputname = str(tmpdir.join('stacked.tif'))
    runner = CliRunner()
    result = runner.invoke(
        stack,
        [
            'tests/data/RGB.byte.tif', '--bidx', '1',
            'tests/data/RGB.byte.tif', '--bidx', '2..',
            '--rgb',
            outputname])
    assert result.exit_code == 0
    with rasterio.open(outputname) as out:
        assert out.count == 3


def test_format_jpeg(tmpdir):
    outputname = str(tmpdir.join('stacked.jpg'))
    runner = CliRunner()
    result = runner.invoke(
        stack,
        ['tests/data/RGB.byte.tif', outputname, '--format', 'JPEG'])
    assert result.exit_code == 0


def test_error(tmpdir):
    outputname = str(tmpdir.join('stacked.tif'))
    runner = CliRunner()
    result = runner.invoke(
        stack,
        ['tests/data/RGB.byte.tif', outputname, '--driver', 'BOGUS'])
    assert result.exit_code == 1

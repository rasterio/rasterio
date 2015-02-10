import sys
import logging

from click.testing import CliRunner

import rasterio
from rasterio.rio.calc import calc


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_err(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                '0.10*{1}.upper()', 'tests/data/shade.tif', outfile],
                catch_exceptions=False)
    assert result.exit_code == 1


def test_multiband_calc(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                '0.10*{1} + 125', 'tests/data/shade.tif', outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 1
        assert src.meta['dtype'] == 'float64'
        data = src.read()
        assert data.min() == 125


def test_singleband_calc(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                '0.10*{1,1} + 125', 'tests/data/shade.tif', outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 1
        assert src.meta['dtype'] == 'float64'
        data = src.read()
        assert data.min() == 125


def test_singleband_calc_by_name(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '0.10*{tests/data/shade.tif,1} + 125',
                    'tests/data/shade.tif', 
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 1
        assert src.meta['dtype'] == 'float64'
        data = src.read()
        assert data.min() == 125


def test_parts_calc(tmpdir):
    # Producing an RGB output from the hill shade.
    # Red band has bumped up values. Other bands are unchanged.
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '({1,1} + 125, {1,1}, {1,1})',
                    '--dtype', 'uint8',
                    'tests/data/shade.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 3
        assert src.meta['dtype'] == 'uint8'
        data = src.read()
        assert data[0].min() == 125
        assert data[1].min() == 0
        assert data[2].min() == 0


def test_parts_calc_2(tmpdir):
    # Produce greyscale output from the RGB file.
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '({1,1} + {1,2} + {1,3})/3',
                    '--dtype', 'uint8',
                    'tests/data/RGB.byte.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 1
        assert src.meta['dtype'] == 'uint8'
        data = src.read()
        assert round(data.mean(), 1) == 60.3


def test_parts_calc_tempval(tmpdir):
    # Produce greyscale output from the RGB file.
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '{1,1}; {} + {1,2}; {} + {1,3}; {}; ({}/3)',
                    '--dtype', 'uint8',
                    'tests/data/RGB.byte.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 1
        assert src.meta['dtype'] == 'uint8'
        data = src.read()
        assert round(data.mean(), 1) == 60.3



def test_copy_rgb(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '{1}',
                    '--dtype', 'uint8',
                    'tests/data/RGB.byte.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 3
        assert src.meta['dtype'] == 'uint8'
        data = src.read()
        assert round(data.mean(), 1) == 60.6


def test_copy_rgb_tempval(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '{1}; {}',
                    '--dtype', 'uint8',
                    'tests/data/RGB.byte.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 3
        assert src.meta['dtype'] == 'uint8'
        data = src.read()
        assert round(data.mean(), 1) == 60.6


def test_copy_rgb_by_name(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '{tests/data/RGB.byte.tif}',
                    '--dtype', 'uint8',
                    'tests/data/RGB.byte.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 3
        assert src.meta['dtype'] == 'uint8'
        data = src.read()
        assert round(data.mean(), 1) == 60.6

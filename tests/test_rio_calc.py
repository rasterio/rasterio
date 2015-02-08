import sys
import logging

from click.testing import CliRunner

import rasterio
from rasterio.rio.calc import calc


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_multiband_calc(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                '0.10*{1} + 125', 'tests/data/shade.tif', outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.meta['dtype'] == 'float64'
        data = src.read()
        assert data.min() == 125


def test_singleband_calc(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                '0.10*{1,1} + 125;', 'tests/data/shade.tif', outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.meta['dtype'] == 'float64'
        data = src.read()
        assert data.min() == 125


def test_parts_calc(tmpdir):
    # Producing an RGB output from the hill shade.
    # Red band has bumped up values. Other bands are unchanged.
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '{1,1} + 125; {1,1}; {1,1}',
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

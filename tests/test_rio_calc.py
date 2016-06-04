import logging
import sys

from click.testing import CliRunner

import rasterio
from rasterio.rio.calc import calc

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_err(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                '($ 0.1 (read 1))', 'tests/data/shade.tif', outfile],
                catch_exceptions=False)
    assert result.exit_code == 1


def test_multiband_calc(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                '(+ 125 (* 0.1 (read 1)))', 'tests/data/shade.tif', outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 1
        assert src.meta['dtype'] == 'uint8'
        data = src.read(masked=True)
        assert data.min() == 125
        assert data.data[0][0][0] == 255
        assert data.mask[0][0][0]


def test_singleband_calc_byindex(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '(+ 125 (* 0.1 (read 1 1)))',
                    'tests/data/shade.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 1
        assert src.meta['dtype'] == 'uint8'
        data = src.read(masked=True)
        assert data.min() == 125


def test_singleband_calc_byname(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '(+ 125 (* 0.1 (take shade 1)))',
                    '--name', 'shade=tests/data/shade.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 1
        assert src.meta['dtype'] == 'uint8'
        data = src.read(masked=True)
        assert data.min() == 125


def test_parts_calc(tmpdir):
    # Producing an RGB output from the hill shade.
    # Red band has bumped up values. Other bands are unchanged.
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '(asarray (+ (read 1 1) 125) (read 1 1) (read 1 1))',
                    'tests/data/shade.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 3
        assert src.meta['dtype'] == 'uint8'
        data = src.read(masked=True)
        assert data[0].min() == 125
        assert data[1].min() == 0
        assert data[2].min() == 0


def test_parts_calc_2(tmpdir):
    # Produce greyscale output from the RGB file.
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '(+ (+ (/ (read 1 1) 3.0) (/ (read 1 2) 3.0)) (/ (read 1 3) 3.0))',
                    'tests/data/RGB.byte.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 1
        assert src.meta['dtype'] == 'uint8'
        data = src.read(masked=True)
        assert round(data.mean(), 1) == 60.3


def test_copy_rgb(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '(read 1)',
                    'tests/data/RGB.byte.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 3
        assert src.meta['dtype'] == 'uint8'
        data = src.read(masked=True)
        assert round(data.mean(), 1) == 60.6


def test_fillnodata(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '(asarray (fillnodata (read 1 1)) (fillnodata (read 1 2)) (fillnodata (read 1 3)))',
                    'tests/data/RGB.byte.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 3
        assert src.meta['dtype'] == 'uint8'
        data = src.read(masked=True)
        assert round(data.mean(), 1) == 60.6


def test_fillnodata_map(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '(asarray (map fillnodata (read 1)))',
                    'tests/data/RGB.byte.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 3
        assert src.meta['dtype'] == 'uint8'
        data = src.read(masked=True)
        assert round(data.mean(), 1) == 60.6


def test_sieve_band(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    '(sieve (band 1 1) 42)',
                    'tests/data/shade.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 1
        assert src.meta['dtype'] == 'uint8'


def test_sieve_read(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(calc, [
                    "(sieve (read 1 1 'uint8') 42)",
                    'tests/data/shade.tif',
                    outfile],
                catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 1
        assert src.meta['dtype'] == 'uint8'

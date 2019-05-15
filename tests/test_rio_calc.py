from click.testing import CliRunner
import pytest

import rasterio
from rasterio.rio.calc import _get_work_windows
from rasterio.rio.main import main_group


def test_err(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(main_group, ['calc'] + [
        '($ 0.1 (read 1))', 'tests/data/shade.tif', outfile],
        catch_exceptions=False)
    assert result.exit_code == 1


def test_multiband_calc(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(main_group, ['calc'] + [
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
    result = runner.invoke(main_group, ['calc'] + [
        '(+ 125 (* 0.1 (read 1 1)))', 'tests/data/shade.tif', outfile],
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
    result = runner.invoke(main_group, ['calc'] + [
        '(+ 125 (* 0.1 (take shade 1)))', '--name', 'shade=tests/data/shade.tif',
        outfile], catch_exceptions=False)
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
    result = runner.invoke(main_group, ['calc'] + [
        '(asarray (+ (read 1 1) 125) (read 1 1) (read 1 1))',
        'tests/data/shade.tif', outfile], catch_exceptions=False)
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
    result = runner.invoke(main_group, ['calc'] + [
        '(+ (+ (/ (read 1 1) 3.0) (/ (read 1 2) 3.0)) (/ (read 1 3) 3.0))',
        'tests/data/RGB.byte.tif', outfile], catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 1
        assert src.meta['dtype'] == 'uint8'
        data = src.read(masked=True)
        assert round(data.mean(), 1) == 60.3


def test_copy_rgb(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(main_group, ['calc'] + [
        '(read 1)', 'tests/data/RGB.byte.tif', outfile],
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
    result = runner.invoke(main_group, ['calc'] + [
        '(asarray (fillnodata (read 1 1)) (fillnodata (read 1 2)) (fillnodata (read 1 3)))',
        'tests/data/RGB.byte.tif', outfile], catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 3
        assert src.meta['dtype'] == 'uint8'
        data = src.read(masked=True)
        assert round(data.mean(), 1) == 58.6


def test_fillnodata_map(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(main_group, ['calc'] + [
        '(asarray (map fillnodata (read 1)))',
        'tests/data/RGB.byte.tif', outfile], catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 3
        assert src.meta['dtype'] == 'uint8'
        data = src.read(masked=True)
        assert round(data.mean(), 1) == 58.6
        assert data[0][60][60] > 0


def test_sieve_band(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(main_group, ['calc'] + [
        '(sieve (band 1 1) 42)', 'tests/data/shade.tif', outfile],
        catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 1
        assert src.meta['dtype'] == 'uint8'


def test_sieve_read(tmpdir):
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(main_group, ['calc'] + [
        "(sieve (read 1 1 'uint8') 42)",
        'tests/data/shade.tif', outfile], catch_exceptions=False)
    assert result.exit_code == 0
    with rasterio.open(outfile) as src:
        assert src.count == 1
        assert src.meta['dtype'] == 'uint8'


def test_positional_calculation_byindex(tmpdir):
    # See Issue 947: https://github.com/mapbox/rasterio/issues/947
    # Prior to fix, 'shade.tif' reliably is read as 2nd input and
    # we should expect this to fail due to array shape error
    # ("operands could not be broadcast together")
    outfile = str(tmpdir.join('out.tif'))
    runner = CliRunner()
    result = runner.invoke(main_group, ['calc'] + [
        '(- (read 1 1) (read 2 2))',
        'tests/data/RGB.byte.tif',
        'tests/data/RGB.byte.tif',
        'tests/data/shade.tif',
        outfile], catch_exceptions=False)
    assert result.exit_code == 0

    window = ((0, 1), (0, 1))
    with rasterio.open('tests/data/RGB.byte.tif') as rgb:
        answer = rgb.read(1, window=window) - rgb.read(1, window=window)

    with rasterio.open(outfile) as src:
        assert src.read(1, window=window) == answer


@pytest.mark.parametrize('width', [10, 791, 3000])
@pytest.mark.parametrize('height', [8, 718, 4000])
@pytest.mark.parametrize('count', [1, 3, 4])
@pytest.mark.parametrize('itemsize', [1, 2, 8])
@pytest.mark.parametrize('mem_limit', [1, 16, 64, 512])
def test_get_work_windows(width, height, count, itemsize, mem_limit):
    work_windows = _get_work_windows(width, height, count, itemsize, mem_limit=mem_limit)
    num_windows_rows = max(i for ((i, j), w) in work_windows) + 1
    num_windows_cols = max(j for ((i, j), w) in work_windows) + 1
    assert sum((w.width for ij, w in work_windows)) == width * num_windows_rows
    assert sum((w.height for ij, w in work_windows)) == height * num_windows_cols

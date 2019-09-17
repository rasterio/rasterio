import logging
import sys

from click.testing import CliRunner

import rasterio
from rasterio.rio.main import main_group as cli
from rasterio.rio.overview import get_maximum_overview_level


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_err(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(cli, ['overview', inputfile, '--build', 'a^2'])
    assert result.exit_code == 2
    assert "must match" in result.output


def test_ls_none(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(cli, ['overview', inputfile, '--ls'])
    assert result.exit_code == 0
    expected = "Overview factors:\n  Band 1: None (method: 'unknown')\n  Band 2: None (method: 'unknown')\n  Band 3: None (method: 'unknown')\n"
    assert result.output == expected


def test_build_ls(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(cli, ['overview', inputfile, '--build', '2,4,8'])
    assert result.exit_code == 0
    result = runner.invoke(cli, ['overview', inputfile, '--ls'])
    assert result.exit_code == 0
    expected = "  Band 1: [2, 4, 8] (method: 'nearest')\n  Band 2: [2, 4, 8] (method: 'nearest')\n  Band 3: [2, 4, 8] (method: 'nearest')\n"
    assert result.output.endswith(expected)


def test_build_pow_ls(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(cli, ['overview', inputfile, '--build', '2^1..3'])
    assert result.exit_code == 0
    result = runner.invoke(cli, ['overview', inputfile, '--ls'])
    assert result.exit_code == 0
    expected = "  Band 1: [2, 4, 8] (method: 'nearest')\n  Band 2: [2, 4, 8] (method: 'nearest')\n  Band 3: [2, 4, 8] (method: 'nearest')\n"
    assert result.output.endswith(expected)


def test_rebuild_ls(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))

    result = runner.invoke(
        cli,
        ['overview', inputfile, '--build', '2,4,8', '--resampling', 'cubic'])
    assert result.exit_code == 0

    result = runner.invoke(cli, ['overview', inputfile, '--rebuild'])
    assert result.exit_code == 0

    result = runner.invoke(cli, ['overview', inputfile, '--ls'])
    assert result.exit_code == 0

    expected = "  Band 1: [2, 4, 8] (method: 'cubic')\n  Band 2: [2, 4, 8] (method: 'cubic')\n  Band 3: [2, 4, 8] (method: 'cubic')\n"
    assert result.output.endswith(expected)


def test_no_args(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(cli, ['overview', inputfile])
    assert result.exit_code == 2


def test_build_auto_ls(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(cli, ['overview', inputfile, '--build', 'auto'])
    assert result.exit_code == 0
    result = runner.invoke(cli, ['overview', inputfile, '--ls'])
    assert result.exit_code == 0
    expected = "  Band 1: [2, 4] (method: 'nearest')\n  Band 2: [2, 4] (method: 'nearest')\n  Band 3: [2, 4] (method: 'nearest')\n"
    assert result.output.endswith(expected)


def test_max_overview(data):
    inputfile = str(data.join('RGB.byte.tif'))

    with rasterio.open(inputfile) as src:
        overview_level = get_maximum_overview_level(src)
    assert overview_level == 2

    with rasterio.open(inputfile) as src:
        overview_level = get_maximum_overview_level(src, minsize=128)
    assert overview_level == 3

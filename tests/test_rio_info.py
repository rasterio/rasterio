import click
from click.testing import CliRunner


import rasterio
from rasterio.rio import cli, info


def test_env():
    runner = CliRunner()
    result = runner.invoke(info.env, ['--formats'])
    assert result.exit_code == 0
    assert 'GTiff' in result.output


def test_info_err():
    runner = CliRunner()
    result = runner.invoke(
        info.info,
        ['tests'])
    assert result.exit_code == 1


def test_info():
    runner = CliRunner()
    result = runner.invoke(
        info.info,
        ['tests/data/RGB.byte.tif'])
    assert result.exit_code == 0
    assert '"count": 3' in result.output


def test_info_verbose():
    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        ['-v', 'info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0


def test_info_quiet():
    runner = CliRunner()
    result = runner.invoke(
        cli.cli,
        ['-q', 'info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0


def test_info_count():
    runner = CliRunner()
    result = runner.invoke(
        info.info,
        ['tests/data/RGB.byte.tif', '--count'])
    assert result.exit_code == 0
    assert result.output == '3\n'


def test_info_nodatavals():
    runner = CliRunner()
    result = runner.invoke(
        info.info,
        ['tests/data/RGB.byte.tif', '--bounds'])
    assert result.exit_code == 0
    assert result.output == '101985.0 2611485.0 339315.0 2826915.0\n'


def test_info_tags():
    runner = CliRunner()
    result = runner.invoke(
        info.info,
        ['tests/data/RGB.byte.tif', '--tags'])
    assert result.exit_code == 0
    assert result.output == '{"AREA_OR_POINT": "Area"}\n'


def test_info_res():
    runner = CliRunner()
    result = runner.invoke(
        info.info,
        ['tests/data/RGB.byte.tif', '--res'])
    assert result.exit_code == 0
    assert result.output.startswith('300.037')


def test_info_lnglat():
    runner = CliRunner()
    result = runner.invoke(
        info.info,
        ['tests/data/RGB.byte.tif', '--lnglat'])
    assert result.exit_code == 0
    assert result.output.startswith('-77.757')


def test_mo_info():
    runner = CliRunner()
    result = runner.invoke(info.info, ['tests/data/RGB.byte.tif'])
    assert result.exit_code == 0
    assert '"res": [300.037' in result.output
    assert '"lnglat": [-77.757' in result.output


def test_info_stats():
    runner = CliRunner()
    result = runner.invoke(info.info, ['tests/data/RGB.byte.tif', '--tell-me-more'])
    assert result.exit_code == 0
    assert '"stats": [{"max": 255.0, "mean": 44.4344' in result.output


def test_info_stats_only():
    runner = CliRunner()
    result = runner.invoke(info.info, ['tests/data/RGB.byte.tif', '--stats', '--bidx', '2'])
    assert result.exit_code == 0
    assert result.output.startswith('1.000000 255.000000 66.02')

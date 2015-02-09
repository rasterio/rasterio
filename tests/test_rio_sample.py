import logging
import sys

import click
from click.testing import CliRunner

import rasterio
from rasterio.rio import sample


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_sample_err():
    runner = CliRunner()
    result = runner.invoke(
        sample.sample,
        ['bogus.tif'],
        "[220650.0, 2719200.0]")
    assert result.exit_code == 1


def test_sample_stdin():
    runner = CliRunner()
    result = runner.invoke(
        sample.sample,
        ['tests/data/RGB.byte.tif'],
        "[220650.0, 2719200.0]\n[220650.0, 2719200.0]",
        catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == '[28, 29, 27]\n[28, 29, 27]'


def test_sample_arg():
    runner = CliRunner()
    result = runner.invoke(
        sample.sample,
        ['tests/data/RGB.byte.tif', "[220650.0, 2719200.0]"],
        catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == '[28, 29, 27]'


def test_sample_bidx():
    runner = CliRunner()
    result = runner.invoke(
        sample.sample,
        ['tests/data/RGB.byte.tif', '--bidx', '1,2', "[220650.0, 2719200.0]"],
        catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == '[28, 29]'


def test_sample_bidx2():
    runner = CliRunner()
    result = runner.invoke(
        sample.sample,
        ['tests/data/RGB.byte.tif', '--bidx', '1..2', "[220650.0, 2719200.0]"],
        catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == '[28, 29]'


def test_sample_bidx3():
    runner = CliRunner()
    result = runner.invoke(
        sample.sample,
        ['tests/data/RGB.byte.tif', '--bidx', '..2', "[220650.0, 2719200.0]"],
        catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == '[28, 29]'


def test_sample_bidx4():
    runner = CliRunner()
    result = runner.invoke(
        sample.sample,
        ['tests/data/RGB.byte.tif', '--bidx', '3', "[220650.0, 2719200.0]"],
        catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == '[27]'

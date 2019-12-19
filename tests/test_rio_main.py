import logging
import sys

from packaging.version import parse
import pytest

from rasterio.rio.main import main_group


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_version(data, runner):
    result = runner.invoke(main_group, ['--version'])
    assert result.exit_code == 0
    assert parse(result.output.strip())


def test_gdal_version(data, runner):
    result = runner.invoke(main_group, ['--gdal-version'])
    assert result.exit_code == 0
    assert parse(result.output.strip())

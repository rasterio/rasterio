import logging
import sys

from packaging.version import parse

from rasterio.rio.main import main_group


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_version(runner):
    result = runner.invoke(main_group, ['--version'])
    assert result.exit_code == 0
    assert parse(result.output.strip())


def test_gdal_version(runner):
    result = runner.invoke(main_group, ['--gdal-version'])
    assert result.exit_code == 0
    assert parse(result.output.strip())


def test_show_versions(runner):
    result = runner.invoke(main_group, ['--show-versions'])
    assert result.exit_code == 0
    assert "System" in result.output
    assert "python" in result.output
    assert "GDAL" in result.output
    assert "Python deps" in result.output

"""Tests for ``rio pipeline`` CLI command."""

import os

import pytest

import rasterio
from rasterio.env import _GDAL_AT_LEAST_3_12
from rasterio.rio.main import main_group


pytestmark = pytest.mark.skipif(
    not _GDAL_AT_LEAST_3_12, reason="GDAL 3.12+ is required for rio pipeline"
)


def test_rio_pipeline_string(runner, tmpdir):
    """rio pipeline executes a quoted pipeline string with embedded read/write."""
    output = str(tmpdir.join("out.tif"))
    pipeline_str = (
        f"! read tests/data/RGB.byte.tif "
        f"! reproject --dst-crs=EPSG:4326 "
        f"! select --band 1 "
        f"! write {output} --overwrite"
    )
    result = runner.invoke(main_group, ["pipeline", pipeline_str])
    assert result.exit_code == 0, result.output
    assert os.path.exists(output)

    with rasterio.open(output) as dst:
        assert dst.count == 1
        assert dst.crs.to_epsg() == 4326


def test_rio_pipeline_options(runner, tmpdir):
    """rio pipeline supports -i/--input, -o/--output, and -f/--format options."""
    output = str(tmpdir.join("out.tif"))
    result = runner.invoke(
        main_group,
        [
            "pipeline",
            "-i",
            "tests/data/RGB.byte.tif",
            "-o",
            output,
            "-f",
            "COG",
            "read ! reproject --dst-crs=EPSG:4326",
        ],
    )
    assert result.exit_code == 0, result.output
    assert os.path.exists(output)

    with rasterio.open(output) as dst:
        assert dst.count == 3
        assert dst.crs.to_epsg() == 4326


def test_rio_pipeline_output_conflict(runner, tmpdir):
    """rio pipeline reports an output given twice as a usage error."""
    result = runner.invoke(
        main_group,
        [
            "pipeline",
            "-o",
            str(tmpdir.join("b.tif")),
            f"! read tests/data/RGB.byte.tif ! write {tmpdir.join('a.tif')}",
        ],
    )
    assert result.exit_code == 1
    assert "only one place" in result.output


def test_rio_pipeline_tokens(runner, tmpdir):
    """rio pipeline passes unquoted step options through to GDAL."""
    output = str(tmpdir.join("out.tif"))
    result = runner.invoke(
        main_group,
        [
            "pipeline",
            "!",
            "read",
            "tests/data/RGB.byte.tif",
            "!",
            "reproject",
            "--dst-crs=EPSG:4326",
            "!",
            "write",
            "-f",
            "GTiff",
            output,
            "--overwrite",
        ],
    )
    assert result.exit_code == 0, result.output

    with rasterio.open(output) as dst:
        assert dst.driver == "GTiff"
        assert dst.crs.to_epsg() == 4326

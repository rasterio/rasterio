"""Tests for rasterio.pipeline (GDAL 3.12+ pipeline support)."""

import json

import numpy as np
import pytest

import rasterio
from rasterio.env import _GDAL_AT_LEAST_3_12
from rasterio.errors import RasterioIOError
from rasterio.pipeline import PipelineVRT, run
from rasterio.windows import Window


pytestmark = pytest.mark.skipif(
    not _GDAL_AT_LEAST_3_12, reason="GDAL 3.12+ is required for rasterio.pipeline"
)


def test_pipeline_vrt_with_open_dataset(path_rgb_byte_tif):
    """PipelineVRT streams multi-step raster pipeline from an open DatasetReader."""
    with rasterio.open(path_rgb_byte_tif) as src:
        with PipelineVRT(
            "read ! reproject --dst-crs=EPSG:4326 ! select --band 1,2",
            input=src,
        ) as vrt:
            assert not vrt.closed
            assert repr(vrt).startswith("<open PipelineVRT")
            assert vrt.count == 2
            assert vrt.crs.to_epsg() == 4326
            assert vrt.dtypes == ("uint8", "uint8")

            # Read a 64x64 window lazily
            win = Window(100, 100, 64, 64)
            data = vrt.read(window=win)
            assert data.shape == (2, 64, 64)
            assert data.dtype == np.uint8

        assert vrt.closed
        assert repr(vrt).startswith("<closed PipelineVRT")


def test_pipeline_vrt_with_path_in_string(path_rgb_byte_tif):
    """PipelineVRT works when input path is embedded in pipeline string with leading '!'."""
    pipeline_str = (
        f"! read {path_rgb_byte_tif} ! select --band 1 ! resize --size 128,128"
    )
    with PipelineVRT(pipeline_str) as vrt:
        assert vrt.count == 1
        assert vrt.width == 128
        assert vrt.height == 128
        assert vrt.shape == (128, 128)
        arr = vrt.read(1)
        assert arr.shape == (128, 128)
        assert np.any(arr > 0)


def test_pipeline_vrt_with_token_list(path_rgb_byte_tif):
    """PipelineVRT accepts a sequence of CLI tokens."""
    tokens = [
        "!",
        "read",
        "!",
        "reproject",
        "--dst-crs=EPSG:4326",
    ]
    with rasterio.open(path_rgb_byte_tif) as src:
        with PipelineVRT(tokens, input=src) as vrt:
            assert vrt.crs.to_epsg() == 4326
            assert vrt.count == 3


def test_pipeline_vrt_mosaic_multiple_datasets(path_rgb_byte_tif):
    """PipelineVRT accepts a list of open datasets for multi-input steps like mosaic/stack."""
    with (
        rasterio.open(path_rgb_byte_tif) as src1,
        rasterio.open(path_rgb_byte_tif) as src2,
    ):
        with PipelineVRT(
            "mosaic ! select --band 1",
            input=[src1, src2],
        ) as vrt:
            assert vrt.count == 1
            assert vrt.shape == src1.shape
            arr = vrt.read(1, window=Window(0, 0, 32, 32))
            expected = src1.read(1, window=Window(0, 0, 32, 32))
            np.testing.assert_array_equal(arr, expected)


def test_pipeline_run_raster_write(path_rgb_byte_tif, tmp_path):
    """run() executes a raster pipeline and writes output file."""
    out_tif = tmp_path / "out_cog.tif"
    with rasterio.open(path_rgb_byte_tif) as src:
        run(
            "read ! reproject --dst-crs=EPSG:4326 ! select --band 1",
            input=src,
            output=out_tif,
            output_format="COG",
        )

    assert out_tif.exists()
    with rasterio.open(out_tif) as dst:
        assert dst.count == 1
        assert dst.crs.to_epsg() == 4326


def test_pipeline_run_output_appends_write_despite_quoted_bang(
    path_rgb_byte_tif, tmp_path
):
    """A quoted "! write" inside the last step is not mistaken for a write step."""
    out_tif = tmp_path / "out.tif"
    with rasterio.open(path_rgb_byte_tif) as src:
        run(
            'read ! edit --metadata "NOTE=x ! write y"',
            input=src,
            output=out_tif,
        )

    with rasterio.open(out_tif) as dst:
        assert dst.tags()["NOTE"] == "x ! write y"


def test_pipeline_run_output_appends_write_to_token_list(path_rgb_byte_tif, tmp_path):
    """A 'write' token that is an option value is not mistaken for a write step."""
    out_tif = tmp_path / "out.tif"
    with rasterio.open(path_rgb_byte_tif) as src:
        run(
            ["read", "!", "edit", "--unset-metadata", "write"],
            input=src,
            output=out_tif,
        )

    with rasterio.open(out_tif) as dst:
        assert dst.count == 3


def test_pipeline_run_hybrid_raster_to_vector(tmp_path):
    """run() executes a mixed raster-to-vector pipeline (sieve -> polygonize -> filter -> simplify-coverage -> write .gpkg)."""
    out_gpkg = tmp_path / "polygons.gpkg"
    shade_tif = "tests/data/shade.tif"

    pipeline_str = (
        f"! read {shade_tif} "
        "! sieve --size-threshold 500 "
        "! polygonize "
        '! filter --where "DN = 0" '
        "! simplify-coverage --tolerance 100 "
        f"! write {out_gpkg} --overwrite --quiet"
    )
    run(pipeline_str)
    assert out_gpkg.exists()
    assert out_gpkg.stat().st_size > 0


def test_pipeline_run_hybrid_with_open_dataset(tmp_path):
    """run() executes a raster-to-vector pipeline starting from an open rasterio dataset."""
    out_geojson = tmp_path / "polygons.geojson"
    with rasterio.open("tests/data/shade.tif") as src:
        run(
            "! read "
            "! sieve --size-threshold 500 "
            "! polygonize "
            '! filter --where "DN = 0" '
            "! simplify-coverage --tolerance 100 "
            f"! write {out_geojson} --overwrite --quiet",
            input=src,
        )

    assert out_geojson.exists()
    with open(out_geojson, encoding="utf-8") as f:
        fc = json.load(f)
    assert fc["type"] == "FeatureCollection"
    assert len(fc["features"]) > 0
    for feat in fc["features"]:
        assert feat["properties"]["DN"] == 0


def test_pipeline_vrt_rejects_vector_output():
    """PipelineVRT raises RasterioIOError when pipeline produces a vector-only dataset."""
    with pytest.raises(RasterioIOError, match="does not contain any raster bands"):
        PipelineVRT("! read tests/data/shade.tif ! polygonize")


def test_pipeline_invalid_syntax():
    """Invalid pipeline step raises RasterioIOError."""
    with pytest.raises(RasterioIOError):
        PipelineVRT("! read tests/data/RGB.byte.tif ! nonexistent-step")

    with pytest.raises(RasterioIOError):
        run("! read tests/data/RGB.byte.tif ! nonexistent-step")

    with pytest.raises(RasterioIOError):
        run(["!", "read", "tests/data/RGB.byte.tif", "!", "nonexistent-step"])


@pytest.mark.parametrize(
    "pipeline",
    [
        "! read tests/data/RGB.byte.tif ! write {a} --overwrite",
        "! read tests/data/RGB.byte.tif ! write --overwrite -o {a}",
        "! read tests/data/RGB.byte.tif ! write -f GTiff --co=TILED=YES {a}",
        ["!", "read", "tests/data/RGB.byte.tif", "!", "write", "{a}"],
    ],
)
def test_pipeline_run_output_conflicts_with_write_path(pipeline, tmp_path):
    """output= is rejected when the write step already names an output."""
    a = str(tmp_path / "a.tif")
    if isinstance(pipeline, str):
        pipeline = pipeline.format(a=a)
    else:
        pipeline = [t.format(a=a) for t in pipeline]

    with pytest.raises(ValueError, match="only one place"):
        run(pipeline, output=tmp_path / "b.tif")
    assert not list(tmp_path.iterdir())


def test_pipeline_run_output_fills_bare_write(path_rgb_byte_tif, tmp_path):
    """output= binds the path of a write step that names none."""
    out_tif = tmp_path / "out.tif"
    run(
        f"! read {path_rgb_byte_tif} ! write -f GTiff --co TILED=YES --overwrite",
        output=out_tif,
    )

    with rasterio.open(out_tif) as dst:
        assert dst.driver == "GTiff"
        assert dst.profile["tiled"]

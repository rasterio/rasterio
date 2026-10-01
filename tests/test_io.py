"""Tests of the rasterio.io module."""

import numpy as np
import pytest

import rasterio
from rasterio.io import DatasetReader, DatasetWriter


httpstif = (
    "https://github.com/rasterio/rasterio/blob/main/tests/data/float32.tif?raw=true"
)


def test_datasetreader_ctor_filename(path_rgb_byte_tif):
    """DatasetReader constructor accepts string filenames."""
    assert DatasetReader(path_rgb_byte_tif).name.endswith("RGB.byte.tif")


@pytest.mark.network
def test_datasetreader_ctor_url(gdalenv):
    """DatasetReader constructor accepts URLs."""
    dataset = DatasetReader(httpstif)
    assert dataset.name.startswith("https")
    assert dataset.name.endswith("float32.tif?raw=true")


def test_datasetwriter_no_crs(tmp_path):
    """DatasetWriter constructor accepts string filenames."""
    filename = str(tmp_path.joinpath("lol.tif"))
    assert DatasetWriter(
        filename,
        "w",
        driver="GTiff",
        width=100,
        height=100,
        count=1,
        dtype="uint8",
    ).name.endswith("lol.tif")


def test_write_cog_dtype(tmp_path):
    # https://github.com/rasterio/rasterio/issues/3652
    with rasterio.open(
        tmp_path.joinpath("test_cog.tif"),
        mode="w",
        driver="COG",
        width=2,
        height=2,
        count=1,
        dtype="float32",
        nodata=np.nan,
        crs="EPSG:3857",
        transform=rasterio.transform.from_origin(0, 2000, 1000, 1000),
    ) as dst:
        assert dst.dtypes[0] == "float32"

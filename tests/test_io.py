"""Tests of the rasterio.io module."""

import pytest

from rasterio.io import DatasetReader, DatasetWriter


httpstif = (
    "https://github.com/rasterio/rasterio/blob/master/tests/data/float32.tif?raw=true"
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

"""Tests of the Python opener VSI plugin."""

import zipfile
import io

import fsspec
import pytest

import rasterio


def test_opener_io_open():
    """Use io.open as opener."""
    with rasterio.open("tests/data/RGB.byte.tif", opener=io.open) as src:
        profile = src.profile
        assert profile["driver"] == "GTiff"
        assert profile["count"] == 3


@pytest.mark.parametrize("urlpath", ["file://tests/data/RGB.byte.tif", "zip://*.tif::tests/data/files.zip"])
def test_opener_fsspec_open(urlpath):
    """Use fsspec.open as opener."""
    with rasterio.open(urlpath, opener=fsspec.open) as src:
        profile = src.profile
        assert profile["driver"] == "GTiff"
        assert profile["count"] == 3


def test_opener_fsspec_fs():
    """Use fsspec filesystem as opener."""
    fs = fsspec.filesystem("file")
    with rasterio.open("tests/data/RGB.byte.tif", opener=fs.open) as src:
        profile = src.profile
        assert profile["driver"] == "GTiff"
        assert profile["count"] == 3


def test_opener_zipfile_open():
    """Use zipfile as opener."""
    with zipfile.ZipFile("tests/data/files.zip") as zf:
        with rasterio.open("RGB.byte.tif", opener=zf.open) as src:
            profile = src.profile
            assert profile["driver"] == "GTiff"
            assert profile["count"] == 3

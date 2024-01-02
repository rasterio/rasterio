"""Tests of the Python opener VSI plugin."""

import zipfile
import io

import fsspec
import numpy as np
import pytest

import rasterio
from rasterio.enums import MaskFlags
from rasterio.errors import RasterioIOError, OpenerRegistrationError


def test_registration_failure():
    """Exception is raised on attempt to register a second opener for a filename and mode."""
    with pytest.raises(OpenerRegistrationError) as exc_info:
        with rasterio.open(
            "tests/data/RGB.byte.tif", opener=io.open
        ) as a, rasterio.open("tests/data/RGB.byte.tif", opener=int) as b:
            pass

    assert exc_info.value.args[0] == "Opener already registered for urlpath and mode"


def test_opener_failure():
    """Use int as an opener :)"""
    with pytest.raises(RasterioIOError) as exc_info:
        rasterio.open("tests/data/RGB.byte.tif", opener=int)

    assert (
        exc_info.value.args[0]
        == "Opener failed to open file with arguments ('tests/data/RGB.byte.tif', 'rb'): TypeError(\"'str' object cannot be interpreted as an integer\")"
    )


def test_opener_io_open():
    """Use io.open as opener."""
    with rasterio.open("tests/data/RGB.byte.tif", opener=io.open) as src:
        profile = src.profile
        assert profile["driver"] == "GTiff"
        assert profile["count"] == 3


@pytest.mark.parametrize(
    "urlpath", ["file://tests/data/RGB.byte.tif", "zip://*.tif::tests/data/files.zip"]
)
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


def test_opener_fsspec_fs_write(tmp_path):
    """Use fsspec filesystem as opener for writing."""
    data = np.ma.masked_less_equal(np.array([[0, 1, 2]], dtype="uint8"), 1)
    fs = fsspec.filesystem("file")
    with rasterio.open(
        (tmp_path / "test.tif").as_posix(),
        "w",
        driver="GTiff",
        count=1,
        width=3,
        height=1,
        dtype="uint8",
        nodata=0,
        opener=fs.open,
    ) as dst:
        dst.write(data, indexes=1)

    # Expect the dataset's nodata value in the first two pixels.
    with rasterio.open(tmp_path / "test.tif") as src:
        assert src.mask_flag_enums == ([MaskFlags.nodata],)
        arr = src.read()
        assert list(arr.flatten()) == [0, 0, 2]


def test_fp_fsspec_openfile_write(tmp_path):
    """Use an fsspec OpenFile for writing."""
    data = np.ma.masked_less_equal(np.array([[0, 1, 2]], dtype="uint8"), 1)
    of = fsspec.open((tmp_path / "test.tif").as_posix(), "wb")
    with rasterio.open(
        of,
        "w",
        driver="GTiff",
        count=1,
        width=3,
        height=1,
        dtype="uint8",
        nodata=0,
    ) as dst:
        dst.write(data, indexes=1)

    # Expect the dataset's nodata value in the first two pixels.
    with rasterio.open(tmp_path / "test.tif") as src:
        assert src.mask_flag_enums == ([MaskFlags.nodata],)
        arr = src.read()
        assert list(arr.flatten()) == [0, 0, 2]

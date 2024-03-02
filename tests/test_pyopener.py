"""Tests of the Python opener VSI plugin."""

import io
import os
import zipfile

import fsspec
import numpy as np
import pytest

import rasterio
from rasterio.enums import MaskFlags
from rasterio.errors import OpenerRegistrationError


def test_registration_failure():
    """Exception is raised on attempt to register a second opener for a filename and mode."""
    with pytest.raises(OpenerRegistrationError) as exc_info:
        with rasterio.open(
            "tests/data/RGB.byte.tif", opener=io.open
        ) as a, rasterio.open("tests/data/RGB.byte.tif", opener=fsspec.open) as b:
            pass

    assert exc_info.value.args[0] == "Opener already registered for urlpath and mode."


def test_opener_failure():
    """Use int as an opener :)"""
    with pytest.raises(OpenerRegistrationError) as exc_info:
        rasterio.open("tests/data/RGB.byte.tif", opener=int)


def test_opener_io_open():
    """Use io.open as opener."""
    with rasterio.open("tests/data/RGB.byte.tif", opener=io.open) as src:
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


@pytest.mark.parametrize(
    "urlpath", ["file://tests/data/RGB.byte.tif", "zip://*.tif::tests/data/files.zip"]
)
def test_opener_fsspec_open(urlpath):
    """Use fsspec.open as opener."""
    with rasterio.open(urlpath, opener=fsspec.open) as src:
        profile = src.profile
        assert profile["driver"] == "GTiff"
        assert profile["count"] == 3


def test_opener_fsspec_fs_open():
    """Use fsspec filesystem open() as opener."""
    fs = fsspec.filesystem("file")
    with rasterio.open("tests/data/RGB.byte.tif", opener=fs.open) as src:
        profile = src.profile
        assert profile["driver"] == "GTiff"
        assert profile["count"] == 3


def test_opener_fsspec_fs():
    """Use fsspec filesystem as opener."""
    fs = fsspec.filesystem("file")
    with rasterio.open("tests/data/RGB.byte.tif", opener=fs) as src:
        profile = src.profile
        assert profile["driver"] == "GTiff"
        assert profile["count"] == 3


def test_opener_fsspec_http_fs():
    """Use fsspec http filesystem as opener."""
    fs = fsspec.filesystem("http")
    with rasterio.open(
        "https://raw.githubusercontent.com/rasterio/rasterio/main/tests/data/float32.tif",
        opener=fs,
    ) as src:
        profile = src.profile
        assert profile["driver"] == "GTiff"
        assert profile["count"] == 1


def test_opener_fsspec_fs_open_write(tmp_path):
    """Use fsspec filesystem open() as opener for writing."""
    data = np.ma.masked_less_equal(np.array([[0, 1, 2]], dtype="uint8"), 1)
    fs = fsspec.filesystem("file")
    with rasterio.open(
        os.fspath(tmp_path / "test.tif"),
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


def test_opener_fsspec_fs_write(tmp_path):
    """Use fsspec filesystem open() as opener for writing."""
    data = np.ma.masked_less_equal(np.array([[0, 1, 2]], dtype="uint8"), 1)
    fs = fsspec.filesystem("file")
    with rasterio.open(
        os.fspath(tmp_path / "test.tif"),
        "w",
        driver="GTiff",
        count=1,
        width=3,
        height=1,
        dtype="uint8",
        nodata=0,
        opener=fs,
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
    of = fsspec.open(os.fspath(tmp_path / "test.tif"), "wb")
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


def test_opener_msk_sidecar():
    """Access .msk sidecar file via opener."""
    # This test fails before issue 3027 is resolved because
    # RGB2.byte.tif.msk is not found.
    with rasterio.open("tests/data/RGB2.byte.tif", opener=io.open) as src:
        for val in src.mask_flag_enums:
            assert val == [MaskFlags.per_dataset]


def test_fsspec_msk_sidecar():
    """Access .msk sidecar file via fsspec."""
    fs = fsspec.filesystem("file")
    with rasterio.open("tests/data/RGB2.byte.tif", opener=fs) as src:
        for val in src.mask_flag_enums:
            assert val == [MaskFlags.per_dataset]


def test_fsspec_http_msk_sidecar():
    """Use fsspec http filesystem as opener."""
    fs = fsspec.filesystem("http")
    with rasterio.open(
        "https://raw.githubusercontent.com/rasterio/rasterio/main/tests/data/RGB2.byte.tif",
        opener=fs,
    ) as src:
        for val in src.mask_flag_enums:
            assert val == [MaskFlags.per_dataset]


def test_opener_tiledb_vfs():
    """Use tiledb virtual filesystem as opener."""
    tiledb = pytest.importorskip("tiledb")
    fs = tiledb.VFS()
    with rasterio.open("tests/data/RGB.byte.tif", opener=fs) as src:
        profile = src.profile
        assert profile["driver"] == "GTiff"
        assert profile["count"] == 3

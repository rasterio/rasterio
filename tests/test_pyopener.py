"""Tests of the Python opener VSI plugin."""

import concurrent.futures
import io
import os
import warnings
import zipfile
from contextlib import nullcontext
from pathlib import Path
from threading import Thread

from affine import Affine
import fsspec
import numpy as np
import pytest

import rasterio
from rasterio.enums import MaskFlags
from rasterio.env import _GDAL_AT_LEAST_3_10
from rasterio.errors import OpenerRegistrationError
from rasterio.warp import reproject


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
    "urlpath", ["file://tests/data/RGB.byte.tif", "zip://RGB.byte.tif::tests/data/files.zip"]
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


@pytest.mark.network
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


@pytest.mark.network
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


def test_delete_on_overwrite(data):
    """Opener can delete dataset when overwriting."""
    fs = fsspec.filesystem("file")
    outputfile = os.path.join(str(data), "RGB.byte.tif")

    with rasterio.open(outputfile, opener=fs) as dst:
        profile = dst.profile

    # No need to write any data, as open() will error if VSI unlinking
    # isn't implemented.
    with rasterio.open(outputfile, "w", opener=fs, **profile) as dst:
        pass


@pytest.mark.parametrize("opener", [io.open, fsspec.filesystem("file")])
def test_opener_registration(opener):
    """Opener is correctly registered."""
    from rasterio._vsiopener import _OPENER_REGISTRY, _opener_registration
    with _opener_registration("tests/data/RGB.byte.tif", opener) as registered_vsi_path:
        assert registered_vsi_path.startswith("/vsiriopener_")
        key = (Path("tests/data"), registered_vsi_path.split("/")[1].split("_")[1])
        val = _OPENER_REGISTRY.get()[key]
        assert val.isfile
        assert val._obj == opener


def test_threads_context():
    """Threads have opener registries."""

    def target():
        with rasterio.open("tests/data/RGB.byte.tif", opener=io.open) as dst:
            assert dst.count == 3

    thread = Thread(target=target)
    thread.start()
    thread.join()


def test_threads_overviews(data):
    """."""
    fs = fsspec.filesystem("file")
    outputfile = os.path.join(str(data), "RGB.byte.tif")

    with rasterio.Env(GDAL_NUM_THREADS=1):
        with rasterio.open(outputfile, "r+", opener=fs) as dst:
            dst.build_overviews([2])


def test_warp(tmp_path):
    """File to file."""
    fs = fsspec.filesystem("file")
    tiffname = str(tmp_path.joinpath("foo.tif"))
    with rasterio.open("tests/data/RGB.byte.tif", opener=fs) as src:
        kwargs = src.profile
        kwargs.update(
            transform=Affine(300.0, 0.0, -8789636.708, 0.0, -300.0, 2943560.235),
            crs="EPSG:3857",
        )
        with rasterio.open(tiffname, "w", opener=fs, **kwargs) as dst:
            for i in (1, 2, 3):
                reproject(rasterio.band(src, i), rasterio.band(dst, i), num_threads=2)


def test_opener_fsspec_fs_tiff_threads():
    """Fsspec filesystem opener is compatible with multithreaded tiff decoding."""
    fs = fsspec.filesystem("file")
    with rasterio.open("tests/data/rgb_lzw.tif", opener=fs, num_threads=2) as src:
        profile = src.profile
        assert profile["driver"] == "GTiff"
        assert profile["count"] == 3
        assert src.read().shape == (3, 718, 791)


def test_opener_fsspec_fs_tiff_threads_2():
    """Fsspec filesystem opener is compatible with multithreaded tiff decoding."""
    fs = fsspec.filesystem("file")
    with rasterio.Env(GDAL_NUM_THREADS=2):
        with rasterio.open("tests/data/rgb_lzw.tif", opener=fs) as src:
            profile = src.profile
            assert profile["driver"] == "GTiff"
            assert profile["count"] == 3
            assert src.read().shape == (3, 718, 791)


def test_opener_fsspec_thread_safe_option():
    fs = fsspec.filesystem("file")
    with (
        pytest.raises(rasterio.errors.GDALOptionNotImplementedError) if not _GDAL_AT_LEAST_3_10 else nullcontext(),
        rasterio.Env(GDAL_NUM_THREADS=2),
        rasterio.open("tests/data/rgb_lzw.tif", thread_safe=True, opener=fs) as src
    ):
        def process(window):
            src.read(window=window).sum()

        windows = [window for ij, window in src.block_windows()]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(process, windows)


def test_opener_multi_range_read():
    """Test with Opener with multi-range-read method."""
    from rasterio.abc import MultiByteRangeResourceContainer

    class CustomResource(io.FileIO):
        """Custom FileIO FS with `read_multi_range` method."""

        def get_byte_ranges(
            self,
            offsets,
            sizes,
        ):
            warnings.warn("Using MultiRange Reads", UserWarning, stacklevel=2)
            return [
                self._read_range(offset, size) for (offset, size) in zip(offsets, sizes)
            ]

        def _read_range(self, offset, size):
            _ = self.seek(offset)
            return self.read(size)

    class CustomResourceContainer:
        def open(self, path, mode="r", **kwds):
            return CustomResource(path, mode=mode, **kwds)
        def isfile(self, path):
            return True
        def isdir(self, path):
            return False
        def ls(self, path):
            return []
        def mtime(self, path):
            return 0
        def size(self, path):
            with CustomResource(path) as f:
                return f.size()

    MultiByteRangeResourceContainer.register(CustomResourceContainer)

    with rasterio.open(
        "tests/data/RGB.byte.tif", opener=CustomResourceContainer()
    ) as src:
        profile = src.profile
        assert profile["driver"] == "GTiff"
        assert profile["count"] == 3
        # Should emit a multi-range read
        with pytest.warns(UserWarning, match="Using MultiRange Reads"):
            _ = src.read()

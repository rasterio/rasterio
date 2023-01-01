"""High level tests for Rasterio's ``GDALDataset`` abstractions."""


from pathlib import Path
try:
    from unittest.mock import MagicMock
except ImportError:
    from mock import MagicMock

from numpy.testing import assert_almost_equal, assert_array_equal
import pytest

import rasterio
import rasterio.shutil
from rasterio.coords import BoundingBox
from rasterio.enums import Compression, Resampling
from rasterio.errors import RasterioIOError, DatasetAttributeError
from rasterio.transform import Affine
from .conftest import gdal_version


def test_files(data):
    tif = Path(data).joinpath('RGB.byte.tif')
    aux = tif.parent.joinpath(tif.name + '.aux.xml')
    with open(aux, 'w'):
        pass
    with rasterio.open(tif) as src:
        assert src.files == [tif.as_posix(), aux.as_posix()]


def test_handle_closed(path_rgb_byte_tif):
    """Code that calls ``DatasetBase.handle()`` after it has been closed
    should raise an exception.
    """
    with rasterio.open(path_rgb_byte_tif) as src:
        pass
    with pytest.raises(RasterioIOError):
        src.files


@pytest.mark.parametrize('tag_value', [item.value for item in Compression])
def test_dataset_compression(path_rgb_byte_tif, tag_value):
    """Compression is found from tags"""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        dataset.tags = MagicMock()
        dataset.tags.return_value = {'COMPRESSION': tag_value}
        assert dataset.compression == Compression(tag_value)


def test_untiled_dataset_blocksize(tmpdir):
    """Blocksize is not relevant to untiled datasets (see #1689)"""
    tmpfile = str(tmpdir.join("test.tif"))
    with rasterio.open(
            tmpfile, "w", driver="GTiff", count=1, height=13, width=23, dtype="uint8", crs="epsg:3857",
            transform=Affine.identity(), blockxsize=64, blockysize=64) as dataset:
        pass

    with rasterio.open(tmpfile) as dataset:
        assert not dataset.profile["tiled"]
        assert dataset.shape == (13, 23)
        assert dataset.block_shapes == [(13, 23)]


def test_dataset_readonly_attributes(path_rgb_byte_tif):
    """Attempts to set read-only attributes fail with DatasetAttributeError"""
    with pytest.raises(DatasetAttributeError):
        with rasterio.open(path_rgb_byte_tif) as dataset:
            dataset.crs = "foo"


def test_dataset_readonly_attributes(path_rgb_byte_tif):
    """Attempts to set read-only attributes still fail with NotImplementedError"""
    with pytest.raises(NotImplementedError):
        with rasterio.open(path_rgb_byte_tif) as dataset:
            dataset.crs = "foo"


def test_statistics(path_rgb_byte_tif):
    """Compute, store, and return basic statistics."""
    with rasterio.open(path_rgb_byte_tif) as dataset:
        stats = dataset.statistics(1)
        assert stats.min == 0
        assert stats.max == 255
        assert_almost_equal(stats.mean, 29.947726688477)
        assert_almost_equal(stats.std, 52.340921626611)


@pytest.mark.parametrize("blockysize", [1, 2, 3, 7, 61, 62])
def test_creation_untiled_blockysize(tmp_path, blockysize):
    """Check for fix of gh-2599"""
    tmpfile = tmp_path / "test.tif"
    with rasterio.open(
        tmpfile,
        "w",
        count=1,
        height=61,
        width=37,
        dtype="uint8",
        blockysize=blockysize,
        tiled=False,
    ) as dataset:
        pass

    with rasterio.open(tmpfile) as dataset:
        assert not dataset.is_tiled
        assert dataset.profile["blockysize"] == min(blockysize, 61)
        assert dataset.block_shapes[0][0] == min(blockysize, 61)


def test_build_vrt__attributes(path_rgb_byte_tif):
    with rasterio.open(
        [path_rgb_byte_tif]
    ) as vrt, rasterio.open(path_rgb_byte_tif) as rds:
        assert vrt.name == "MultiFileVRT"
        assert rds.count == vrt.count
        assert rds.crs == vrt.crs
        assert rds.transform == vrt.transform
        if gdal_version.at_least("3.3"):
            assert rds.gcps == vrt.gcps
        assert rds.units == vrt.units
        assert rds.descriptions == vrt.descriptions
        assert rds.dtypes == vrt.dtypes
        assert rds.shape == vrt.shape
        assert rds.nodata == vrt.nodata
        vrt_profile = vrt.profile.copy()
        assert vrt_profile.pop("driver") == "VRT"
        assert vrt_profile.pop("blockxsize") == 128
        assert vrt_profile.pop("blockysize") == 128
        assert vrt_profile.pop("tiled") is True
        rds_profile = rds.profile.copy()
        rds_profile.pop("tiled")
        rds_profile.pop("blockysize")
        rds_profile.pop("driver")
        rds_profile.pop("interleave")
        assert rds_profile == vrt_profile
        assert vrt.block_shapes == [(128, 128), (128, 128), (128, 128)]
        assert_array_equal(vrt.read(), rds.read())

@pytest.mark.parametrize(
    "method,value",
    [(Resampling.nearest, 2), (Resampling.average, 2)],
)
def test_build_vrt__multi(method, value, directory_with_overlapping_rasters):
    with rasterio.open(
        sorted(directory_with_overlapping_rasters.iterdir()),
        resampling=method,
    ) as vrt:
        assert vrt.name == "MultiFileVRT"
        assert vrt.count == 1
        assert vrt.shape == (15, 15)
        assert vrt.crs == 4326
        assert vrt.transform.almost_equals(
            Affine(0.2, 0.0, -114.0, 0.0, -0.2, 46.0)
        )
        assert vrt.bounds == BoundingBox(
            left=-114.0, bottom=43.0, right=-111.0, top=46.0
        )
        assert_array_equal(vrt.read()[:, 5:10, 5:10], value)


def test_build_vrt__write(path_rgb_byte_tif, tmp_path):
    dst_file = tmp_path / "file.vrt"
    with rasterio.open([path_rgb_byte_tif]) as vrt:
        rasterio.shutil.copy(vrt, dst_file)

    with rasterio.open(dst_file) as vrt, rasterio.open(path_rgb_byte_tif) as rds:
        assert rds.count == vrt.count
        assert rds.crs == vrt.crs
        assert rds.transform == vrt.transform
        if gdal_version.at_least("3.3"):
            assert rds.gcps == vrt.gcps
        assert rds.units == vrt.units
        assert rds.descriptions == vrt.descriptions
        assert rds.dtypes == vrt.dtypes
        assert rds.shape == vrt.shape
        assert rds.nodata == vrt.nodata
        vrt_profile = vrt.profile.copy()
        assert vrt_profile.pop("driver") == "VRT"
        assert vrt_profile.pop("blockxsize") == 128
        assert vrt_profile.pop("blockysize") == 128
        assert vrt_profile.pop("tiled") is True
        rds_profile = rds.profile.copy()
        rds_profile.pop("tiled")
        rds_profile.pop("blockysize")
        rds_profile.pop("driver")
        rds_profile.pop("interleave")
        assert rds_profile == vrt_profile
        assert vrt.block_shapes == [(128, 128), (128, 128), (128, 128)]
        assert_array_equal(vrt.read(), rds.read())


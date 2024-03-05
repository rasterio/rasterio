"""High level tests for Rasterio's ``GDALDataset`` abstractions."""


import math
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import rasterio
from rasterio.coords import BoundingBox
from rasterio.enums import Compression
from rasterio.errors import DatasetAttributeError, RasterioIOError
from rasterio.transform import Affine

from .conftest import assert_bounding_box_equal


def test_files(data):
    tif = Path(data).joinpath('RGB.byte.tif')
    aux = tif.parent.joinpath(tif.name + '.aux.xml')
    with open(aux, 'w'):
        pass
    with rasterio.open(tif) as src:
        assert src.files == [os.fspath(tif), os.fspath(aux)]


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
        blockysize, blockxsize = dataset.block_shapes[0]
        assert blockxsize == dataset.width
        assert dataset.profile["blockysize"] == min(blockysize, 61)
        assert blockysize == min(blockysize, 61)


@pytest.mark.parametrize(
    ["width", "height", "transform", "expected_bounds"],
    [
        pytest.param(2, 2, Affine.identity(), BoundingBox(0.0, 2.0, 2.0, 0.0), id="Identity transform"),
        pytest.param(2, 2, Affine.scale(1, -1), BoundingBox(0.0, -2.0, 2.0, 0.0), id="North-up transform"),
        pytest.param(2, 2, Affine.translation(2, 2) * Affine.scale(1, -1), BoundingBox(2.0, 0.0, 4.0, 2.0), id="Translated transform"),
        pytest.param(2, 2, Affine.scale(4) * Affine.scale(1, -1), BoundingBox(0.0, -8.0, 8.0, 0.0), id="Scaled transform"),
        pytest.param(2, 2, Affine.rotation(90) * Affine.scale(1, -1), BoundingBox(0.0, 0.0, 2.0, 2.0), id="90 degree rotated transform"),
        pytest.param(2, 2, Affine.rotation(45) * Affine.scale(1, -1), BoundingBox(0.0, -math.sqrt(2), 2 * math.sqrt(2), math.sqrt(2)), id="45 degree rotated transform"),
        pytest.param(2, 2, Affine.scale(4, 1) * Affine.scale(1, -1), BoundingBox(0, -2.0, 8.0, 0.0), id="Rectangular pixel transform"),
        pytest.param(6, 2, Affine.scale(1, -1), BoundingBox(0, -2.0, 6.0, 0.0), id="Differing width and height"),
    ]
)
def test_bounds(width, height, transform, expected_bounds, image_file_with_custom_size_and_transform):
    filepath = image_file_with_custom_size_and_transform(width, height, transform)
    with rasterio.open(filepath) as dataset:
        assert_bounding_box_equal(expected_bounds, dataset.bounds)

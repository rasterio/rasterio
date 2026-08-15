"""Tests of the raster stacking tool."""

import numpy as np
import pytest

import rasterio
from rasterio.enums import Resampling
from rasterio.merge import merge
from rasterio.stack import stack
from rasterio.transform import from_origin
from rasterio.vrt import WarpedVRT


def write_raster(path, data, transform):
    """Write a small test raster."""
    if data.ndim == 2:
        data = data[np.newaxis, ...]

    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=data.shape[2],
        height=data.shape[1],
        count=data.shape[0],
        dtype=data.dtype,
        crs="EPSG:3857",
        transform=transform,
        nodata=0,
    ) as dataset:
        dataset.write(data)


def test_stack_warpedvrt(tmp_path):
    """Stack reads WarpedVRT sources without requesting boundless data."""
    left_path = tmp_path / "left.tif"
    right_path = tmp_path / "right.tif"
    transform = from_origin(0, 2, 1, 1)
    write_raster(left_path, np.full((2, 2), 1, dtype="uint8"), transform)
    write_raster(
        right_path,
        np.full((2, 2), 2, dtype="uint8"),
        from_origin(2, 2, 1, 1),
    )

    with rasterio.open(left_path) as left, rasterio.open(right_path) as right:
        with (
            WarpedVRT(left, crs=left.crs) as left_vrt,
            WarpedVRT(right, crs=right.crs) as right_vrt,
        ):
            result, result_transform = stack([left_vrt, right_vrt], nodata=0)

    expected = np.zeros((2, 2, 4), dtype="uint8")
    expected[0, :, :2] = 1
    expected[1, :, 2:] = 2
    assert result_transform == transform
    np.testing.assert_array_equal(result, expected)


def test_stack_disjoint_chunked_mixed_indexes(tmp_path):
    """Disjoint chunks preserve the destination bands of later sources."""
    left_path = tmp_path / "left.tif"
    right_path = tmp_path / "right.tif"
    output_path = tmp_path / "stacked.tif"
    height = width = 800

    left = np.stack(
        [
            np.full((height, width), 11, dtype="uint8"),
            np.full((height, width), 22, dtype="uint8"),
            np.full((height, width), 33, dtype="uint8"),
        ]
    )
    right = np.stack(
        [
            np.full((height, width), 66, dtype="uint8"),
            np.full((height, width), 77, dtype="uint8"),
        ]
    )
    write_raster(left_path, left, from_origin(0, height, 1, 1))
    write_raster(right_path, right, from_origin(width, height, 1, 1))

    stack(
        [left_path, right_path],
        indexes=[[3, 1], 2],
        nodata=0,
        dst_path=output_path,
        dst_kwds={"tiled": True, "blockxsize": 256, "blockysize": 256},
        mem_limit=1,
    )

    expected = np.zeros((3, height, width * 2), dtype="uint8")
    expected[0, :, :width] = 33
    expected[1, :, :width] = 11
    expected[2, :, width:] = 77
    with rasterio.open(output_path) as result:
        assert result.transform == from_origin(0, height, 1, 1)
        np.testing.assert_array_equal(result.read(), expected)


@pytest.mark.parametrize("resampling", [Resampling.nearest, Resampling.average])
def test_stack_downsampled_matches_merge(tmp_path, resampling):
    """Stack uses merge-compatible window alignment when downsampling."""
    first_path = tmp_path / "first.tif"
    second_path = tmp_path / "second.tif"
    transform = from_origin(0.35, 9.65, 1, 1)
    first_data = np.arange(63, dtype="uint8").reshape(7, 9) + 1
    second_data = np.flip(first_data, axis=1)
    write_raster(first_path, first_data, transform)
    write_raster(second_path, second_data, transform)

    with rasterio.open(first_path) as first, rasterio.open(second_path) as second:
        bounds = first.bounds
        result, result_transform = stack(
            [first, second], bounds=bounds, res=2.3, resampling=resampling, nodata=0
        )
        first_merged, first_transform = merge(
            [first], bounds=bounds, res=2.3, resampling=resampling, nodata=0
        )
        second_merged, second_transform = merge(
            [second], bounds=bounds, res=2.3, resampling=resampling, nodata=0
        )

    assert result_transform == first_transform == second_transform
    np.testing.assert_array_equal(result[0], first_merged[0])
    np.testing.assert_array_equal(result[1], second_merged[0])

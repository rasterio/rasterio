"""Tests of raster stacking features."""

from contextlib import ExitStack

import rasterio
from rasterio.stack import stack
from rasterio.vrt import WarpedVRT


def test_stack_disjoint(tmp_path, runner):
    dst_path = tmp_path.joinpath("stacked.tif")
    stack(
        [
            "tests/data/rgb1.tif",
            "tests/data/rgb2.tif",
            "tests/data/rgb3.tif",
            "tests/data/rgb4.tif",
        ],
        dst_path=dst_path,
    )

    with rasterio.open(dst_path) as out:
        assert out.count == 12
        assert out.shape == (718, 791)


def test_stack_warped_vrt(tmp_path, runner):
    dst_path = tmp_path.joinpath("stacked.tif")
    with ExitStack() as exit_stack:
        inputs = [
            WarpedVRT(exit_stack.enter_context(rasterio.open(path)), crs="EPSG:3857")
            for path in [
                "tests/data/rgb1.tif",
                "tests/data/rgb2.tif",
                "tests/data/rgb3.tif",
                "tests/data/rgb4.tif",
            ]
        ]
        stack(inputs, dst_path=dst_path, dst_kwds={"driver": "GTiff"})

    with rasterio.open(dst_path) as out:
        assert out.count == 12
        assert out.shape == (734, 801)

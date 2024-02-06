"""Tests of rasterio.merge"""

import boto3
from hypothesis import given, settings
from hypothesis.strategies import floats
import numpy
import pytest

import affine
import rasterio
from rasterio.merge import merge
from rasterio.crs import CRS
from rasterio.errors import RasterioError


# Non-coincident datasets test fixture.
# Three overlapping GeoTIFFs, two to the NW and one to the SE.
@pytest.fixture(scope="function")
def test_data_dir_overlapping(tmp_path):
    kwargs = {
        "crs": "EPSG:4326",
        "transform": affine.Affine(0.2, 0, -114, 0, -0.2, 46),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 0,
    }

    with rasterio.open(tmp_path.joinpath("nw1.tif"), "w", **kwargs) as dst:
        data = numpy.ones((10, 10), dtype=rasterio.uint8)
        dst.write(data, indexes=1)

    with rasterio.open(tmp_path.joinpath("nw3.tif"), "w", **kwargs) as dst:
        data = numpy.ones((10, 10), dtype=rasterio.uint8) * 3
        dst.write(data, indexes=1)

    kwargs["transform"] = affine.Affine(0.2, 0, -113, 0, -0.2, 45)

    with rasterio.open(tmp_path.joinpath("se.tif"), "w", **kwargs) as dst:
        data = numpy.ones((10, 10), dtype=rasterio.uint8) * 2
        dst.write(data, indexes=1)

    return tmp_path


def test_different_crs(test_data_dir_overlapping):
    inputs = [x.name for x in test_data_dir_overlapping.iterdir()]

    # Create new raster with different crs
    with rasterio.open(test_data_dir_overlapping.joinpath(inputs[-1])) as ds_src:
        kwds = ds_src.profile
        kwds['crs'] = CRS.from_epsg(3499)
        with rasterio.open(test_data_dir_overlapping.joinpath("new.tif"), 'w', **kwds) as ds_out:
            ds_out.write(ds_src.read())
    with pytest.raises(RasterioError):
        result = merge(list(test_data_dir_overlapping.iterdir()))


@pytest.mark.parametrize(
    "method,value",
    [("first", 1), ("last", 2), ("min", 1), ("max", 3), ("sum", 6), ("count", 3)],
)
def test_merge_method(test_data_dir_overlapping, method, value):
    """Merge method produces expected values in intersection"""
    inputs = sorted(list(test_data_dir_overlapping.iterdir()))  # nw is first.
    datasets = [rasterio.open(x) for x in inputs]
    output_count = 1
    arr, _ = merge(
        datasets, output_count=output_count, method=method, dtype=numpy.uint64
    )
    numpy.testing.assert_array_equal(arr[:, 5:10, 5:10], value)


def test_issue2163():
    """Demonstrate fix for issue 2163"""
    with rasterio.open("tests/data/float_raster_with_nodata.tif") as src:
        data = src.read()
        result, transform = merge([src])
        assert numpy.allclose(data, result[:, : data.shape[1], : data.shape[2]])


def test_unsafe_casting():
    """Demonstrate fix for issue 2179"""
    with rasterio.open("tests/data/float_raster_with_nodata.tif") as src:
        result, transform = merge([src], dtype="uint8", nodata=0.0)
        assert not result.any()  # this is why it's called "unsafe".


@pytest.mark.skipif(
    not (boto3.Session().get_credentials()),
    reason="S3 raster access requires credentials",
)
@pytest.mark.network
@pytest.mark.slow
@settings(deadline=None, max_examples=5)
@given(
    dx=floats(min_value=-0.05, max_value=0.05),
    dy=floats(min_value=-0.05, max_value=0.05),
)
def test_issue2202(dx, dy):
    shapely = pytest.importorskip("shapely", reason="Test requires shapely.")
    import rasterio.merge
    from shapely import wkt
    from shapely.affinity import translate

    aoi = wkt.loads(
        r"POLYGON((11.09 47.94, 11.06 48.01, 11.12 48.11, 11.18 48.11, 11.18 47.94, 11.09 47.94))"
    )
    aoi = translate(aoi, dx, dy)

    with rasterio.Env(AWS_NO_SIGN_REQUEST=True,):
        ds = [
            rasterio.open(i)
            for i in [
                "/vsis3/copernicus-dem-30m/Copernicus_DSM_COG_10_N47_00_E011_00_DEM/Copernicus_DSM_COG_10_N47_00_E011_00_DEM.tif",
                "/vsis3/copernicus-dem-30m/Copernicus_DSM_COG_10_N48_00_E011_00_DEM/Copernicus_DSM_COG_10_N48_00_E011_00_DEM.tif",
            ]
        ]
        aux_array, aux_transform = rasterio.merge.merge(datasets=ds, bounds=aoi.bounds)
        from rasterio.plot import show

        show(aux_array)


import math
from rasterio import windows
from rasterio.warp import aligned_target


def _chunk_output(width, height, count, itemsize, mem_limit=1):
    """Divide the calculation output into chunks.

    This function determines the chunk size such that an array of shape
    (chunk_size, chunk_size, count) with itemsize bytes per element
    requires no more than mem_limit megabytes of memory.

    Output chunks are described by rasterio Windows.

    Parameters
    ----------
    width : int
        Output width
    height : int
        Output height
    count : int
        Number of output bands
    itemsize : int
        Number of bytes per pixel
    mem_limit : int, default
        The maximum size in memory of a chunk array

    Returns
    -------
    sequence of Windows
    """
    max_pixels = mem_limit * 1.0e6 / itemsize * count
    chunk_size = int(math.floor(math.sqrt(max_pixels)))
    ncols = int(math.ceil(width / chunk_size))
    nrows = int(math.ceil(height / chunk_size))
    chunk_windows = []

    for col in range(ncols):
        col_offset = col * chunk_size
        w = min(chunk_size, width - col_offset)
        for row in range(nrows):
            row_offset = row * chunk_size
            h = min(chunk_size, height - row_offset)
            chunk_windows.append(
                ((row, col), windows.Window(col_offset, row_offset, w, h))
            )

    return chunk_windows


def test_merge_destination_1(tmp_path):
    """Merge into an opened dataset."""
    with rasterio.open("tests/data/float_raster_with_nodata.tif") as src:
        profile = src.profile
        data = src.read()

        from rasterio import windows

        with rasterio.open(tmp_path.joinpath("test.tif"), "w", **profile) as dst:
            for _, chunk_window in _chunk_output(
                dst.width, dst.height, dst.count, 64, mem_limit=1
            ):
                chunk_bounds = windows.bounds(chunk_window, dst.transform)
                chunk_arr, chunk_transform = merge([src], bounds=chunk_bounds)
                target_window = windows.from_bounds(*chunk_bounds, dst.transform)
                dst.write(chunk_arr, window=target_window)

        with rasterio.open(tmp_path.joinpath("test.tif")) as dst:
            result = dst.read()
            assert numpy.allclose(data, result[:, : data.shape[1], : data.shape[2]])


def test_merge_destination_2(tmp_path):
    """Merge into an opened, target-aligned dataset."""
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        profile = src.profile
        dst_transform, dst_width, dst_height = aligned_target(
            src.transform, src.width, src.height, src.res
        )
        profile.update(transform=dst_transform, width=dst_width, height=dst_height)

        data = src.read()

        from rasterio import windows
        from rasterio import enums

        with rasterio.open(tmp_path.joinpath("test.tif"), "w", **profile) as dst:
            dst.write(numpy.ones((dst.count, dst.height, dst.width)) * 255)
            for _, chunk_window in _chunk_output(
                dst.width, dst.height, dst.count, 32, mem_limit=0.5
            ):
                chunk_bounds = windows.bounds(chunk_window, dst.transform)
                chunk_arr, chunk_transform = merge([src], bounds=chunk_bounds)
                target_window = windows.from_bounds(*chunk_bounds, dst.transform)
                target_window = windows.Window(
                    col_off=round(target_window.col_off),
                    row_off=round(target_window.row_off),
                    width=round(target_window.width),
                    height=round(target_window.height),
                )
                print(_, chunk_window, target_window)
                dst.write(chunk_arr, window=target_window)

        with rasterio.open(tmp_path.joinpath("test.tif")) as dst:
            result = dst.read()
            assert result.shape == (3, 719, 792)
            assert numpy.allclose(data.mean(), result[:, :-1, :-1].mean())

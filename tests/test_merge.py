"""Tests of rasterio.merge"""

import boto3
from hypothesis import given, settings
from hypothesis.strategies import floats
import numpy
import pytest
import warnings

import affine
import rasterio
from rasterio.merge import merge
from rasterio.crs import CRS
from rasterio.errors import MergeError, RasterioError
from rasterio.vrt import WarpedVRT
from rasterio.warp import aligned_target
from rasterio import windows

from .conftest import gdal_version


@pytest.fixture(scope="function")
def test_data_complex(tmp_path):
    transform = affine.Affine(30.0, 0.0, 215200.0, 0.0, -30.0, 4397500.0)
    t2 = transform * transform.translation(0, 3)

    with rasterio.open(
        tmp_path.joinpath("r2.tif"),
        "w",
        nodata=0,
        dtype=numpy.complex64,
        height=2,
        width=2,
        count=1,
        crs="EPSG:32611",
        transform=transform,
    ) as src:
        src.write(numpy.ones((1, 2, 2)))

    with rasterio.open(
        tmp_path.joinpath("r1.tif"),
        "w",
        nodata=0,
        dtype=numpy.complex64,
        height=2,
        width=2,
        count=1,
        crs="EPSG:32611",
        transform=t2,
    ) as src:
        src.write(numpy.ones((1, 2, 2)) * 2 - 1j)

    return tmp_path


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


def test_masked_output():
    """Get a masked array."""
    with rasterio.open("tests/data/float_raster_with_nodata.tif") as src:
        data = src.read()
        result, transform = merge([src], masked=True)
        assert numpy.allclose(data, result[:, : data.shape[1], : data.shape[2]])
        assert result.mask.any()
        assert result.fill_value == src.nodatavals[0]


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
        aux_array, aux_transform = rasterio.merge.merge(ds, bounds=aoi.bounds)
        from rasterio.plot import show

        show(aux_array)


def test_merge_destination_1(tmp_path):
    """Merge into an opened dataset."""
    with rasterio.open("tests/data/float_raster_with_nodata.tif") as src:
        profile = src.profile
        data = src.read()

        with rasterio.open(tmp_path.joinpath("test.tif"), "w", **profile) as dst:
            for chunk in windows.subdivide(
                windows.Window(0, 0, dst.width, dst.height), 256, 256
            ):
                chunk_bounds = windows.bounds(chunk, dst.transform)
                chunk_arr, chunk_transform = merge([src], bounds=chunk_bounds)
                dst_window = windows.from_bounds(*chunk_bounds, dst.transform)
                dw = windows.from_bounds(*chunk_bounds, dst.transform)
                dw = dw.round_offsets().round_lengths()
                dst.write(chunk_arr, window=dw)

        with rasterio.open(tmp_path.joinpath("test.tif")) as dst:
            result = dst.read()
            assert numpy.allclose(data, result[:, : data.shape[1], : data.shape[2]])


def test_merge_destination_2(tmp_path):
    """Merge into an opened, target-aligned dataset."""
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        profile = src.profile
        dst_transform, dst_width, dst_height = aligned_target(
            src.transform,
            src.width,
            src.height,
            src.res,
        )
        profile.update(transform=dst_transform, width=dst_width, height=dst_height)
        data = src.read()

        with rasterio.open(tmp_path.joinpath("test.tif"), "w", **profile) as dst:
            for chunk in windows.subdivide(
                windows.Window(0, 0, dst.width, dst.height), 256, 256
            ):
                chunk_bounds = windows.bounds(chunk, dst.transform)
                chunk_arr, chunk_transform = merge([src], bounds=chunk_bounds)
                dw = windows.from_bounds(*chunk_bounds, dst.transform)
                dw = dw.round_offsets().round_lengths()
                dst.write(chunk_arr, window=dw)

        with rasterio.open(tmp_path.joinpath("test.tif")) as dst:
            result = dst.read()
            assert result.shape == (3, 719, 792)
            assert numpy.allclose(
                data[data != 0].mean(),
                result[result != 0].mean(),
            )


@pytest.mark.xfail(gdal_version.at_least("3.8"), reason="Unsolved mask read bug #3070.")
def test_complex_merge(test_data_complex):

    with warnings.catch_warnings():
        warnings.simplefilter('error')
        result, _ = merge([test_data_complex/"r2.tif"])
        assert result.dtype == numpy.complex64
        assert numpy.all(result == 1)


def test_complex_nodata(test_data_complex):
    inputs = list(test_data_complex.iterdir())

    with warnings.catch_warnings():
        warnings.simplefilter('error')

        result, _ = merge(inputs, nodata=numpy.nan)
        assert numpy.all(numpy.isnan(result[:, 2]))

        result, _ = merge(inputs, nodata=0-1j)
        assert numpy.all(result[:, 2] == 0-1j)


def test_complex_outrange_nodata_():
    with rasterio.open("tests/data/float_raster_with_nodata.tif") as src:
        with pytest.warns(UserWarning, match="Ignoring nodata value"):
            res, _ = merge([src], nodata=1+1j, dtype='float64')


@pytest.mark.parametrize(
    "matrix",
    [
        affine.Affine.scale(-1, 1),
        affine.Affine.scale(1, -1),
        affine.Affine.rotation(45.0),
    ],
)
def test_failure_source_transforms(data, matrix):
    """Rotated, flipped, and upside down rasters cannot be merged."""
    with rasterio.open(str(data.join("RGB.byte.tif")), "r+") as src:
        src.transform = matrix * src.transform
        with pytest.raises(MergeError):
            merge([src])


def test_merge_warpedvrt(tmp_path):
    """Merge a WarpedVRT into an opened dataset."""
    with rasterio.open("tests/data/RGB.byte.tif") as src:
        with WarpedVRT(src, crs="EPSG:3857") as vrt:
            profile = vrt.profile
            data = vrt.read()
            profile["driver"] = "GTiff"

            with rasterio.open(tmp_path.joinpath("test.tif"), "w", **profile) as dst:
                for chunk in windows.subdivide(
                    windows.Window(0, 0, dst.width, dst.height), 256, 256
                ):
                    chunk_bounds = windows.bounds(chunk, dst.transform)
                    chunk_arr, chunk_transform = merge([vrt], bounds=chunk_bounds)
                    dst_window = windows.from_bounds(*chunk_bounds, dst.transform)
                    dw = windows.from_bounds(*chunk_bounds, dst.transform)
                    dw = dw.round_offsets().round_lengths()
                    dst.write(chunk_arr, window=dw)

    with rasterio.open(tmp_path.joinpath("test.tif")) as dst:
        result = dst.read()
        assert numpy.allclose(data.mean(), result.mean(), rtol=1e-4)

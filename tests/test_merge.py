"""Tests of rasterio.merge"""

import boto3
from hypothesis import given, settings
from hypothesis.strategies import floats
import numpy
import pytest

import affine
import rasterio
from rasterio.merge import merge

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


@pytest.mark.parametrize(
    "method,value", [("first", 1), ("last", 2), ("min", 1), ("max", 3)]
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

"""Tests of rasterio.merge"""

from glob import glob
from xml.etree import ElementTree as ET

import boto3
from hypothesis import given, settings
from hypothesis.strategies import floats
import numpy
import pytest

import affine
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.errors import RasterioError
from rasterio.merge import merge, virtual_merge


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


def test_virtual_merge(tmp_path):
    """Test."""
    xml = virtual_merge(glob("tests/data/rgb?.tif"))
    assert b'resampling="nearest"' in xml

    tmp_path.joinpath("test.vrt").write_bytes(xml)
    with rasterio.open(tmp_path.joinpath("test.vrt")) as dataset:
        rgb = dataset.read()

    import matplotlib.pyplot as plt
    plt.imshow(numpy.moveaxis(rgb, 0, -1))
    plt.savefig("test_virtual_merge.png")


@pytest.mark.parametrize("resampling", [Resampling.nearest, Resampling.bilinear])
def test_virtual_merge_resampling(tmp_path, resampling):
    """Test."""
    xml = virtual_merge(glob("tests/data/rgb?.tif"), resampling=resampling)
    root = ET.fromstring(xml)
    assert all(
        elem.attrib["resampling"] == resampling.name
        for elem in root.findall(".//ComplexSource")
    )
    assert all(
        elem.attrib["resampling"] == resampling.name
        for elem in root.findall(".//SimpleSource")
    )

import affine
import numpy
import pytest

import rasterio


@pytest.mark.xfail(reason="Likely upstream bug")
@pytest.mark.parametrize("nodata", [-1, -128])
def test_write_int8_mem(nodata):
    profile = {
        "driver": "GTiff",
        "width": 2,
        "height": 1,
        "count": 1,
        "dtype": "int8",
        "crs": "EPSG:3857",
        "transform": affine.Affine(10, 0, 0, 0, -10, 0),
        "nodata": nodata,
    }

    values = numpy.array([[nodata, nodata]], dtype="int8")

    with rasterio.open("/vsimem/test.tif", "w", **profile) as src:
        src.write(values, indexes=1)

    with rasterio.open("/vsimem/test.tif") as src:
        read = src.read(indexes=1)
        assert read[0][0] == nodata
        assert read[0][1] == nodata


@pytest.mark.parametrize("nodata", [None, -1, -128])
def test_write_int8_fs(tmp_path, nodata):
    filename = tmp_path.joinpath("test.tif")
    profile = {
        "driver": "GTiff",
        "width": 2,
        "height": 1,
        "count": 1,
        "dtype": "int8",
        "crs": "EPSG:3857",
        "transform": affine.Affine(10, 0, 0, 0, -10, 0),
        "nodata": nodata,
    }

    values = numpy.array([[127, -128]], dtype="int8")

    with rasterio.open(filename, "w", **profile) as src:
        src.write(values, indexes=1)

    with rasterio.open(filename) as src:
        read = src.read(indexes=1)
        assert read[0][0] == 127
        assert read[0][1] == -128

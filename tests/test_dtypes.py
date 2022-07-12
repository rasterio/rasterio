import itertools

import affine
import numpy as np
import pytest

from .conftest import gdal_version

import rasterio
from rasterio import (
    ubyte,
    uint8,
    uint16,
    uint32,
    uint64,
    sbyte,
    int8,
    int16,
    int32,
    int64,
    float32,
    float64,
    complex_,
    complex_int16,
)
from rasterio.dtypes import (
    _gdal_typename,
    is_ndarray,
    check_dtype,
    get_minimum_dtype,
    can_cast_dtype,
    validate_dtype,
    _is_complex_int,
    _getnpdtype,
    _get_gdal_dtype,
)
from rasterio.env import GDALVersion


_GDAL_AT_LEAST_35 = GDALVersion.runtime().at_least("3.5")

DTYPES = [
    ubyte,
    uint8,
    uint16,
    uint32,
    sbyte,
    int8,
    int16,
    int32,
    float32,
    float64,
    complex_,
]

if _GDAL_AT_LEAST_35:
    DTYPES.extend([uint64, int64])


def test_is_ndarray():
    assert is_ndarray(np.zeros((1,)))
    assert not is_ndarray([0])
    assert not is_ndarray((0,))


def test_np_dt_uint8():
    assert check_dtype(np.uint8)


def test_dt_ubyte():
    assert check_dtype(ubyte)


def test_check_dtype_invalid():
    assert not check_dtype('foo')


@pytest.mark.parametrize(
    ("dtype", "name"),
    [
        (ubyte, "Byte"),
        (np.uint8, "Byte"),
        (np.uint16, "UInt16"),
        ("uint8", "Byte"),
        ("complex_int16", "CInt16"),
        (complex_int16, "CInt16"),
    ],
)
def test_gdal_name(dtype, name):
    assert _gdal_typename(dtype) == name


def test_get_minimum_dtype():
    assert get_minimum_dtype([0, 1]) == uint8
    assert get_minimum_dtype([0, 1000]) == uint16
    assert get_minimum_dtype([0, 100000]) == uint32
    assert get_minimum_dtype([-1, 0, 1]) == int16
    assert get_minimum_dtype([-1, 0, 100000]) == int32
    assert get_minimum_dtype([-1.5, 0, 1.5]) == float32
    assert get_minimum_dtype([-1.5e+100, 0, 1.5e+100]) == float64

    assert get_minimum_dtype(np.array([0, 1], dtype=np.uint)) == uint8
    assert get_minimum_dtype(np.array([0, 1000], dtype=np.uint)) == uint16
    assert get_minimum_dtype(np.array([0, 100000], dtype=np.uint)) == uint32
    assert get_minimum_dtype(np.array([-1, 0, 1], dtype=int)) == int16
    assert get_minimum_dtype(np.array([-1, 0, 100000], dtype=int)) == int32
    assert get_minimum_dtype(np.array([-1.5, 0, 1.5], dtype=np.float64)) == float32


def test_get_minimum_dtype__int64():
    if gdal_version.at_least("3.5"):
        assert get_minimum_dtype([-1, 0, 2147483648]) == int64
    else:
        with pytest.raises(ValueError, match="Values out of range for supported dtypes"):
            get_minimum_dtype([-1, 0, 2147483648])


def test_get_minimum_dtype__uint64():
    if gdal_version.at_least("3.5"):
        assert get_minimum_dtype([0, 4294967296]) == uint64
    else:
        with pytest.raises(ValueError, match="Values out of range for supported dtypes"):
            get_minimum_dtype([0, 4294967296])


def test_can_cast_dtype():
    assert can_cast_dtype((1, 2, 3), np.uint8)
    assert can_cast_dtype(np.array([1, 2, 3]), np.uint8)
    assert can_cast_dtype(np.array([1, 2, 3], dtype=np.uint8), np.uint8)
    assert can_cast_dtype(np.array([1, 2, 3]), np.float32)
    assert can_cast_dtype(np.array([1.4, 2.1, 3.65]), np.float32)
    assert not can_cast_dtype(np.array([1.4, 2.1, 3.65]), np.uint8)


@pytest.mark.parametrize("dtype", ["float64", "float32"])
def test_can_cast_dtype_nan(dtype):
    assert can_cast_dtype([np.nan], dtype)


@pytest.mark.parametrize("dtype", ["uint8", "uint16", "uint32", "int32"])
def test_cant_cast_dtype_nan(dtype):
    assert not can_cast_dtype([np.nan], dtype)


def test_validate_dtype():
    assert validate_dtype([1, 2, 3], ('uint8', 'uint16'))
    assert validate_dtype(np.array([1, 2, 3]), ('uint8', 'uint16'))
    assert validate_dtype(np.array([1.4, 2.1, 3.65]), ('float32',))
    assert not validate_dtype(np.array([1.4, 2.1, 3.65]), ('uint8',))


def test_complex(tmpdir):
    name = str(tmpdir.join("complex.tif"))
    arr1 = np.ones((2, 2), dtype=complex_)
    profile = dict(driver='GTiff', width=2, height=2, count=1, dtype=complex_)

    with rasterio.open(name, 'w', **profile) as dst:
        dst.write(arr1, 1)

    with rasterio.open(name) as src:
        arr2 = src.read(1)

    assert np.array_equal(arr1, arr2)


def test_is_complex_int():
    assert _is_complex_int("complex_int16")


def test_not_is_complex_int():
    assert not _is_complex_int("complex")


def test_get_npdtype():
    npdtype = _getnpdtype("complex_int16")
    assert npdtype == np.complex64
    assert npdtype.kind == "c"


def test__get_gdal_dtype__int64():
    if gdal_version.at_least("3.5"):
        assert _get_gdal_dtype("int64") == 12
    else:
        with pytest.raises(TypeError, match="Unsupported data type"):
            _get_gdal_dtype("int64")


@pytest.mark.parametrize("dtype,nodata", itertools.product(DTYPES, [1, 127]))
def test_write_mem(dtype, nodata):
    profile = {
        "driver": "GTiff",
        "width": 2,
        "height": 1,
        "count": 1,
        "dtype": dtype,
        "crs": "EPSG:3857",
        "transform": affine.Affine(10, 0, 0, 0, -10, 0),
        "nodata": nodata,
    }

    values = np.array([[nodata, nodata]], dtype=dtype)

    with rasterio.open("/vsimem/test.tif", "w", **profile) as src:
        src.write(values, indexes=1)

    with rasterio.open("/vsimem/test.tif") as src:
        read = src.read(indexes=1)
        assert read[0][0] == nodata
        assert read[0][1] == nodata


@pytest.mark.parametrize("dtype,nodata", itertools.product(DTYPES, [None, 1, 127]))
def test_write_fs(tmp_path, dtype, nodata):
    filename = tmp_path.joinpath("test.tif")
    profile = {
        "driver": "GTiff",
        "width": 2,
        "height": 1,
        "count": 1,
        "dtype": dtype,
        "crs": "EPSG:3857",
        "transform": affine.Affine(10, 0, 0, 0, -10, 0),
        "nodata": nodata,
    }

    if dtype.startswith('int') or dtype.startswith('uint'):
        info = np.iinfo(dtype)
    else:
        info = np.finfo(dtype)
    values = np.array([[info.max, info.min]], dtype=dtype)

    with rasterio.open(filename, "w", **profile) as src:
        src.write(values, indexes=1)

    with rasterio.open(filename) as src:
        read = src.read(indexes=1)
        assert read[0][0] == info.max
        assert read[0][1] == info.min

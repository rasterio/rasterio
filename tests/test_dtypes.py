import numpy as np
import pytest

import rasterio
from rasterio import (
    ubyte,
    uint8,
    uint16,
    uint32,
    int16,
    int32,
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
)


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

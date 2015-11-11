import numpy as np

from rasterio import (
    ubyte, uint8, uint16, uint32, int16, int32, float32, float64)
from rasterio.dtypes import (
    _gdal_typename, is_ndarray, check_dtype, get_minimum_dtype, can_cast_dtype,
    validate_dtype
)


def test_is_ndarray():
    assert is_ndarray(np.zeros((1,)))
    assert is_ndarray([0]) == False
    assert is_ndarray((0,)) == False


def test_np_dt_uint8():
    assert check_dtype(np.uint8)


def test_dt_ubyte():
    assert check_dtype(ubyte)


def test_check_dtype_invalid():
    assert check_dtype('foo') == False


def test_gdal_name():
    assert _gdal_typename(ubyte) == 'Byte'
    assert _gdal_typename(np.uint8) == 'Byte'
    assert _gdal_typename(np.uint16) == 'UInt16'


def test_get_minimum_dtype():
    assert get_minimum_dtype([0, 1]) == uint8
    assert get_minimum_dtype([0, 1000]) == uint16
    assert get_minimum_dtype([0, 100000]) == uint32
    assert get_minimum_dtype([-1, 0, 1]) == int16
    assert get_minimum_dtype([-1, 0, 100000]) == int32
    assert get_minimum_dtype([-1.5, 0, 1.5]) == float32
    assert get_minimum_dtype([-1.5e+100, 0, 1.5e+100]) == float64


def test_can_cast_dtype():
    assert can_cast_dtype((1, 2, 3), np.uint8) == True
    assert can_cast_dtype(np.array([1, 2, 3]), np.uint8) == True
    assert can_cast_dtype(np.array([1, 2, 3], dtype=np.uint8), np.uint8) == True
    assert can_cast_dtype(np.array([1, 2, 3]), np.float32) == True
    assert can_cast_dtype(np.array([1.4, 2.1, 3.65]), np.float32) == True
    assert can_cast_dtype(np.array([1.4, 2.1, 3.65]), np.uint8) == False


def test_validate_dtype():
    assert validate_dtype([1, 2, 3], ('uint8', 'uint16')) == True
    assert validate_dtype(np.array([1, 2, 3]), ('uint8', 'uint16')) == True
    assert validate_dtype(np.array([1.4, 2.1, 3.65]), ('float32',)) == True
    assert validate_dtype(np.array([1.4, 2.1, 3.65]),('uint8',)) == False

import numpy as np

from rasterio import dtypes, ubyte


def test_is_ndarray():
    assert dtypes.is_ndarray(np.zeros((1,)))
    assert dtypes.is_ndarray([0]) == False
    assert dtypes.is_ndarray((0,)) == False


def test_np_dt_uint8():
    assert dtypes.check_dtype(np.uint8)


def test_dt_ubyte():
    assert dtypes.check_dtype(ubyte)


def test_gdal_name():
    assert dtypes._gdal_typename(ubyte) == 'Byte'
    assert dtypes._gdal_typename(np.uint8) == 'Byte'
    assert dtypes._gdal_typename(np.uint16) == 'UInt16'

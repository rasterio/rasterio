import numpy as np

import rasterio.dtypes

def test_np_dt_uint8():
    assert rasterio.dtypes.check_dtype(np.uint8)

def test_dt_ubyte():
    assert rasterio.dtypes.check_dtype(rasterio.ubyte)

def test_gdal_name():
    assert rasterio.dtypes._gdal_typename(rasterio.ubyte) == 'Byte'
    assert rasterio.dtypes._gdal_typename(np.uint8) == 'Byte'
    assert rasterio.dtypes._gdal_typename(np.uint16) == 'UInt16'

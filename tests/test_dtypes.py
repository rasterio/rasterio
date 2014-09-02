import numpy

import rasterio
import rasterio.dtypes

def test_np_dt_uint8():
    assert rasterio.check_dtype(numpy.dtype(numpy.uint8))

def test_dt_ubyte():
    assert rasterio.check_dtype(numpy.dtype(rasterio.ubyte))

def test_gdal_name():
    assert rasterio.dtypes._gdal_typename(rasterio.ubyte) == 'Byte'
    assert rasterio.dtypes._gdal_typename(numpy.uint8) == 'Byte'
    assert rasterio.dtypes._gdal_typename(numpy.uint16) == 'UInt16'


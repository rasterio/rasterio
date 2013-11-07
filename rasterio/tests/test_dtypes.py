import numpy

import rasterio

def test_np_dt_uint8():
    assert rasterio.check_dtype(numpy.dtype(numpy.uint8))
def test_dt_ubyte():
    assert rasterio.check_dtype(numpy.dtype(rasterio.ubyte))


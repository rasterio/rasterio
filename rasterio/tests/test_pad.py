
import numpy
import rasterio

def pad(array, transform, pad_width, mode, **kwds):
    padded_array = numpy.pad(array, pad_width, mode, **kwds)
    padded_trans = list(transform)
    padded_trans[2] -= pad_width*padded_trans[0]
    padded_trans[5] -= pad_width*padded_trans[4]
    return padded_array, rasterio.AffineMatrix(*padded_trans)

def test_pad():
    arr = numpy.ones((10, 10))
    trans = rasterio.AffineMatrix(1.0, 0.0, 0.0, 0.0, -1.0, 10.0)
    arr2, trans2 = pad(arr, trans, 2, 'edge')
    assert arr2.shape == (14, 14)
    assert trans2.xoff ==  -2.0
    assert trans2.yoff ==  12.0

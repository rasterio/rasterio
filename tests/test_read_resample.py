import numpy

import rasterio


# Rasterio exposes GDAL's resampling/decimation on I/O. These are the tests
# that it does this correctly.
#
# Rasterio's test dataset is 718 rows by 791 columns.

def test_read_out_shape_resample_down():
    with rasterio.open('tests/data/RGB.byte.tif') as s:
        out = numpy.zeros((8, 8), dtype=rasterio.ubyte)
        data = s.read(1, out=out)
        expected = numpy.array([
            [  0,   0,  20,  15,   0,   0,   0,   0],
            [  0,   6, 193,   9, 255, 127,  23,  39],
            [  0,   7,  27, 255, 193,  14,  28,  34],
            [  0,  31,  29,  44,  14,  22,  43,   0],
            [  0,   9,  69,  49,  17,  22, 255,   0],
            [ 11,   7,  13,  25,  13,  29,  33,   0],
            [  8,  10,  88,  27,  20,  33,  25,   0],
            [  0,   0,   0,   0,  98,  23,   0,   0]], dtype=numpy.uint8)
        assert (data == expected).all() # all True.


def test_read_out_shape_resample_up():
    # Instead of testing array items, test statistics. Upsampling by an even
    # constant factor shouldn't change the mean.
    with rasterio.open('tests/data/RGB.byte.tif') as s:
        out = numpy.zeros((7180, 7910), dtype=rasterio.ubyte)
        data = s.read(1, out=out, masked=True)
        assert data.shape == (7180, 7910)
        assert data.mean() == s.read(1, masked=True).mean()


def test_read_downsample_alpha():
    with rasterio.Env(GTIFF_IMPLICIT_JPEG_OVR=False):
        with rasterio.open('tests/data/alpha.tif') as src:
            out = numpy.zeros((100, 100), dtype=rasterio.ubyte)
            assert src.width == 1223
            assert src.height == 1223
            assert src.count == 4
            assert src.read(1, out=out, masked=False).shape == out.shape
            # attempt decimated read of alpha band
            src.read(4, out=out, masked=False)

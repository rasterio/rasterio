import numpy

import rasterio


# Rasterio exposes GDAL's resampling/decimation on I/O. These are the tests
# that it does this correctly.
#
# Rasterio's test dataset is 718 rows by 791 columns.

def test_read_out_shape_resample_down():
    with rasterio.open('tests/data/RGB.byte.tif') as s:
        out = numpy.zeros((7, 8), dtype=rasterio.ubyte)
        data = s.read(1, out=out)
        expected = numpy.array([
            [  0,   8,   5,   7,   0,   0,   0,   0],
            [  0,   6,  61,  15,  27,  15,  24, 128],
            [  0,  20, 152,  23,  15,  19,  28,   0],
            [  0,  17, 255,  25, 255,  22,  32,   0],
            [  9,   7,  14,  16,  19,  18,  36,   0],
            [  6,  27,  43, 207,  38,  31,  73,   0],
            [  0,   0,   0,   0,  74,  23,   0,   0]], dtype=numpy.uint8)
        assert (data == expected).all() # all True.


def test_read_out_shape_resample_up():
    # Instead of testing array items, test statistics. Upsampling by an even
    # constant factor shouldn't change the mean.
    with rasterio.open('tests/data/RGB.byte.tif') as s:
        out = numpy.zeros((7180, 7910), dtype=rasterio.ubyte)
        data = s.read(1, out=out, masked=True)
        assert data.shape == (7180, 7910)
        assert data.mean() == s.read(1, masked=True).mean()

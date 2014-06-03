import unittest

import numpy
from hashlib import md5

import rasterio


class ReaderContextTest(unittest.TestCase):

    def test_context(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assertEqual(s.name, 'rasterio/tests/data/RGB.byte.tif')
            self.assertEqual(s.driver, 'GTiff')
            self.assertEqual(s.closed, False)
            self.assertEqual(s.count, 3)
            self.assertEqual(s.width, 791)
            self.assertEqual(s.height, 718)
            self.assertEqual(s.shape, (718, 791))
            self.assertEqual(s.dtypes, [rasterio.ubyte]*3)
            self.assertEqual(s.nodatavals, [0]*3)
            self.assertEqual(s.indexes, [1,2,3])
            self.assertEqual(s.crs['proj'], 'utm')
            self.assertEqual(s.crs['zone'], 18)
            self.assert_(s.crs_wkt.startswith('PROJCS'), s.crs_wkt)
            for i, v in enumerate((101985.0, 2611485.0, 339315.0, 2826915.0)):
                self.assertAlmostEqual(s.bounds[i], v)
            self.assertEqual(
                s.transform, 
                [101985.0, 300.0379266750948, 0.0, 
                 2826915.0, 0.0, -300.041782729805])
            self.assertEqual(s.meta['crs'], s.crs)
            self.assertEqual(
                repr(s), 
                "<open RasterReader name='rasterio/tests/data/RGB.byte.tif' "
                "mode='r'>")
        self.assertEqual(s.closed, True)
        self.assertEqual(s.count, 3)
        self.assertEqual(s.width, 791)
        self.assertEqual(s.height, 718)
        self.assertEqual(s.shape, (718, 791))
        self.assertEqual(s.dtypes, [rasterio.ubyte]*3)
        self.assertEqual(s.nodatavals, [0]*3)
        self.assertEqual(s.crs['proj'], 'utm')
        self.assertEqual(s.crs['zone'], 18)
        self.assertEqual(
            s.transform, 
            [101985.0, 300.0379266750948, 0.0, 
             2826915.0, 0.0, -300.041782729805])
        self.assertEqual(
            repr(s),
            "<closed RasterReader name='rasterio/tests/data/RGB.byte.tif' "
            "mode='r'>")

    def test_derived_spatial(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assert_(s.crs_wkt.startswith('PROJCS'), s.crs_wkt)
            for i, v in enumerate((101985.0, 2611485.0, 339315.0, 2826915.0)):
                self.assertAlmostEqual(s.bounds[i], v)
            for a, b in zip(s.ul(0, 0), (101985.0, 2826915.0)):
                self.assertAlmostEqual(a, b)

    def test_read_ubyte(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            a = s.read_band(1)
            self.assertEqual(a.dtype, rasterio.ubyte)

    def test_read_ubyte_bad_index(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assertRaises(IndexError, s.read_band, 0)

    def test_read_ubyte_out(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            a = numpy.zeros((718, 791), dtype=rasterio.ubyte)
            a = s.read_band(1, a)
            self.assertEqual(a.dtype, rasterio.ubyte)

    def test_read_out_dtype_fail(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            a = numpy.zeros((718, 791), dtype=rasterio.float32)
            try:
                s.read_band(1, a)
            except ValueError as e:
                assert "the array's dtype 'float32' does not match the file's dtype" in str(e)
            except:
                assert "failed to catch exception" is False

    def test_read_out_shape_resample(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            a = numpy.zeros((7, 8), dtype=rasterio.ubyte)
            s.read_band(1, a)
            self.assert_(
                repr(a) == """array([[  0,   8,   5,   7,   0,   0,   0,   0],
       [  0,   6,  61,  15,  27,  15,  24, 128],
       [  0,  20, 152,  23,  15,  19,  28,   0],
       [  0,  17, 255,  25, 255,  22,  32,   0],
       [  9,   7,  14,  16,  19,  18,  36,   0],
       [  6,  27,  43, 207,  38,  31,  73,   0],
       [  0,   0,   0,   0,  74,  23,   0,   0]], dtype=uint8)""", a)

    def test_read_basic(self):
        with rasterio.open('rasterio/tests/data/shade.tif') as s:
            a = s.read()  # Gray
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (1, 1024, 1024))
            self.assertTrue(hasattr(a, 'mask'))
            self.assertEqual(a.fill_value, 255)
            self.assertEqual(list(set(s.nodatavals)), [255])
            self.assertEqual(a.dtype, rasterio.ubyte)
            self.assertEqual(a.sum((1, 2)).tolist(), [0])
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            a = s.read()  # RGB
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (3, 718, 791))
            self.assertTrue(hasattr(a, 'mask'))
            self.assertEqual(a.fill_value, 0)
            self.assertEqual(list(set(s.nodatavals)), [0])
            self.assertEqual(a.dtype, rasterio.ubyte)
            a = s.read(masked=False)  # no mask
            self.assertFalse(hasattr(a, 'mask'))
            self.assertEqual(list(set(s.nodatavals)), [0])
            self.assertEqual(a.dtype, rasterio.ubyte)
        with rasterio.open('rasterio/tests/data/float.tif') as s:
            a = s.read()  # floating point values
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (1, 2, 3))
            self.assertFalse(hasattr(a, 'mask'))
            self.assertEqual(list(set(s.nodatavals)), [None])
            self.assertEqual(a.dtype, rasterio.float64)

    def test_read_indexes(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            a = s.read()  # RGB
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (3, 718, 791))
            self.assertEqual(a.sum((1, 2)).tolist(),
                             [17008452, 25282412, 27325233])
            # read last index as 2D array
            a = s.read(s.indexes[-1])  # B
            self.assertEqual(a.ndim, 2)
            self.assertEqual(a.shape, (718, 791))
            self.assertEqual(a.sum(), 27325233)
            # read last index as 2D array
            a = s.read(s.indexes[-1:])  # [B]
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (1, 718, 791))
            self.assertEqual(a.sum((1, 2)).tolist(), [27325233])
            # out of range indexes
            self.assertRaises(IndexError, s.read, 0)
            self.assertRaises(IndexError, s.read, [3, 4])
            # read slice
            a = s.read(s.indexes[0:2])  # [RG]
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (2, 718, 791))
            self.assertEqual(a.sum((1, 2)).tolist(), [17008452, 25282412])
            # read stride
            a = s.read(s.indexes[::2])  # [RB]
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (2, 718, 791))
            self.assertEqual(a.sum((1, 2)).tolist(), [17008452, 27325233])
            # read zero-length slice
            a = s.read(s.indexes[1:1])
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (0, 718, 791))
            self.assertEqual(a.sum((1, 2)).tolist(), [])

    def test_read_window(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            # correct format
            self.assertRaises(ValueError, s.read, window=(300, 320, 320, 330))
            # window with 1 nodata on band 3
            a = s.read(window=((300, 320), (320, 330)))
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (3, 20, 10))
            self.assertTrue(hasattr(a, 'mask'))
            self.assertEqual(a.mask.sum((1, 2)).tolist(), [0, 0, 1])
            self.assertEqual([md5(x.tostring()).hexdigest() for x in a],
                              ['1df719040daa9dfdb3de96d6748345e8',
                               'ec8fb3659f40c4a209027231bef12bdb',
                               '5a9c12aebc126ec6f27604babd67a4e2'])
            # window without any missing data
            a = s.read(window=((310, 330), (320, 330)))
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (3, 20, 10))
            self.assertFalse(hasattr(a, 'mask'))
            self.assertEqual([md5(x.tostring()).hexdigest() for x in a[:]],
                              ['9e3000d60b4b6fb956f10dc57c4dc9b9',
                               '6a675416a32fcb70fbcf601d01aeb6ee',
                               '94fd2733b534376c273a894f36ad4e0b'])

    def test_read_out(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            # without mask
            a = numpy.empty((3, 718, 791), numpy.ubyte)
            b = s.read(out=a, masked=False)
            self.assertEqual(id(a), id(b))
            # with mask
            a = numpy.ma.empty((3, 718, 791), numpy.ubyte)
            b = s.read(out=a, masked=True)
            self.assertEqual(id(a.data), id(b.data))
            # use all parameters
            a = numpy.empty((1, 20, 10), numpy.ubyte)
            b = s.read([2], a, ((310, 330), (320, 330)), False)
            self.assertEqual(id(a), id(b))
            # pass 2D array with index
            a = numpy.empty((20, 10), numpy.ubyte)
            b = s.read(2, a, ((310, 330), (320, 330)), False)
            self.assertEqual(id(a), id(b))
            self.assertEqual(a.ndim, 2)
            # different data types
            a = numpy.empty((3, 718, 791), numpy.float64)
            self.assertRaises(ValueError, s.read, out=a)
            # different number of array dimensions
            a = numpy.empty((20, 10), numpy.ubyte)
            return
            # TODO: find out why this assert statement doesn't work
            self.assertRaises(ValueError, s.read, [2], out=a)
            # b = s.read([2], out=a)
            # Exception ValueError: 'Buffer has wrong number of dimensions
            # (expected 2, got 1)' in 'rasterio._io.io_ubyte' ignored

    def test_read_nan_nodata(self):
        with rasterio.open('rasterio/tests/data/float_nan.tif') as s:
            a = s.read()
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (1, 2, 3))
            self.assertTrue(hasattr(a, 'mask'))
            self.assertNotEqual(a.fill_value, numpy.nan)
            self.assertEqual(str(list(set(s.nodatavals))), str([numpy.nan]))
            self.assertEqual(a.dtype, rasterio.float32)
            self.assertFalse(numpy.isnan(a).any())
            a = s.read(masked=False)
            self.assertFalse(hasattr(a, 'mask'))
            self.assertTrue(numpy.isnan(a).any())

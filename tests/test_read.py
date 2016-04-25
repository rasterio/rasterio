import logging
import sys
import unittest

import numpy
from hashlib import md5

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


class ReaderContextTest(unittest.TestCase):

    def test_context(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            self.assertEqual(s.name, 'tests/data/RGB.byte.tif')
            self.assertEqual(s.driver, 'GTiff')
            self.assertEqual(s.closed, False)
            self.assertEqual(s.count, 3)
            self.assertEqual(s.width, 791)
            self.assertEqual(s.height, 718)
            self.assertEqual(s.shape, (3, 718, 791))
            self.assertEqual(s.dtypes, tuple([rasterio.ubyte] * 3))
            self.assertEqual(s.nodatavals, (0, 0, 0))
            self.assertEqual(s.indexes, (1, 2, 3))
            self.assertEqual(s.crs['init'], 'epsg:32618')
            self.assert_(s.crs_wkt.startswith('PROJCS'), s.crs_wkt)
            for i, v in enumerate((101985.0, 2611485.0, 339315.0, 2826915.0)):
                self.assertAlmostEqual(s.bounds[i], v)
            self.assertEqual(
                s.affine, 
                (300.0379266750948, 0.0, 101985.0,
                 0.0, -300.041782729805, 2826915.0,
                 0, 0, 1.0))
            self.assertEqual(s.meta['crs'], s.crs)
            self.assertEqual(
                repr(s), 
                "<open RasterReader name='tests/data/RGB.byte.tif' "
                "mode='r'>")
        self.assertEqual(s.closed, True)
        self.assertEqual(s.count, 3)
        self.assertEqual(s.width, 791)
        self.assertEqual(s.height, 718)
        self.assertEqual(s.shape, (3, 718, 791))
        self.assertEqual(s.dtypes, tuple([rasterio.ubyte] * 3))
        self.assertEqual(s.nodatavals, (0, 0, 0))
        self.assertEqual(s.crs['init'], 'epsg:32618')
        self.assertEqual(
            s.affine, 
            (300.0379266750948, 0.0, 101985.0,
             0.0, -300.041782729805, 2826915.0,
             0, 0, 1.0))
        self.assertEqual(
            repr(s),
            "<closed RasterReader name='tests/data/RGB.byte.tif' "
            "mode='r'>")

    def test_derived_spatial(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            self.assert_(s.crs_wkt.startswith('PROJCS'), s.crs_wkt)
            for i, v in enumerate((101985.0, 2611485.0, 339315.0, 2826915.0)):
                self.assertAlmostEqual(s.bounds[i], v)
            for a, b in zip(s.ul(0, 0), (101985.0, 2826915.0)):
                self.assertAlmostEqual(a, b)

    def test_read_ubyte(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = s.read(1)
            self.assertEqual(a.dtype, rasterio.ubyte)

    def test_read_ubyte_bad_index(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            self.assertRaises(IndexError, s.read, 0)

    def test_read_ubyte_out(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = numpy.zeros((718, 791), dtype=rasterio.ubyte)
            a = s.read(1, a)
            self.assertEqual(a.dtype, rasterio.ubyte)

    def test_read_out_dtype_fail(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = numpy.zeros((718, 791), dtype=rasterio.float32)
            try:
                s.read(1, a)
            except ValueError as e:
                assert "the array's dtype 'float32' does not match the file's dtype" in str(e)
            except:
                assert "failed to catch exception" is False

    def test_read_basic(self):
        with rasterio.open('tests/data/shade.tif') as s:
            a = s.read(masked=True)  # Gray
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (1, 1024, 1024))
            self.assertTrue(hasattr(a, 'mask'))
            self.assertEqual(a.fill_value, 255)
            self.assertEqual(list(set(s.nodatavals)), [255])
            self.assertEqual(a.dtype, rasterio.ubyte)
            self.assertEqual(a.sum((1, 2)).tolist(), [0])
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = s.read(masked=True)  # RGB
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
        with rasterio.open('tests/data/float.tif') as s:
            a = s.read(masked=True)  # floating point values
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (1, 2, 3))
            self.assert_(hasattr(a, 'mask'))
            self.assertEqual(list(set(s.nodatavals)), [None])
            self.assertEqual(a.dtype, rasterio.float64)

    def test_read_indexes(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
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
            try:
                a = s.read(s.indexes[1:1])
            except ValueError:
                pass

    def test_read_window(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            # correct format
            self.assertRaises(ValueError, s.read, window=(300, 320, 320, 330))
            # window with 1 nodata on band 3
            a = s.read(window=((300, 320), (320, 330)), masked=True)
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (3, 20, 10))
            self.assertTrue(hasattr(a, 'mask'))
            self.assertEqual(a.mask.sum((1, 2)).tolist(), [0, 0, 1])
            self.assertEqual([md5(x.tostring()).hexdigest() for x in a],
                              ['1df719040daa9dfdb3de96d6748345e8',
                               'ec8fb3659f40c4a209027231bef12bdb',
                               '5a9c12aebc126ec6f27604babd67a4e2'])
            # window without any missing data, but still is masked result
            a = s.read(window=((310, 330), (320, 330)), masked=True)
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (3, 20, 10))
            self.assertTrue(hasattr(a, 'mask'))
            self.assertEqual([md5(x.tostring()).hexdigest() for x in a[:]],
                              ['9e3000d60b4b6fb956f10dc57c4dc9b9',
                               '6a675416a32fcb70fbcf601d01aeb6ee',
                               '94fd2733b534376c273a894f36ad4e0b'])

    def test_read_window_overflow(self):
        """Test graceful Numpy-like handling of windows that overflow
        the dataset's bounds."""
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = s.read(window=((None, 20000), (None, 20000)))
            self.assertEqual(a.shape, s.shape)

    def test_read_window_beyond(self):
        """Test graceful Numpy-like handling of windows beyond
        the dataset's bounds."""
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = s.read(window=((10000, 20000), (10000, 20000)))
            self.assertEqual(a.shape, (3,0,0))

    def test_read_window_overlap(self):
        """Test graceful Numpy-like handling of windows beyond
        the dataset's bounds."""
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = s.read(window=((-100, 20000), (-100, 20000)))
            self.assertEqual(a.shape, (3,100,100))

    def test_read_out(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            # regular array, without mask
            a = numpy.empty((3, 718, 791), numpy.ubyte)
            b = s.read(out=a)
            self.assertFalse(hasattr(a, 'mask'))
            self.assertFalse(hasattr(b, 'mask'))
            # with masked array
            a = numpy.ma.empty((3, 718, 791), numpy.ubyte)
            b = s.read(out=a)
            self.assertEqual(id(a.data), id(b.data))
            # TODO: is there a way to id(a.mask)?
            self.assertTrue(hasattr(a, 'mask'))
            self.assertTrue(hasattr(b, 'mask'))
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
            self.assertRaises(ValueError, s.read, [2], out=a)
            # different number of array shape in 3D
            a = numpy.empty((2, 20, 10), numpy.ubyte)
            self.assertRaises(ValueError, s.read, [2], out=a)

    def test_read_nan_nodata(self):
        with rasterio.open('tests/data/float_nan.tif') as s:
            a = s.read(masked=True)
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
            # Window does not contain a nodatavalue, result is still masked
            a = s.read(window=((0, 2), (0, 2)), masked=True)
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (1, 2, 2))
            self.assertTrue(hasattr(a, 'mask'))

    def test_read_no_band(self):
        with rasterio.open('tests/data/no_band.h5') as s:
            self.assertEqual(s.count, 0)
            self.assertEqual(s.meta['dtype'], 'float_')
            self.assertIsNone(s.meta['nodata'])
            self.assertRaises(ValueError, s.read)

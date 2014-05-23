import unittest

import numpy

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
                (300.0379266750948, 0.0, 101985.0,
                 0.0, -300.041782729805, 2826915.0,
                 0, 0, 1.0))
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
            (300.0379266750948, 0.0, 101985.0,
             0.0, -300.041782729805, 2826915.0,
             0, 0, 1.0))
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


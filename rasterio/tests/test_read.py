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
            self.assertEqual(s.indexes, [1,2,3])
            self.assertEqual(s.crs['proj'], 'utm')
            self.assertEqual(s.crs['zone'], 18)
            self.assertEqual(
                s.transform, 
                [101985.0, 300.0379266750948, 0.0, 
                 2826915.0, 0.0, -300.041782729805])
            self.assertEqual(s.meta['crs'], s.crs)
            self.assertEqual(
                repr(s), 
                "<open RasterReader 'rasterio/tests/data/RGB.byte.tif' "
                "at %s>" % hex(id(s)))
        self.assertEqual(s.closed, True)
        self.assertEqual(s.count, 3)
        self.assertEqual(s.width, 791)
        self.assertEqual(s.height, 718)
        self.assertEqual(s.shape, (718, 791))
        self.assertEqual(s.dtypes, [rasterio.ubyte]*3)
        self.assertEqual(s.crs['proj'], 'utm')
        self.assertEqual(s.crs['zone'], 18)
        self.assertEqual(
            s.transform, 
            [101985.0, 300.0379266750948, 0.0, 
             2826915.0, 0.0, -300.041782729805])
        self.assertEqual(
            repr(s),
            "<closed RasterReader 'rasterio/tests/data/RGB.byte.tif' "
            "at %s>" % hex(id(s)))
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
            self.assertRaises(ValueError, s.read_band, 1, a)
    def test_read_out_shape_fail(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            a = numpy.zeros((42, 42), dtype=rasterio.ubyte)
            self.assertRaises(ValueError, s.read_band, 1, a)


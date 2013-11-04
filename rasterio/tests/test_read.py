import unittest

import rasterio

class ReaderContextTest(unittest.TestCase):
    def test_context(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assertEqual(s.name, 'rasterio/tests/data/RGB.byte.tif')
            self.assertEqual(s.closed, False)
            self.assertEqual(s.count, 3)
            self.assertEqual(s.width, 791)
            self.assertEqual(s.height, 718)
            self.assertEqual(s.shape, (718, 791))
            self.assertEqual(
                repr(s), 
                "<open RasterReader 'rasterio/tests/data/RGB.byte.tif' "
                "at %s>" % hex(id(s)))
        self.assertEqual(s.closed, True)
        self.assertEqual(s.count, 3)
        self.assertEqual(s.width, 791)
        self.assertEqual(s.height, 718)
        self.assertEqual(s.shape, (718, 791))
        self.assertEqual(
            repr(s),
            "<closed RasterReader 'rasterio/tests/data/RGB.byte.tif' "
            "at %s>" % hex(id(s)))


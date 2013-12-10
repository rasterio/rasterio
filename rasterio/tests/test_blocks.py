import unittest

import rasterio

class RasterBlocksTest(unittest.TestCase):
    def test_blocks(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            blocks = list(s.blocks)
            self.assertEqual(len(blocks), 1)


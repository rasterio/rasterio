import unittest

import rasterio

class RasterBlocksTest(unittest.TestCase):
    def test_blocks(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assertEqual(len(s.block_shapes), 3)
            self.assertEqual(s.block_shapes, [(3, 791), (3, 791), (3, 791)])
            blocks = list(s.blocks(1))
            self.assertEqual(blocks[0], (0, 0, 791, 3))
            self.assertEqual(blocks[1], (0, 3, 791, 3))
            self.assertEqual(blocks[~0], (0, 717, 791, 1))


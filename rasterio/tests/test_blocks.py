import unittest

import rasterio

class RasterBlocksTest(unittest.TestCase):
    def test_blocks(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assertEqual(len(s.block_shapes), 3)
            self.assertEqual(s.block_shapes, [(3, 791), (3, 791), (3, 791)])
            windows = s.block_windows(1)
            first = next(windows)
            self.assertEqual(first, (0, 0, 791, 3))
            second = next(windows)
            self.assertEqual(second, (0, 3, 791, 3))
            last = list(windows)[~0]
            self.assertEqual(last, (0, 717, 791, 1))


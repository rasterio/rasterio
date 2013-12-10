import logging
import os.path
import unittest
import shutil
import subprocess
import sys
import tempfile

import numpy

import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

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
    def test_block_coverage(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assertEqual(
                s.width*s.height,
                sum(b[2]*b[3] for b in s.block_windows(1)))

class WindowReadTest(unittest.TestCase):
    def test_read_window(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            windows = s.block_windows(1)
            first_window = next(windows)
            first_block = s.read_band(1, window=first_window)
            self.assertEqual(first_block.dtype, rasterio.ubyte)
            self.assertEqual(first_block.shape[::-1], first_window[2:])

class WindowWriteTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
    def tearDown(self):
        shutil.rmtree(self.tempdir)
    def test_write_window(self):
        name = os.path.join(self.tempdir, "test_write_window.tif")
        a = numpy.ones((50, 50), dtype=rasterio.ubyte) * 127
        with rasterio.open(
                name, 'w', 
                driver='GTiff', width=100, height=100, count=1, 
                dtype=a.dtype) as s:
            s.write_band(1, a, window=(30, 10, 50, 50))
        info = subprocess.check_output(["gdalinfo", "-stats", name])
        self.assert_(
            "Minimum=0.000, Maximum=127.000, "
            "Mean=31.750, StdDev=54.993" in info.decode('utf-8'),
            info)


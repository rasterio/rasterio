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
            (j,i), first = next(windows)
            self.assertEqual((j,i), (0, 0))
            self.assertEqual(first, (0, 0, 3, 791))
            (j, i), second = next(windows)
            self.assertEqual((j,i), (1, 0))
            self.assertEqual(second, (3, 0, 3, 791))
            (j, i), last = list(windows)[~0]
            self.assertEqual((j,i), (239, 0))
            self.assertEqual(last, (717, 0, 1, 791))
    def test_block_coverage(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assertEqual(
                s.width*s.height,
                sum(w[2]*w[3] for ji, w in s.block_windows(1)))

class WindowReadTest(unittest.TestCase):
    def test_read_window(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            windows = s.block_windows(1)
            ji, first_window = next(windows)
            first_block = s.read_band(1, window=first_window)
            self.assertEqual(first_block.dtype, rasterio.ubyte)
            self.assertEqual(first_block.shape, first_window[2:])

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


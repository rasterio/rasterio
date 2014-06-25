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

class WindowTest(unittest.TestCase):
    def test_window_shape_errors(self):
        # Positive height and width are needed when stop is None.
        self.assertRaises(
            ValueError,
            rasterio.window_shape, 
            (((10, 20),(10, None)),) )
        self.assertRaises(
            ValueError,
            rasterio.window_shape, 
            (((None, 10),(10, 20)),) )
    def test_window_shape_None_start(self):
        self.assertEqual(
            rasterio.window_shape(((None,4),(None,102))),
            (4, 102))
    def test_window_shape_None_stop(self):
        self.assertEqual(
            rasterio.window_shape(((10, None),(10, None)), 100, 90),
            (90, 80))
    def test_window_shape_positive(self):
        self.assertEqual(
            rasterio.window_shape(((0,4),(1,102))),
            (4, 101))
    def test_window_shape_negative(self):
        self.assertEqual(
            rasterio.window_shape(((-10, None),(-10, None)), 100, 90),
            (10, 10))
        self.assertEqual(
            rasterio.window_shape(((~0, None),(~0, None)), 100, 90),
            (1, 1))
        self.assertEqual(
            rasterio.window_shape(((None, ~0),(None, ~0)), 100, 90),
            (99, 89))
    def test_eval(self):
        self.assertEqual(
            rasterio.eval_window(((-10, None), (-10, None)), 100, 90),
            ((90, 100), (80, 90)))
        self.assertEqual(
            rasterio.eval_window(((None, -10), (None, -10)), 100, 90),
            ((0, 90), (0, 80)))

def test_window_index():
    idx = rasterio.window_index(((0,4),(1,12)))
    assert len(idx) == 2
    r, c = idx
    assert r.start == 0
    assert r.stop == 4
    assert c.start == 1
    assert c.stop == 12
    arr = numpy.ones((20,20))
    assert arr[idx].shape == (4, 11)

class RasterBlocksTest(unittest.TestCase):
    def test_blocks(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assertEqual(len(s.block_shapes), 3)
            self.assertEqual(s.block_shapes, [(3, 791), (3, 791), (3, 791)])
            windows = s.block_windows(1)
            (j,i), first = next(windows)
            self.assertEqual((j,i), (0, 0))
            self.assertEqual(first, ((0, 3), (0, 791)))
            windows = s.block_windows()
            (j,i), first = next(windows)
            self.assertEqual((j,i), (0, 0))
            self.assertEqual(first, ((0, 3), (0, 791)))
            (j, i), second = next(windows)
            self.assertEqual((j,i), (1, 0))
            self.assertEqual(second, ((3, 6), (0, 791)))
            (j, i), last = list(windows)[~0]
            self.assertEqual((j,i), (239, 0))
            self.assertEqual(last, ((717, 718), (0, 791)))
    def test_block_coverage(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            self.assertEqual(
                s.width*s.height,
                sum((w[0][1]-w[0][0])*(w[1][1]-w[1][0]) 
                    for ji, w in s.block_windows(1)))

class WindowReadTest(unittest.TestCase):
    def test_read_window(self):
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as s:
            windows = s.block_windows(1)
            ji, first_window = next(windows)
            first_block = s.read_band(1, window=first_window)
            self.assertEqual(first_block.dtype, rasterio.ubyte)
            self.assertEqual(
                first_block.shape, 
                rasterio.window_shape(first_window))

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
            s.write_band(1, a, window=((30, 80), (10, 60)))
        # subprocess.call(["open", name])
        info = subprocess.check_output(["gdalinfo", "-stats", name])
        self.assert_(
            "Minimum=0.000, Maximum=127.000, "
            "Mean=31.750, StdDev=54.993" in info.decode('utf-8'),
            info)


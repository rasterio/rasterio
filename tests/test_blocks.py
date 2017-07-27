from functools import partial
import logging
import os.path
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from packaging.version import parse
import pytest

import rasterio
from rasterio import windows
from rasterio.errors import RasterBlockError


class WindowTest(unittest.TestCase):

    def test_window_shape_None_start(self):
        self.assertEqual(
            rasterio.window_shape(((None, 4), (None, 102))),
            (4, 102))

    def test_window_shape_None_stop(self):
        self.assertEqual(
            rasterio.window_shape(((10, None), (10, None)), 100, 90),
            (90, 80))

    def test_window_shape_positive(self):
        self.assertEqual(
            rasterio.window_shape(((0, 4), (1, 102))),
            (4, 101))

    def test_window_shape_negative(self):
        self.assertEqual(
            rasterio.window_shape(((-10, None), (-10, None)), 100, 90),
            (10, 10))
        self.assertEqual(
            rasterio.window_shape(((~0, None), (~0, None)), 100, 90),
            (1, 1))
        self.assertEqual(
            rasterio.window_shape(((None, ~0), (None, ~0)), 100, 90),
            (99, 89))

    def test_eval(self):
        self.assertEqual(
            rasterio.eval_window(((-10, None), (-10, None)), 100, 90),
            windows.Window.from_ranges((90, 100), (80, 90)))
        self.assertEqual(
            rasterio.eval_window(((None, -10), (None, -10)), 100, 90),
            windows.Window.from_ranges((0, 90), (0, 80)))

def test_window_index():
    idx = rasterio.window_index(((0, 4), (1, 12)))
    assert len(idx) == 2
    r, c = idx
    assert r.start == 0
    assert r.stop == 4
    assert c.start == 1
    assert c.stop == 12
    arr = np.ones((20, 20))
    assert arr[idx].shape == (4, 11)


class RasterBlocksTest(unittest.TestCase):

    def test_blocks(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            self.assertEqual(len(s.block_shapes), 3)
            self.assertEqual(s.block_shapes, ((3, 791), (3, 791), (3, 791)))
            itr = s.block_windows(1)
            (j, i), first = next(itr)
            self.assertEqual((j, i), (0, 0))
            self.assertEqual(first, windows.Window.from_ranges((0, 3), (0, 791)))
            itr = s.block_windows()
            (j, i), first = next(itr)
            self.assertEqual((j, i), (0, 0))
            self.assertEqual(first, windows.Window.from_ranges((0, 3), (0, 791)))
            (j, i), second = next(itr)
            self.assertEqual((j, i), (1, 0))
            self.assertEqual(second, windows.Window.from_ranges((3, 6), (0, 791)))
            (j, i), last = list(itr)[~0]
            self.assertEqual((j, i), (239, 0))
            self.assertEqual(
                last, windows.Window.from_ranges((717, 718), (0, 791)))

    def test_block_coverage(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            self.assertEqual(
                s.width * s.height,
                sum((w[0][1] - w[0][0]) * (w[1][1] - w[1][0])
                    for ji, w in s.block_windows(1)))


class WindowReadTest(unittest.TestCase):
    def test_read_window(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            windows = s.block_windows(1)
            ji, first_window = next(windows)
            first_block = s.read(1, window=first_window)
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
        a = np.ones((50, 50), dtype=rasterio.ubyte) * 127
        with rasterio.open(
                name, 'w',
                driver='GTiff', width=100, height=100, count=1,
                dtype=a.dtype) as s:
            s.write(a, indexes=1, window=windows.Window(10, 30, 50, 50))
        # subprocess.call(["open", name])
        info = subprocess.check_output(["gdalinfo", "-stats", name])
        self.assertTrue(
            "Minimum=0.000, Maximum=127.000, "
            "Mean=31.750, StdDev=54.993" in info.decode('utf-8'),
            info)


def test_block_windows_unfiltered(path_rgb_byte_tif):
    """Get all block windows"""
    with rasterio.open(path_rgb_byte_tif) as src:
        assert len(list(src.block_windows())) == 240


def test_block_windows_filtered_all(path_rgb_byte_tif):
    """Get all block windows using filter"""
    with rasterio.open(path_rgb_byte_tif) as src:
        w, s, e, n = src.bounds
        focus_window = src.window(w, s, e, n)
        filter_func = partial(windows.intersect, focus_window)
        itr = ((ij, win) for ij, win in src.block_windows() if filter_func(win))
        assert len(list(itr)) == 240


def test_block_windows_filtered_one(path_rgb_byte_tif):
    """Get the first block windows using filter"""
    with rasterio.open(path_rgb_byte_tif) as src:
        w, s, e, n = src.bounds
        focus_window = src.window(w, n - 1.0, w + 1.0, n)
        filter_func = partial(windows.intersect, focus_window)
        itr = ((ij, win) for ij, win in src.block_windows() if filter_func(win))
        assert next(itr) == ((0, 0), windows.Window.from_ranges((0, 3), (0, 791)))
        with pytest.raises(StopIteration):
            next(itr)


def test_block_windows_filtered_none(path_rgb_byte_tif):
    """Get no block windows using filter"""
    with rasterio.open(path_rgb_byte_tif) as src:
        w, s, e, n = src.bounds
        focus_window = src.window(w - 100.0, n + 1.0, w - 1.0, n + 100.0,
                                  boundless=True)
        filter_func = partial(windows.intersect, focus_window)
        itr = ((ij, win) for ij, win in src.block_windows() if filter_func(win))
        with pytest.raises(StopIteration):
            next(itr)


@pytest.mark.skipif(
    parse(rasterio.__gdal_version__) < parse('2.0.0'),
    reason="TIFF block size access requires GDAL 2.0")
def test_block_size_tiff(path_rgb_byte_tif):
    """Without compression a TIFF's blocks are all the same size"""
    with rasterio.open(path_rgb_byte_tif) as src:
        block_windows = list(src.block_windows())
        sizes = [src.block_size(1, i, j) for (i, j), w in block_windows]
        assert sizes.count(2373) == 1
        assert sizes.count(7119) == len(block_windows) - 1


@pytest.mark.skipif(
    parse(rasterio.__gdal_version__) < parse('2.0.0'),
    reason="TIFF block size access requires GDAL 2.0")
def test_block_size_exception():
    """A JPEG has no TIFF metadata and no API for block size"""
    with pytest.raises(RasterBlockError):
        with rasterio.open('tests/data/389225main_sw_1965_1024.jpg') as src:
            src.block_size(1, 0, 0)


def test_block_window_tiff(path_rgb_byte_tif):
    """Block window accessors are consistent"""
    with rasterio.open(path_rgb_byte_tif) as src:
        for (i, j), w in src.block_windows():
            assert src.block_window(1, i, j) == w

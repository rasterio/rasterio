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

class WriterContextTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
    def tearDown(self):
        shutil.rmtree(self.tempdir)
    def test_context(self):
        name = os.path.join(self.tempdir, "test_context.tif")
        with rasterio.open(
                name, 'w', 
                driver='GTiff', width=100, height=100, count=1, 
                dtype=rasterio.ubyte) as s:
            self.assertEqual(s.name, name)
            self.assertEqual(s.driver, 'GTiff')
            self.assertEqual(s.closed, False)
            self.assertEqual(s.count, 1)
            self.assertEqual(s.width, 100)
            self.assertEqual(s.height, 100)
            self.assertEqual(s.shape, (100, 100))
            self.assertEqual(s.indexes, [1])
            self.assertEqual(
                repr(s), 
                "<open RasterUpdater '%s' at %s>" % (name, hex(id(s))))
        self.assertEqual(s.closed, True)
        self.assertEqual(s.count, 1)
        self.assertEqual(s.width, 100)
        self.assertEqual(s.height, 100)
        self.assertEqual(s.shape, (100, 100))
        self.assertEqual(
            repr(s), 
            "<closed RasterUpdater '%s' at %s>" % (name, hex(id(s))))
        info = subprocess.check_output(["gdalinfo", name])
        self.assert_("GTiff" in info.decode('utf-8'))
        self.assert_(
            "Size is 100, 100" in info.decode('utf-8'))
        self.assert_(
            "Band 1 Block=100x81 Type=Byte, ColorInterp=Gray" in info.decode('utf-8'))
    def test_write_ubyte(self):
        name = os.path.join(self.tempdir, "test_write_ubyte.tif")
        a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
        with rasterio.open(
                name, 'w', 
                driver='GTiff', width=100, height=100, count=1, 
                dtype=a.dtype) as s:
            s.write_band(1, a)
        info = subprocess.check_output(["gdalinfo", "-stats", name])
        self.assert_(
            "Minimum=127.000, Maximum=127.000, "
            "Mean=127.000, StdDev=0.000" in info.decode('utf-8'),
            info)
    def test_write_float(self):
        name = os.path.join(self.tempdir, "test_write_float.tif")
        a = numpy.ones((100, 100), dtype=rasterio.float32) * 42.0
        with rasterio.open(
                name, 'w', 
                driver='GTiff', width=100, height=100, count=2,
                dtype=rasterio.float32) as s:
            self.assertEqual(s.dtypes, [rasterio.float32]*2)
            s.write_band(1, a)
            s.write_band(2, a)
        info = subprocess.check_output(["gdalinfo", "-stats", name])
        self.assert_(
            "Minimum=42.000, Maximum=42.000, "
            "Mean=42.000, StdDev=0.000" in info.decode('utf-8'),
            info)
    def test_write_crs_transform(self):
        name = os.path.join(self.tempdir, "test_write_crs_transform.tif")
        a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
        with rasterio.open(
                name, 'w', 
                driver='GTiff', width=100, height=100, count=1,
                crs={'units': 'm', 'no_defs': True, 'ellps': 'WGS84', 
                     'proj': 'utm', 'zone': 18},
                transform=[101985.0, 300.0379266750948, 0.0, 
                           2826915.0, 0.0, -300.041782729805],
                dtype=rasterio.ubyte) as s:
            s.write_band(1, a)
        info = subprocess.check_output(["gdalinfo", name])
        self.assert_('PROJCS["UTM Zone 18, Northern Hemisphere",' in info.decode('utf-8'))
        self.assert_("(300.037926675094809,-300.041782729804993)" in info.decode('utf-8'))
    def test_write_meta(self):
        name = os.path.join(self.tempdir, "test_write_meta.tif")
        a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
        meta = dict(
            driver='GTiff', width=100, height=100, count=1)
        with rasterio.open(name, 'w', dtype=a.dtype, **meta) as s:
            s.write_band(1, a)
        info = subprocess.check_output(["gdalinfo", "-stats", name])
        self.assert_(
            "Minimum=127.000, Maximum=127.000, "
            "Mean=127.000, StdDev=0.000" in info.decode('utf-8'),
            info)
    def test_write_nodata(self):
        name = os.path.join(self.tempdir, "test_write_nodata.tif")
        a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
        with rasterio.open(
                name, 'w', 
                driver='GTiff', width=100, height=100, count=2, 
                dtype=a.dtype, nodata=0) as s:
            s.write_band(1, a)
            s.write_band(2, a)
        info = subprocess.check_output(["gdalinfo", "-stats", name])
        self.assert_("NoData Value=0" in info.decode('utf-8'), info)
    def test_write_lzw(self):
        name = os.path.join(self.tempdir, "test_write_lzw.tif")
        a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
        with rasterio.open(
                name, 'w', 
                driver='GTiff', 
                width=100, height=100, count=1, 
                dtype=a.dtype,
                compress='LZW') as s:
            s.write_band(1, a)
        info = subprocess.check_output(["gdalinfo", name])
        self.assert_("LZW" in info.decode('utf-8'), info)


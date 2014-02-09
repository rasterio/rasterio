# Test of opening and closing and opening

import logging
import os.path
import shutil
import subprocess
import sys
import tempfile
import unittest

import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
log = logging.getLogger('rasterio.tests')

class RevolvingDoorTest(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()
    
    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_write_colormap_revolving_door(self):

        with rasterio.open('rasterio/tests/data/shade.tif') as src:
            shade = src.read_band(1)
            meta = src.meta

        tiffname = os.path.join(self.tempdir, 'foo.tif')
        
        with rasterio.open(tiffname, 'w', **meta) as dst:
            dst.write_band(1, shade)

        with rasterio.open(tiffname) as src:
            pass


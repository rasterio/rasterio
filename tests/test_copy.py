import logging
import os.path
import unittest
import shutil
import subprocess
import sys
import tempfile

import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


class CopyTest(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tempdir)

    def test_copy(self):
        name = os.path.join(self.tempdir, 'test_copy.tif')
        rasterio.copy(
            'tests/data/RGB.byte.tif',
            name)
        info = subprocess.check_output(["gdalinfo", name])
        self.assert_("GTiff" in info.decode('utf-8'))

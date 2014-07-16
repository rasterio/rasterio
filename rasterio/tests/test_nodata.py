import logging
import pytest
import re
import subprocess
import sys

import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_nodata(tmpdir):
    dst_path = str(tmpdir.join('lol.tif'))
    with rasterio.drivers():
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
            with rasterio.open(dst_path, 'w', **src.meta) as dst:
                assert dst.meta['nodata'] == 0.0
                assert dst.nodatavals == [0.0, 0.0, 0.0]
    info = subprocess.check_output([
        'gdalinfo', dst_path])
    pattern = b'Band 1.*?NoData Value=0'
    assert re.search(pattern, info, re.DOTALL) is not None
    pattern = b'Band 2.*?NoData Value=0'
    assert re.search(pattern, info, re.DOTALL) is not None
    pattern = b'Band 2.*?NoData Value=0'
    assert re.search(pattern, info, re.DOTALL) is not None

def test_set_nodata(tmpdir):
    dst_path = str(tmpdir.join('lol.tif'))
    with rasterio.drivers():
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
            meta = src.meta
            meta['nodata'] = 42
            with rasterio.open(dst_path, 'w', **meta) as dst:
                assert dst.meta['nodata'] == 42
                assert dst.nodatavals == [42, 42, 42]
    info = subprocess.check_output([
        'gdalinfo', dst_path])
    pattern = b'Band 1.*?NoData Value=42'
    assert re.search(pattern, info, re.DOTALL) is not None
    pattern = b'Band 2.*?NoData Value=42'
    assert re.search(pattern, info, re.DOTALL) is not None
    pattern = b'Band 2.*?NoData Value=42'
    assert re.search(pattern, info, re.DOTALL) is not None




import logging
import subprocess
import sys
import re
import numpy
import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_context(tmpdir):
    name = str(tmpdir.join("test_context.tif"))
    with rasterio.open(
            name, 'w', 
            driver='GTiff', width=100, height=100, count=1, 
            dtype=rasterio.ubyte) as s:
        assert s.name == name
        assert s.driver == 'GTiff'
        assert s.closed == False
        assert s.count == 1
        assert s.width == 100
        assert s.height == 100
        assert s.shape == (100, 100)
        assert s.indexes == [1]
        assert repr(s) == "<open RasterUpdater '%s' at %s>" % (name, hex(id(s)))
    assert s.closed == True
    assert s.count == 1
    assert s.width == 100
    assert s.height == 100
    assert s.shape == (100, 100)
    assert repr(s) == "<closed RasterUpdater '%s' at %s>" % (name, hex(id(s)))
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert "GTiff" in info
    assert "Size is 100, 100" in info
    assert "Band 1 Block=100x81 Type=Byte, ColorInterp=Gray" in info
    
def test_write_ubyte(tmpdir):
    name = str(tmpdir.mkdir("sub").join("test_write_ubyte.tif"))
    a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
    with rasterio.open(
            name, 'w', 
            driver='GTiff', width=100, height=100, count=1, 
            dtype=a.dtype) as s:
        s.write_band(1, a)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=127.000, Maximum=127.000, Mean=127.000, StdDev=0.000" in info
    
def test_write_float(tmpdir):
    name = str(tmpdir.join("test_write_float.tif"))
    a = numpy.ones((100, 100), dtype=rasterio.float32) * 42.0
    with rasterio.open(
            name, 'w', 
            driver='GTiff', width=100, height=100, count=2,
            dtype=rasterio.float32) as s:
        assert s.dtypes == [rasterio.float32]*2
        s.write_band(1, a)
        s.write_band(2, a)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=42.000, Maximum=42.000, Mean=42.000, StdDev=0.000" in info
    
def test_write_crs_transform(tmpdir):
    name = str(tmpdir.join("test_write_crs_transform.tif"))
    a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
    transform = [101985.0, 300.0379266750948, 0.0,
                       2826915.0, 0.0, -300.041782729805]
    with rasterio.open(
            name, 'w', 
            driver='GTiff', width=100, height=100, count=1,
            crs={'units': 'm', 'no_defs': True, 'ellps': 'WGS84', 
                 'proj': 'utm', 'zone': 18},
            transform=transform,
            dtype=rasterio.ubyte) as s:
        s.write_band(1, a)
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert 'PROJCS["UTM Zone 18, Northern Hemisphere",' in info
    # make sure that pixel size is nearly the same as transform
    # (precision varies slightly by platform)
    assert re.search("Pixel Size = \(300.03792\d+,-300.04178\d+\)", info)

def test_write_meta(tmpdir):
    name = str(tmpdir.join("test_write_meta.tif"))
    a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
    meta = dict(driver='GTiff', width=100, height=100, count=1)
    with rasterio.open(name, 'w', dtype=a.dtype, **meta) as s:
        s.write_band(1, a)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=127.000, Maximum=127.000, Mean=127.000, StdDev=0.000" in info
    
def test_write_nodata(tmpdir):
    name = str(tmpdir.join("test_write_nodata.tif"))
    a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
    with rasterio.open(
            name, 'w', 
            driver='GTiff', width=100, height=100, count=2, 
            dtype=a.dtype, nodata=0) as s:
        s.write_band(1, a)
        s.write_band(2, a)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "NoData Value=0" in info

def test_write_lzw(tmpdir):
    name = str(tmpdir.join("test_write_lzw.tif"))
    a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
    with rasterio.open(
            name, 'w', 
            driver='GTiff', 
            width=100, height=100, count=1, 
            dtype=a.dtype,
            compress='LZW') as s:
        s.write_band(1, a)
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert "LZW" in info


import logging
import re
import subprocess
import sys

import affine
import numpy as np
import pytest

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_validate_dtype_None(tmpdir):
    """Raise TypeError if there is no dtype"""
    name = str(tmpdir.join("lol.tif"))
    with pytest.raises(TypeError):
        rasterio.open(
            name, 'w', driver='GTiff', width=100, height=100, count=1)


def test_validate_dtype_str(tmpdir):
    name = str(tmpdir.join("lol.tif"))
    with pytest.raises(TypeError):
        rasterio.open(
            name, 'w', driver='GTiff', width=100, height=100, count=1,
            dtype='Int16')


def test_validate_count_None(tmpdir):
    name = str(tmpdir.join("lol.tif"))
    with pytest.raises(TypeError):
        rasterio.open(
            name, 'w', driver='GTiff', width=100, height=100,  # count=None
            dtype=rasterio.uint8)


def test_no_crs(tmpdir):
    # A dataset without crs is okay.
    name = str(tmpdir.join("lol.tif"))
    with rasterio.open(
            name, 'w', driver='GTiff', width=100, height=100, count=1,
            dtype=rasterio.uint8) as dst:
        dst.write(np.ones((100, 100), dtype=rasterio.uint8), indexes=1)

def test_context(tmpdir):
    name = str(tmpdir.join("test_context.tif"))
    with rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=1,
            dtype=rasterio.ubyte) as s:
        assert s.name == name
        assert s.driver == 'GTiff'
        assert not s.closed
        assert s.count == 1
        assert s.width == 100
        assert s.height == 100
        assert s.shape == (100, 100)
        assert s.indexes == (1,)
        assert repr(s) == "<open RasterUpdater name='%s' mode='w'>" % name
    assert s.closed
    assert s.count == 1
    assert s.width == 100
    assert s.height == 100
    assert s.shape == (100, 100)
    assert repr(s) == "<closed RasterUpdater name='%s' mode='w'>" % name
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert "GTiff" in info
    assert "Size is 100, 100" in info
    assert "Band 1 Block=100x81 Type=Byte, ColorInterp=Gray" in info


def test_write_ubyte(tmpdir):
    name = str(tmpdir.mkdir("sub").join("test_write_ubyte.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    with rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=1,
            dtype=a.dtype) as s:
        s.write(a, indexes=1)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=127.000, Maximum=127.000, Mean=127.000, StdDev=0.000" in info
def test_write_ubyte_multi(tmpdir):
    name = str(tmpdir.mkdir("sub").join("test_write_ubyte_multi.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    with rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=1,
            dtype=a.dtype) as s:
        s.write(a, 1)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=127.000, Maximum=127.000, Mean=127.000, StdDev=0.000" in info
def test_write_ubyte_multi_list(tmpdir):
    name = str(tmpdir.mkdir("sub").join("test_write_ubyte_multi_list.tif"))
    a = np.array([np.ones((100, 100), dtype=rasterio.ubyte) * 127])
    with rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=1,
            dtype=a.dtype) as s:
        s.write(a, [1])
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=127.000, Maximum=127.000, Mean=127.000, StdDev=0.000" in info
def test_write_ubyte_multi_3(tmpdir):
    name = str(tmpdir.mkdir("sub").join("test_write_ubyte_multi_list.tif"))
    arr = np.array(3 * [np.ones((100, 100), dtype=rasterio.ubyte) * 127])
    with rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=3,
            dtype=arr.dtype) as s:
        s.write(arr)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=127.000, Maximum=127.000, Mean=127.000, StdDev=0.000" in info

def test_write_float(tmpdir):
    name = str(tmpdir.join("test_write_float.tif"))
    a = np.ones((100, 100), dtype=rasterio.float32) * 42.0
    with rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=2,
            dtype=rasterio.float32) as s:
        assert s.dtypes == (rasterio.float32, rasterio.float32)
        s.write(a, indexes=1)
        s.write(a, indexes=2)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=42.000, Maximum=42.000, Mean=42.000, StdDev=0.000" in info

def test_write_crs_transform(tmpdir):
    name = str(tmpdir.join("test_write_crs_transform.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    transform = affine.Affine.from_gdal(101985.0, 300.0379266750948, 0.0,
                                        2826915.0, 0.0, -300.041782729805)
    with rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=1,
            crs={'units': 'm', 'no_defs': True, 'ellps': 'WGS84',
                 'proj': 'utm', 'zone': 18},
            transform=transform,
            dtype=rasterio.ubyte) as s:
        s.write(a, indexes=1)
    assert s.crs == {'init': 'epsg:32618'}
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert 'PROJCS["UTM Zone 18, Northern Hemisphere",' in info
    # make sure that pixel size is nearly the same as transform
    # (precision varies slightly by platform)
    assert re.search("Pixel Size = \(300.03792\d+,-300.04178\d+\)", info)

def test_write_crs_transform_affine(tmpdir):
    name = str(tmpdir.join("test_write_crs_transform.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    transform = affine.Affine.from_gdal(101985.0, 300.0379266750948, 0.0,
                                        2826915.0, 0.0, -300.041782729805)
    with rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=1,
            crs={'units': 'm', 'no_defs': True, 'ellps': 'WGS84',
                 'proj': 'utm', 'zone': 18},
            transform=transform,
            dtype=rasterio.ubyte) as s:
        s.write(a, indexes=1)
    assert s.crs == {'init': 'epsg:32618'}
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert 'PROJCS["UTM Zone 18, Northern Hemisphere",' in info
    # make sure that pixel size is nearly the same as transform
    # (precision varies slightly by platform)
    assert re.search("Pixel Size = \(300.03792\d+,-300.04178\d+\)", info)

def test_write_crs_transform_2(tmpdir):
    """Using 'EPSG:32618' as CRS."""
    name = str(tmpdir.join("test_write_crs_transform.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    transform = affine.Affine.from_gdal(101985.0, 300.0379266750948, 0.0,
                                        2826915.0, 0.0, -300.041782729805)
    with rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=1,
            crs='EPSG:32618',
            transform=transform,
            dtype=rasterio.ubyte) as s:
        s.write(a, indexes=1)
    assert s.crs == {'init': 'epsg:32618'}
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert 'PROJCS["WGS 84 / UTM zone 18N",' in info
    # make sure that pixel size is nearly the same as transform
    # (precision varies slightly by platform)
    assert re.search("Pixel Size = \(300.03792\d+,-300.04178\d+\)", info)

def test_write_crs_transform_3(tmpdir):
    """Using WKT as CRS."""
    name = str(tmpdir.join("test_write_crs_transform.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    transform = affine.Affine.from_gdal(101985.0, 300.0379266750948, 0.0,
                                        2826915.0, 0.0, -300.041782729805)
    crs_wkt = 'PROJCS["UTM Zone 18, Northern Hemisphere",GEOGCS["WGS 84",DATUM["unknown",SPHEROID["WGS84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-75],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["Meter",1]]'
    with rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=1,
            crs=crs_wkt,
            transform=transform,
            dtype=rasterio.ubyte) as s:
        s.write(a, indexes=1)
    assert s.crs == {'init': 'epsg:32618'}
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert 'PROJCS["UTM Zone 18, Northern Hemisphere",' in info
    # make sure that pixel size is nearly the same as transform
    # (precision varies slightly by platform)
    assert re.search("Pixel Size = \(300.03792\d+,-300.04178\d+\)", info)

def test_write_meta(tmpdir):
    name = str(tmpdir.join("test_write_meta.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    meta = dict(driver='GTiff', width=100, height=100, count=1)
    with rasterio.open(name, 'w', dtype=a.dtype, **meta) as s:
        s.write(a, indexes=1)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=127.000, Maximum=127.000, Mean=127.000, StdDev=0.000" in info

def test_write_nodata(tmpdir):
    name = str(tmpdir.join("test_write_nodata.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    with rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=2,
            dtype=a.dtype, nodata=0) as s:
        s.write(a, indexes=1)
        s.write(a, indexes=2)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "NoData Value=0" in info


def test_guard_nodata(tmpdir):
    name = str(tmpdir.join("test_guard_nodata.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    with pytest.raises(ValueError):
        rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=2,
            dtype=a.dtype, nodata=-1)


def test_write_lzw(tmpdir):
    name = str(tmpdir.join("test_write_lzw.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    with rasterio.open(
            name, 'w',
            driver='GTiff',
            width=100, height=100, count=1,
            dtype=a.dtype,
            compress='LZW') as s:
        assert ('compress', 'LZW') in s.kwds.items()
        s.write(a, indexes=1)
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert "LZW" in info

def test_write_noncontiguous(tmpdir):
    name = str(tmpdir.join("test_write_nodata.tif"))
    ROWS = 4
    COLS = 10
    BANDS = 6
    # Create a 3-D random int array (rows, columns, bands)
    total = ROWS * COLS * BANDS
    arr = np.random.randint(
        0, 10, size=total).reshape(
            (ROWS, COLS, BANDS), order='F').astype(np.int32)
    kwargs = {
        'driver': 'GTiff',
        'width': COLS,
        'height': ROWS,
        'count': BANDS,
        'dtype': rasterio.int32
    }
    with rasterio.open(name, 'w', **kwargs) as dst:
        for i in range(BANDS):
            dst.write(arr[:, :, i], indexes=i + 1)

import re
import subprocess

import affine
import numpy as np
import pytest

from .conftest import requires_gdal31

import rasterio
from rasterio.drivers import blacklist
from rasterio.enums import Resampling
from rasterio.env import Env
from rasterio.errors import RasterioIOError


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


def test_validate_dtype_float128(tmpdir, basic_image):
    """Raise TypeError if dtype is unsupported by GDAL."""
    name = str(tmpdir.join('float128.tif'))
    try:
        basic_image_f128 = basic_image.astype('float128')
    except TypeError:
        pytest.skip("Unsupported data type")
    height, width = basic_image_f128.shape
    with pytest.raises(TypeError):
        rasterio.open(name, 'w', driver='GTiff', width=width, height=height,
                      count=1, dtype=basic_image_f128.dtype)


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


@pytest.mark.gdalbin
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
        assert repr(s) == "<open DatasetWriter name='%s' mode='w'>" % name
    assert s.closed
    assert s.count == 1
    assert s.width == 100
    assert s.height == 100
    assert s.shape == (100, 100)
    assert repr(s) == "<closed DatasetWriter name='%s' mode='w'>" % name
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert "GTiff" in info
    assert "Size is 100, 100" in info
    assert "Band 1 Block=100x81 Type=Byte, ColorInterp=Gray" in info


@pytest.mark.gdalbin
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


@pytest.mark.gdalbin
def test_write_sbyte(tmpdir):
    name = str(tmpdir.mkdir("sub").join("test_write_sbyte.tif"))
    a = np.ones((100, 100), dtype=rasterio.sbyte) * -33
    with rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=1,
            dtype=a.dtype) as dst:
        dst.write(a, indexes=1)

    with rasterio.open(name) as dst:
        assert (dst.read() == -33).all()

    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=-33.000, Maximum=-33.000, Mean=-33.000, StdDev=0.000" in info
    assert 'SIGNEDBYTE' in info


@pytest.mark.gdalbin
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


@pytest.mark.gdalbin
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


@pytest.mark.gdalbin
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


@pytest.mark.gdalbin
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


@pytest.mark.gdalbin
def test_write_crs_transform(tmpdir):
    name = str(tmpdir.join("test_write_crs_transform.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    transform = affine.Affine(300.0379266750948, 0.0, 101985.0,
                              0.0, -300.041782729805, 2826915.0)

    with rasterio.open(
        name,
        "w",
        driver="GTiff",
        width=100,
        height=100,
        count=1,
        crs={
            "units": "m",
            "no_defs": True,
            "datum": "WGS84",
            "proj": "utm",
            "zone": 18,
        },
        transform=transform,
        dtype=rasterio.ubyte,
    ) as s:
        s.write(a, indexes=1)
    assert s.crs.to_epsg() == 32618
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    # make sure that pixel size is nearly the same as transform
    # (precision varies slightly by platform)
    assert re.search(r'Pixel Size = \(300.03792\d+,-300.04178\d+\)', info)


@pytest.mark.gdalbin
def test_write_crs_transform_affine(tmpdir):
    name = str(tmpdir.join("test_write_crs_transform.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    transform = affine.Affine(300.0379266750948, 0.0, 101985.0,
                              0.0, -300.041782729805, 2826915.0)
    with rasterio.open(
        name,
        "w",
        driver="GTiff",
        width=100,
        height=100,
        count=1,
        crs={
            "units": "m",
            "no_defs": True,
            "datum": "WGS84",
            "proj": "utm",
            "zone": 18,
        },
        transform=transform,
        dtype=rasterio.ubyte,
    ) as s:
        s.write(a, indexes=1)

    assert s.crs.to_epsg() == 32618
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    # make sure that pixel size is nearly the same as transform
    # (precision varies slightly by platform)
    assert re.search(r'Pixel Size = \(300.03792\d+,-300.04178\d+\)', info)


@pytest.mark.gdalbin
def test_write_crs_transform_2(tmpdir, monkeypatch):
    """Using 'EPSG:32618' as CRS."""
    monkeypatch.delenv('GDAL_DATA', raising=False)
    name = str(tmpdir.join("test_write_crs_transform.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    transform = affine.Affine(300.0379266750948, 0.0, 101985.0,
                              0.0, -300.041782729805, 2826915.0)
    with rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=1,
            crs='EPSG:32618',
            transform=transform,
            dtype=rasterio.ubyte) as s:
        s.write(a, indexes=1)

    assert s.crs.to_epsg() == 32618
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert 'UTM zone 18N' in info
    # make sure that pixel size is nearly the same as transform
    # (precision varies slightly by platform)
    assert re.search(r'Pixel Size = \(300.03792\d+,-300.04178\d+\)', info)


@pytest.mark.gdalbin
def test_write_crs_transform_3(tmpdir):
    """Using WKT as CRS."""
    name = str(tmpdir.join("test_write_crs_transform.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    transform = affine.Affine(300.0379266750948, 0.0, 101985.0,
                              0.0, -300.041782729805, 2826915.0)
    wkt = 'PROJCS["WGS 84 / UTM zone 18N",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",-75],PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH],AUTHORITY["EPSG","32618"]]'

    with rasterio.open(
            name, 'w',
            driver='GTiff', width=100, height=100, count=1,
            crs=wkt,
            transform=transform,
            dtype=rasterio.ubyte) as s:
        s.write(a, indexes=1)
    assert s.crs.to_epsg() == 32618
    info = subprocess.check_output(["gdalinfo", name]).decode('utf-8')
    assert 'UTM zone 18N' in info
    # make sure that pixel size is nearly the same as transform
    # (precision varies slightly by platform)
    assert re.search(r'Pixel Size = \(300.03792\d+,-300.04178\d+\)', info)


@pytest.mark.gdalbin
def test_write_meta(tmpdir):
    name = str(tmpdir.join("test_write_meta.tif"))
    a = np.ones((100, 100), dtype=rasterio.ubyte) * 127
    meta = dict(driver='GTiff', width=100, height=100, count=1)
    with rasterio.open(name, 'w', dtype=a.dtype, **meta) as s:
        s.write(a, indexes=1)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=127.000, Maximum=127.000, Mean=127.000, StdDev=0.000" in info


@pytest.mark.gdalbin
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


@pytest.mark.parametrize("driver", list(blacklist.keys()))
def test_write_blacklist(tmpdir, driver):

    # Skip if we don't have driver support built in.
    with Env() as env:
        if driver not in env.drivers():
            pytest.skip()

    name = str(tmpdir.join("data.test"))
    with pytest.raises(RasterioIOError) as exc_info:
        rasterio.open(name, 'w', driver=driver, width=100, height=100,
                      count=1, dtype='uint8')
    exc = str(exc_info.value)
    assert exc.startswith("Blacklisted")


def test_creation_metadata_deprecation(tmpdir):
    name = str(tmpdir.join("test.tif"))
    with rasterio.open(name, 'w', driver='GTiff', height=1, width=1, count=1, dtype='uint8', BIGTIFF='YES') as dst:
        dst.write(np.ones((1, 1, 1), dtype='uint8'))
        assert dst.tags(ns='rio_creation_kwds') == {}


def test_wplus_transform(tmpdir):
    """Transform is set on a new dataset created in w+ mode (see issue #1359)"""
    name = str(tmpdir.join("test.tif"))
    transform = affine.Affine.translation(10.0, 10.0) * affine.Affine.scale(0.5, -0.5)
    with rasterio.open(name, 'w+', driver='GTiff', crs='epsg:4326', transform=transform, height=10, width=10, count=1, dtype='uint8') as dst:
        dst.write(np.ones((1, 10, 10), dtype='uint8'))
        assert dst.transform == transform


def test_write_no_driver__issue_1203(tmpdir):
    name = str(tmpdir.join("test.invalid"))
    with pytest.raises(ValueError), rasterio.open(name, 'w', height=1, width=1, count=1, dtype='uint8'):
        print("TEST FAILED IF THIS IS REACHED.")


@pytest.mark.parametrize("mode", ["w", "w+"])
def test_require_width(tmpdir, mode):
    """width and height are required for w and w+ mode"""
    name = str(tmpdir.join("test.tif"))
    with pytest.raises(TypeError):
        with rasterio.open(name, mode, driver="GTiff", height=1, count=1, dtype='uint8'):
            print("TEST FAILED IF THIS IS REACHED.")


def test_too_big_for_tiff(tmpdir):
    """RasterioIOError is raised when TIFF is too big"""
    name = str(tmpdir.join("test.tif"))
    with pytest.raises(RasterioIOError):
        rasterio.open(name, 'w', driver='GTiff', height=100000, width=100000, count=1, dtype='uint8', BIGTIFF=False)


@pytest.mark.parametrize("extension, driver", [
    ('tif', 'GTiff'),
    ('tiff', 'GTiff'),
    ('png', 'PNG'),
    ('jpg', 'JPEG'),
    ('jpeg', 'JPEG'),
])
def test_write__autodetect_driver(tmpdir, extension, driver):
    name = str(tmpdir.join("test.{}".format(extension)))
    with rasterio.open(name, 'w', height=1, width=1, count=1, dtype='uint8') as rds:
        assert rds.driver == driver


@pytest.mark.parametrize("driver", ["PNG", "JPEG"])
def test_issue2088(tmpdir, capsys, driver):
    """Write a PNG or JPEG without error messages"""
    with rasterio.open(
        str(tmpdir.join("test")),
        "w",
        driver=driver,
        dtype="uint8",
        count=1,
        height=256,
        width=256,
        transform=affine.Affine.identity(),
    ) as src:
        data = np.ones((256, 256), dtype=np.uint8)
        src.write(data, 1)

    captured = capsys.readouterr()
    assert "ERROR 4" not in captured.err
    assert "ERROR 4" not in captured.out


@requires_gdal31
def test_write_cog(tmpdir, path_rgb_byte_tif):
    """Show resolution of issue #2102"""
    with rasterio.open(path_rgb_byte_tif) as src:
        profile = src.profile
        profile.update(driver="COG", extent=src.bounds, resampling=Resampling.bilinear)
        with rasterio.open(str(tmpdir.join("test.tif")), "w", **profile) as cog:
            cog.write(src.read())

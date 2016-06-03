import logging
import pytest
import subprocess
import sys
import json

import rasterio
from rasterio._base import _can_create_osr
from rasterio.crs import CRS
from rasterio.errors import CRSError


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


# When possible, Rasterio gives you the CRS in the form of an EPSG code.
def test_read_epsg(tmpdir):
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.crs.data == {'init': 'epsg:32618'}

def test_read_epsg3857(tmpdir):
    tiffname = str(tmpdir.join('lol.tif'))
    subprocess.call([
        'gdalwarp', '-t_srs', 'EPSG:3857',
        'tests/data/RGB.byte.tif', tiffname])
    with rasterio.open(tiffname) as src:
        assert src.crs.data == {'init': 'epsg:3857'}

# Ensure that CRS sticks when we write a file.
def test_write_3857(tmpdir):
    src_path = str(tmpdir.join('lol.tif'))
    subprocess.call([
        'gdalwarp', '-t_srs', 'EPSG:3857',
        'tests/data/RGB.byte.tif', src_path])
    dst_path = str(tmpdir.join('wut.tif'))
    with rasterio.open(src_path) as src:
        with rasterio.open(dst_path, 'w', **src.meta) as dst:
            assert dst.crs.data == {'init': 'epsg:3857'}
    info = subprocess.check_output([
        'gdalinfo', dst_path])
    # WKT string may vary a bit w.r.t GDAL versions
    assert 'PROJCS["WGS 84 / Pseudo-Mercator"' in info.decode('utf-8')


def test_from_proj4_json():
    json_str = '{"proj": "longlat", "ellps": "WGS84", "datum": "WGS84"}'
    crs_dict = CRS.from_string(json_str)
    assert crs_dict == json.loads(json_str)

    # Test with invalid JSON code
    with pytest.raises(ValueError):
        assert CRS.from_string('{foo: bar}')


def test_from_epsg():
    crs_dict = CRS.from_epsg(4326)
    assert crs_dict['init'].lower() == 'epsg:4326'

    # Test with invalid EPSG code
    with pytest.raises(ValueError):
        assert CRS.from_epsg(0)


def test_from_epsg_string():
    crs_dict = CRS.from_string('epsg:4326')
    assert crs_dict['init'].lower() == 'epsg:4326'

    # Test with invalid EPSG code
    with pytest.raises(ValueError):
        assert CRS.from_string('epsg:xyz')


def test_from_string():
    wgs84_crs = CRS.from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    assert wgs84_crs.data == {'no_defs': True, 'ellps': 'WGS84', 'datum': 'WGS84', 'proj': 'longlat'}

    # Make sure this doesn't get handled using the from_epsg() even though 'epsg' is in the string
    epsg_init_crs = CRS.from_string('+units=m +init=epsg:26911 +no_defs=True')
    assert epsg_init_crs.data == {'units': 'm', 'init': 'epsg:26911', 'no_defs': True}


def test_bare_parameters():
    """ Make sure that bare parameters (e.g., no_defs) are handled properly,
    even if they come in with key=True.  This covers interaction with pyproj,
    which makes presents bare parameters as key=<bool>."""

    # Example produced by pyproj
    crs_dict = CRS.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert crs_dict.get('no_defs', False) is True

    crs_dict = CRS.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=False +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert crs_dict.get('no_defs', True) is False


def test_is_geographic():
    assert CRS({'init': 'EPSG:4326'}).is_geographic() is True
    assert CRS({'init': 'EPSG:3857'}).is_geographic() is False

    wgs84_crs = CRS.from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    assert wgs84_crs.is_geographic() is True

    nad27_crs = CRS.from_string('+proj=longlat +ellps=clrk66 +datum=NAD27 +no_defs')
    assert nad27_crs.is_geographic() is True

    lcc_crs = CRS.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert lcc_crs.is_geographic() is False


def test_is_projected():
    assert CRS({'init': 'EPSG:3857'}).is_projected() is True
    assert CRS({'INIT': 'EPSG:4326'}).is_projected() is False

    lcc_crs = CRS.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert CRS(lcc_crs).is_projected() is True

    wgs84_crs = CRS.from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    assert CRS(wgs84_crs).is_projected() is False


def test_is_same_crs():
    crs1 = CRS({'init': 'EPSG:4326'})
    crs2 = CRS({'init': 'EPSG:3857'})

    assert crs1 == crs1
    assert crs1 != crs2

    wgs84_crs = CRS.from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    assert crs1 == wgs84_crs

    # Make sure that same projection with different parameter are not equal
    lcc_crs1 = CRS.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    lcc_crs2 = CRS.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=45 +lat_0=0')
    assert lcc_crs1 != lcc_crs2


def test_to_string():
    assert CRS.to_string({'init': 'EPSG:4326'}) == "+init=EPSG:4326"


def test_is_valid_false():
    with pytest.raises(CRSError):
        CRS(init='EPSG:432600').is_valid()


def test_is_valid():
    assert CRS(init='EPSG:4326').is_valid()


def test_empty_json():
    with pytest.raises(CRSError):
        CRS.from_string('{}')
    with pytest.raises(CRSError):
        CRS.from_string('[]')
    with pytest.raises(CRSError):
        CRS.from_string('')


def test_can_create_osr():
    assert _can_create_osr({'init': 'EPSG:4326'})
    assert _can_create_osr('EPSG:4326')


def test_can_create_osr_empty():
    assert _can_create_osr({})
    assert _can_create_osr('')


def test_can_create_osr_invalid():
    assert not _can_create_osr(None)
    assert not _can_create_osr('EPSG:-1')
    assert not _can_create_osr('EPSG:')
    assert not _can_create_osr('foo')

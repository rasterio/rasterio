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
        assert src.crs.to_dict() == {'init': 'epsg:32618'}

def test_read_epsg3857(tmpdir):
    tiffname = str(tmpdir.join('lol.tif'))
    subprocess.call([
        'gdalwarp', '-t_srs', 'EPSG:3857',
        'tests/data/RGB.byte.tif', tiffname])
    with rasterio.open(tiffname) as src:
        assert src.crs.to_dict() == {'init': 'epsg:3857'}

# Ensure that CRS sticks when we write a file.
def test_write_3857(tmpdir):
    src_path = str(tmpdir.join('lol.tif'))
    subprocess.call([
        'gdalwarp', '-t_srs', 'EPSG:3857',
        'tests/data/RGB.byte.tif', src_path])
    dst_path = str(tmpdir.join('wut.tif'))
    with rasterio.open(src_path) as src:
        with rasterio.open(dst_path, 'w', **src.meta) as dst:
            assert dst.crs.to_dict() == {'init': 'epsg:3857'}
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
    assert wgs84_crs.to_dict() == {'no_defs': True, 'ellps': 'WGS84', 'datum': 'WGS84', 'proj': 'longlat'}

    # Make sure this doesn't get handled using the from_epsg() even though 'epsg' is in the string
    epsg_init_crs = CRS.from_string('+units=m +init=epsg:26911 +no_defs=True')
    assert epsg_init_crs.to_dict() == {'units': 'm', 'init': 'epsg:26911', 'no_defs': True}


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
    assert CRS({'init': 'EPSG:4326'}).is_geographic is True
    assert CRS({'init': 'EPSG:3857'}).is_geographic is False

    wgs84_crs = CRS.from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    assert wgs84_crs.is_geographic is True

    nad27_crs = CRS.from_string('+proj=longlat +ellps=clrk66 +datum=NAD27 +no_defs')
    assert nad27_crs.is_geographic is True

    lcc_crs = CRS.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert lcc_crs.is_geographic is False


def test_is_projected():
    assert CRS({'init': 'EPSG:3857'}).is_projected is True

    lcc_crs = CRS.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert CRS(lcc_crs).is_projected is True

    wgs84_crs = CRS.from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    assert CRS(wgs84_crs).is_projected is False


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


def test_null_crs_equality():
    """Null CRS should be equal"""
    assert (CRS() == CRS()) is True


def test_null_crs_inequality():
    """Null CRS should not be inequal"""
    assert (CRS() != CRS()) is False


def test_null_and_valid_crs_equality():
    assert (CRS() == CRS(init='EPSG:4326')) is False


def test_crs_OSR_equivalence():
    crs1 = CRS.from_string('+proj=longlat +datum=WGS84 +no_defs')
    crs2 = CRS.from_string('+proj=latlong +datum=WGS84 +no_defs')
    crs3 = CRS({'init': 'EPSG:4326'})
    assert crs1 == crs2
    assert crs1 == crs3


def test_crs_OSR_no_equivalence():
    crs1 = CRS.from_string('+proj=longlat +datum=WGS84 +no_defs')
    crs2 = CRS.from_string('+proj=longlat +datum=NAD27 +no_defs')
    assert crs1 != crs2


def test_to_string():
    assert CRS({'init': 'EPSG:4326'}).to_string() == "+init=EPSG:4326"


def test_is_valid_false():
    with pytest.raises(CRSError):
        CRS(init='EPSG:432600').is_valid


def test_is_valid():
    assert CRS(init='EPSG:4326').is_valid


def test_empty_json():
    with pytest.raises(CRSError):
        CRS.from_string('{}')
    with pytest.raises(CRSError):
        CRS.from_string('[]')
    with pytest.raises(CRSError):
        CRS.from_string('')


@pytest.mark.parametrize('arg', [None, {}, ''])
def test_can_create_osr_none_err(arg):
    """Passing None or empty fails"""
    with pytest.raises(ValueError):
        _can_create_osr(arg)


def test_can_create_osr():
    assert _can_create_osr({'init': 'EPSG:4326'})
    assert _can_create_osr('EPSG:4326')


@pytest.mark.parametrize('arg', ['EPSG:-1', 'foo'])
def test_can_create_osr_invalid(arg):
    """invalid CRS definitions fail"""
    assert not _can_create_osr(arg)


@pytest.mark.xfail()
def test_can_create_osr_invalid_epsg_0():
    """this invalid CRS should fail, but doesn't because of a GDAL bug"""
    assert not _can_create_osr('EPSG:')


def test_has_wkt_property():
    assert CRS({'init': 'EPSG:4326'}).wkt.startswith('GEOGCS["WGS 84",DATUM')


def test_repr():
    assert repr(CRS({'init': 'EPSG:4326'})).startswith("CRS({'init'")


def test_epsg_code():
    assert CRS({'init': 'EPSG:4326'}).is_epsg_code
    assert not CRS({'proj': 'latlon'}).is_epsg_code

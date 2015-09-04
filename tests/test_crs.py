import logging
import pytest
import subprocess
import sys
import json

import rasterio
from rasterio import crs
from rasterio.crs import (
    is_geographic_crs, is_projected_crs, is_same_crs, is_valid_crs)


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


# When possible, Rasterio gives you the CRS in the form of an EPSG code.
def test_read_epsg(tmpdir):
    with rasterio.drivers():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            assert src.crs == {'init': 'epsg:32618'}

def test_read_epsg3857(tmpdir):
    tiffname = str(tmpdir.join('lol.tif'))
    subprocess.call([
        'gdalwarp', '-t_srs', 'EPSG:3857', 
        'tests/data/RGB.byte.tif', tiffname])
    with rasterio.drivers():
        with rasterio.open(tiffname) as src:
            assert src.crs == {'init': 'epsg:3857'}

# Ensure that CRS sticks when we write a file.
def test_write_3857(tmpdir):
    src_path = str(tmpdir.join('lol.tif'))
    subprocess.call([
        'gdalwarp', '-t_srs', 'EPSG:3857', 
        'tests/data/RGB.byte.tif', src_path])
    dst_path = str(tmpdir.join('wut.tif'))
    with rasterio.drivers():
        with rasterio.open(src_path) as src:
            with rasterio.open(dst_path, 'w', **src.meta) as dst:
                assert dst.crs == {'init': 'epsg:3857'}
    info = subprocess.check_output([
        'gdalinfo', dst_path])
    assert """PROJCS["WGS 84 / Pseudo-Mercator",
    GEOGCS["WGS 84",
        DATUM["WGS_1984",
            SPHEROID["WGS 84",6378137,298.257223563,
                AUTHORITY["EPSG","7030"]],
            AUTHORITY["EPSG","6326"]],
        PRIMEM["Greenwich",0],
        UNIT["degree",0.0174532925199433],
        AUTHORITY["EPSG","4326"]],
    PROJECTION["Mercator_1SP"],
    PARAMETER["central_meridian",0],
    PARAMETER["scale_factor",1],
    PARAMETER["false_easting",0],
    PARAMETER["false_northing",0],
    UNIT["metre",1,
        AUTHORITY["EPSG","9001"]],
    EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs"],
    AUTHORITY["EPSG","3857"]]""" in info.decode('utf-8')


def test_from_proj4_json():
    json_str = '{"proj": "longlat", "ellps": "WGS84", "datum": "WGS84"}'
    crs_dict = crs.from_string(json_str)
    assert crs_dict == json.loads(json_str)

    # Test with invalid JSON code
    with pytest.raises(ValueError):
        assert crs.from_string('{foo: bar}')


def test_from_epsg():
    crs_dict = crs.from_epsg(4326)
    assert crs_dict['init'].lower() == 'epsg:4326'

    # Test with invalid EPSG code
    with pytest.raises(ValueError):
        assert crs.from_epsg(0)


def test_from_epsg_string():
    crs_dict = crs.from_string('epsg:4326')
    assert crs_dict['init'].lower() == 'epsg:4326'

    # Test with invalid EPSG code
    with pytest.raises(ValueError):
        assert crs.from_string('epsg:xyz')


def test_from_string():
    wgs84_crs = crs.from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    assert wgs84_crs == {'no_defs': True, 'ellps': 'WGS84', 'datum': 'WGS84', 'proj': 'longlat'}

    # Make sure this doesn't get handled using the from_epsg() even though 'epsg' is in the string
    epsg_init_crs = crs.from_string('+units=m +init=epsg:26911 +no_defs=True')
    assert epsg_init_crs == {'units': 'm', 'init': 'epsg:26911', 'no_defs': True}


def test_bare_parameters():
    """ Make sure that bare parameters (e.g., no_defs) are handled properly,
    even if they come in with key=True.  This covers interaction with pyproj,
    which makes presents bare parameters as key=<bool>."""

    # Example produced by pyproj
    crs_dict = crs.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert crs_dict.get('no_defs', False) is True

    crs_dict = crs.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=False +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert crs_dict.get('no_defs', True) is False


def test_is_geographic():
    assert is_geographic_crs({'init': 'EPSG:4326'}) is True
    assert is_geographic_crs({'init': 'EPSG:3857'}) is False

    wgs84_crs = crs.from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    assert is_geographic_crs(wgs84_crs) is True

    nad27_crs = crs.from_string('+proj=longlat +ellps=clrk66 +datum=NAD27 +no_defs')
    assert is_geographic_crs(nad27_crs) is True

    lcc_crs = crs.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert is_geographic_crs(lcc_crs) is False


def test_is_projected():
    assert is_projected_crs({'init': 'EPSG:3857'}) is True
    assert is_projected_crs({'init': 'EPSG:4326'}) is False

    lcc_crs = crs.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert is_projected_crs(lcc_crs) is True

    wgs84_crs = crs.from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    assert is_projected_crs(wgs84_crs) is False


def test_is_same_crs():
    crs1 = {'init': 'EPSG:4326'}
    crs2 = {'init': 'EPSG:3857'}

    assert is_same_crs(crs1, crs1) is True
    assert is_same_crs(crs1, crs2) is False

    wgs84_crs = crs.from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    assert is_same_crs(crs1, wgs84_crs) is True

    # Make sure that same projection with different parameter are not equal
    lcc_crs1 = crs.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    lcc_crs2 = crs.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=45 +lat_0=0')
    assert is_same_crs(lcc_crs1, lcc_crs2) is False


def test_to_string():
    assert crs.to_string({'init': 'EPSG:4326'}) == "+init=EPSG:4326"


def test_is_valid_false():
    assert not is_valid_crs('EPSG:432600')


def test_is_valid():
    assert is_valid_crs('EPSG:4326')

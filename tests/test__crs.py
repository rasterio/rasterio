"""crs module tests"""

import json
import logging
import os
import subprocess

import pytest

import rasterio
from rasterio._crs import _CRS
from rasterio.env import env_ctx_if_needed, Env
from rasterio.enums import WktVersion
from rasterio.errors import CRSError

from .conftest import requires_gdal21, requires_gdal22, requires_gdal_lt_3, requires_gdal3


# Items like "D_North_American_1983" characterize the Esri dialect
# of WKT SRS.
ESRI_PROJECTION_STRING = (
    'PROJCS["USA_Contiguous_Albers_Equal_Area_Conic_USGS_version",'
    'GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",'
    'SPHEROID["GRS_1980",6378137.0,298.257222101]],'
    'PRIMEM["Greenwich",0.0],'
    'UNIT["Degree",0.0174532925199433]],'
    'PROJECTION["Albers"],'
    'PARAMETER["false_easting",0.0],'
    'PARAMETER["false_northing",0.0],'
    'PARAMETER["central_meridian",-96.0],'
    'PARAMETER["standard_parallel_1",29.5],'
    'PARAMETER["standard_parallel_2",45.5],'
    'PARAMETER["latitude_of_origin",23.0],'
    'UNIT["Meter",1.0],'
    'VERTCS["NAVD_1988",'
    'VDATUM["North_American_Vertical_Datum_1988"],'
    'PARAMETER["Vertical_Shift",0.0],'
    'PARAMETER["Direction",1.0],UNIT["Centimeter",0.01]]]')


def test_from_dict():
    """Can create a _CRS from a dict"""
    crs = _CRS.from_dict({'init': 'epsg:3857'})
    assert crs.to_dict()['proj'] == 'merc'
    assert 'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84"' in crs.to_wkt()


@pytest.mark.parametrize('south,epsg', [(False, 32631), (True, 32731)])
def test_from_dict_bool_kwarg(south, epsg):
    """Confirm resolution of issue #2246"""
    crs = _CRS.from_dict({'proj': 'utm', 'zone': 31, 'south': south})
    assert crs.to_epsg() == epsg


def test_from_dict_keywords():
    """Can create a CRS from keyword args, ignoring unknowns"""
    crs = _CRS.from_dict(init='epsg:3857', foo='bar')
    assert crs.to_dict()['proj'] == 'merc'
    assert 'PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84"' in crs.to_wkt()


def test_from_epsg():
    """Can create a CRS from EPSG code"""
    crs = _CRS.from_epsg(4326)
    assert crs.to_dict()['proj'] == 'longlat'


@pytest.mark.parametrize('code', [0, -1, float('nan'), 1.3])
def test_from_epsg_error(code):
    """Raise exception with invalid EPSG code"""
    with pytest.raises(ValueError):
        assert _CRS.from_epsg(code)


@pytest.mark.parametrize('proj,expected', [({'init': 'epsg:4326'}, True), ({'init': 'epsg:3857'}, False)])
def test_is_geographic(proj, expected):
    """CRS is or is not geographic"""
    assert _CRS.from_dict(proj).is_geographic is expected


@pytest.mark.parametrize('proj,expected', [({'init': 'epsg:4326'}, False), ({'init': 'epsg:3857'}, True)])
def test_is_projected(proj, expected):
    """CRS is or is not projected"""
    assert _CRS.from_dict(proj).is_projected is expected


def test_equality():
    """CRS are or are not equal"""
    _CRS.from_epsg(4326) == _CRS.from_proj4('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')


def test_to_wkt():
    """CRS converts to WKT"""
    assert _CRS.from_dict({'init': 'epsg:4326'}).to_wkt().startswith('GEOGCS["WGS 84",DATUM')


@pytest.mark.parametrize('proj_string', ['+init=epsg:4326', '+proj=longlat +datum=WGS84 +no_defs'])
def test_to_epsg(proj_string):
    """CRS has EPSG code"""
    assert _CRS.from_proj4(proj_string).to_epsg(confidence_threshold=20) == 4326


@pytest.mark.parametrize('proj_string', [ESRI_PROJECTION_STRING])
def test_esri_wkt_to_epsg(proj_string):
    """CRS has no EPSG code"""
    assert _CRS.from_wkt(proj_string, morph_from_esri_dialect=True).to_epsg() is None


def test_epsg_no_code_available():
    """CRS has no EPSG code"""
    lcc_crs = _CRS.from_proj4('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert lcc_crs.to_epsg() is None


def test_from_wkt_invalid():
    """Raise exception if input WKT is invalid"""
    with pytest.raises(CRSError):
        _CRS.from_wkt('bogus')


@requires_gdal_lt_3
@pytest.mark.parametrize('projection_string', [ESRI_PROJECTION_STRING])
def test_from_esri_wkt_no_fix(projection_string):
    """Test ESRI CRS morphing with no datum fixing"""
    with Env():
        crs = _CRS.from_wkt(projection_string)
        assert 'DATUM["D_North_American_1983"' in crs.to_wkt()


@requires_gdal_lt_3
@pytest.mark.parametrize('projection_string', [ESRI_PROJECTION_STRING])
def test_from_esri_wkt_fix_datum(projection_string):
    """Test ESRI CRS morphing with datum fixing"""
    with Env(GDAL_FIX_ESRI_WKT='DATUM'):
        crs = _CRS.from_wkt(projection_string, morph_from_esri_dialect=True)
        assert 'DATUM["North_American_Datum_1983"' in crs.to_wkt()


@requires_gdal_lt_3
def test_to_esri_wkt_fix_datum():
    """Morph to Esri form"""
    assert 'DATUM["D_North_American_1983"' in _CRS.from_dict(init='epsg:26913').to_wkt(morph_to_esri_dialect=True)


@requires_gdal3
@pytest.mark.parametrize("version", ["WKT2_2019", WktVersion.WKT2_2019])
def test_to_wkt__version(version):
    assert _CRS.from_epsg(4326).to_wkt(version=version).startswith('GEOGCRS["WGS 84",')


@requires_gdal3
def test_to_wkt__env_version():
    with Env(OSR_WKT_FORMAT="WKT2_2018"):
        assert _CRS.from_epsg(4326).to_wkt().startswith('GEOGCRS["WGS 84",')


@requires_gdal3
def test_to_wkt__version_invalid():
    with pytest.raises(ValueError):
        _CRS.from_epsg(4326).to_wkt(version="INVALID")

@requires_gdal_lt_3
def test_to_wkt__version__warning_gdal2():
    with pytest.warns(UserWarning):
        _CRS.from_epsg(4326).to_wkt(version=WktVersion.WKT2_2019)


def test_compound_crs():
    """Parse compound WKT"""
    wkt = """COMPD_CS["unknown",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]],VERT_CS["unknown",VERT_DATUM["unknown",2005],UNIT["metre",1.0,AUTHORITY["EPSG","9001"]],AXIS["Up",UP]]]"""
    assert _CRS.from_wkt(wkt).to_wkt().startswith('COMPD_CS')


def test_exception_proj4():
    """Get the exception message we expect"""
    with pytest.raises(CRSError):
        _CRS.from_proj4("+proj=bogus")


def test_linear_units():
    """CRS linear units can be had"""
    assert _CRS.from_epsg(3857).linear_units == 'metre'

def test_crs_to_dict():
    x = _CRS.from_proj4("+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs")
    expected = {'proj': 'merc',
                'a': 6378137,
                'b': 6378137,
                'lat_ts': 0,
                'lon_0': 0,
                'x_0': 0,
                'y_0': 0,
                'k': 1,
                'units': 'm',
                'nadgrids': '@null',
                'wktext': True,
                'no_defs': True}
    assert x.to_dict() == expected

def test_crs_from_dict():
    expected = {'proj': 'lcc',
                'lat_0': 40,
                'lon_0': -96,
                'lat_1': 20,
                'lat_2': 60,
                'x_0': 0,
                'y_0': 0,
                'datum': 'NAD83',
                'units': 'm',
                'no_defs': True}
    x = _CRS.from_dict(expected)
    assert x.to_dict() == expected

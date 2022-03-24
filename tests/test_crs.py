"""crs module tests"""

import copy
import json
import logging
import pickle
import subprocess

import pytest

import rasterio
from rasterio._base import _can_create_osr
from rasterio.crs import CRS, epsg_treats_as_latlong, epsg_treats_as_northingeasting
from rasterio.enums import WktVersion
from rasterio.env import env_ctx_if_needed, Env
from rasterio.errors import CRSError

from .conftest import (
    gdal_version,
    requires_gdal21,
    requires_gdal22,
    requires_gdal_lt_3,
    requires_gdal3,
    requires_gdal31,
)

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


class CustomCRS:
    def to_wkt(self):
        return CRS.from_epsg(4326).to_wkt()


def test_crs_constructor_dict():
    """Can create a CRS from a dict"""
    crs = CRS({'init': 'epsg:3857'})
    assert crs['init'] == 'epsg:3857'
    assert 'PROJCS["WGS 84 / Pseudo-Mercator"' in crs.wkt


def test_crs_constructor_keywords():
    """Can create a CRS from keyword args, ignoring unknowns"""
    crs = CRS(init='epsg:3857', foo='bar')
    assert crs['init'] == 'epsg:3857'
    assert 'PROJCS["WGS 84 / Pseudo-Mercator"' in crs.wkt


def test_crs_constructor_crs_obj():
    """Can create a CRS from a CRS obj"""
    crs = CRS(CRS(init='epsg:3857'))
    assert crs['init'] == 'epsg:3857'
    assert 'PROJCS["WGS 84 / Pseudo-Mercator"' in crs.wkt


@pytest.fixture(scope='session')
def profile_rgb_byte_tif(path_rgb_byte_tif):
    with rasterio.open(path_rgb_byte_tif) as src:
        return src.profile


def test_read_epsg():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert src.crs.to_epsg() == 32618


def test_read_compdcs():
    """Expect no match for a single EPSG for this COMPDCS"""
    with rasterio.open('zip://tests/data/ak-compdcs.zip!test.tif') as src:
        assert src.crs.to_epsg() == None


@requires_gdal_lt_3
def test_read_esri_wkt():
    with rasterio.open('tests/data/test_esri_wkt.tif') as src:
        assert 'PROJCS["USA_Contiguous_Albers_Equal_Area_Conic_USGS_version",' in src.crs.wkt
        assert 'GEOGCS["GCS_North_American_1983",DATUM["D_North_American_1983",' in src.crs.wkt
        assert src.crs.to_dict() == {
            'datum': 'NAD83',
            'lat_0': 23,
            'lat_1': 29.5,
            'lat_2': 45.5,
            'lon_0': -96,
            'no_defs': True,
            'proj': 'aea',
            'units': 'm',
            'x_0': 0,
            'y_0': 0,
        }


def test_read_no_crs():
    """crs of a dataset with no SRS is None"""
    with rasterio.open('tests/data/389225main_sw_1965_1024.jpg') as src:
        assert src.crs is None


# Ensure that CRS sticks when we write a file.
@pytest.mark.gdalbin
def test_write_3857(tmpdir):
    src_path = str(tmpdir.join('lol.tif'))
    subprocess.call([
        'gdalwarp', '-t_srs', 'epsg:3857',
        'tests/data/RGB.byte.tif', src_path])
    dst_path = str(tmpdir.join('wut.tif'))
    with rasterio.open(src_path) as src:
        with rasterio.open(dst_path, 'w', **src.meta) as dst:
            assert dst.crs.to_epsg() == 3857
    info = subprocess.check_output([
        'gdalinfo', dst_path])
    # WKT string may vary a bit w.r.t GDAL versions
    assert '"WGS 84 / Pseudo-Mercator"' in info.decode('utf-8')


def test_write_bogus_fails(tmpdir, profile_rgb_byte_tif):
    src_path = str(tmpdir.join('lol.tif'))
    profile = profile_rgb_byte_tif.copy()
    profile['crs'] = ['foo']
    with pytest.raises(CRSError):
        rasterio.open(src_path, 'w', **profile)
        # TODO: switch to DatasetWriter here and don't require a .start().


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
    assert wgs84_crs.to_dict() == {'init': 'epsg:4326'}

    # Make sure this doesn't get handled using the from_epsg() even though 'epsg' is in the string
    epsg_init_crs = CRS.from_string('+init=epsg:26911')
    assert epsg_init_crs.to_dict() == {'init': 'epsg:26911'}


@pytest.mark.parametrize('proj,expected', [({'init': 'epsg:4326'}, True), ({'init': 'epsg:3857'}, False)])
def test_is_geographic(proj, expected):
    assert CRS(proj).is_geographic is expected


def test_is_geographic_from_string():
    wgs84_crs = CRS.from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    assert wgs84_crs.is_geographic is True

    nad27_crs = CRS.from_string('+proj=longlat +ellps=clrk66 +datum=NAD27 +no_defs')
    assert nad27_crs.is_geographic is True

    lcc_crs = CRS.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert lcc_crs.is_geographic is False


def test_is_projected():
    assert CRS({'init': 'epsg:3857'}).is_projected is True

    lcc_crs = CRS.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert CRS(lcc_crs).is_projected is True

    wgs84_crs = CRS.from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    assert CRS(wgs84_crs).is_projected is False


@requires_gdal21(reason="CRS equality is buggy pre-2.1")
@pytest.mark.parametrize('epsg_code', [3857, 4326, 26913, 32618])
def test_equality_from_epsg(epsg_code):
    assert CRS.from_epsg(epsg_code) == CRS.from_epsg(epsg_code)


@requires_gdal21(reason="CRS equality is buggy pre-2.1")
@pytest.mark.parametrize('epsg_code', [3857, 4326, 26913, 32618])
def test_equality_from_dict(epsg_code):
    assert CRS.from_dict(init='epsg:{}'.format(epsg_code)) == CRS.from_dict(init='epsg:{}'.format(epsg_code))


def test_is_same_crs():
    crs1 = CRS({'init': 'epsg:4326'})
    crs2 = CRS({'init': 'epsg:3857'})

    assert crs1 == crs1
    assert crs1 != crs2

    wgs84_crs = CRS.from_string('+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs')
    assert crs1 == wgs84_crs

    # Make sure that same projection with different parameter are not equal
    lcc_crs1 = CRS.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    lcc_crs2 = CRS.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc +x_0=0 +units=m +lat_2=77 +lat_1=45 +lat_0=0')
    assert lcc_crs1 != lcc_crs2


def test_null_crs_equality():
    assert CRS() == CRS()
    a = CRS()
    assert a == a
    assert not a != a


def test_null_and_valid_crs_equality():
    assert (CRS() == CRS(init='epsg:4326')) is False


def test_to_string():
    assert CRS({'init': 'epsg:4326'}).to_string() == "EPSG:4326"


def test_is_valid_false():
    with Env(), pytest.raises(CRSError):
        CRS(init='epsg:432600').is_valid


def test_is_valid():
    assert CRS(init='epsg:4326').is_valid


@pytest.mark.parametrize('arg', ['{}', '[]', ''])
def test_empty_json(arg):
    with Env(), pytest.raises(CRSError):
        CRS.from_string(arg)


@pytest.mark.parametrize('arg', [None, {}, ''])
def test_can_create_osr_none_err(arg):
    """Passing None or empty fails"""
    assert not _can_create_osr(arg)


def test_can_create_osr():
    assert _can_create_osr({'init': 'epsg:4326'})
    assert _can_create_osr('epsg:4326')


@pytest.mark.parametrize('arg', ['epsg:-1', 'foo'])
def test_can_create_osr_invalid(arg):
    """invalid CRS definitions fail"""
    with Env():
        assert not _can_create_osr(arg)


@requires_gdal22(
    reason="GDAL bug resolved in 2.2+ allowed invalid CRS to be created")
def test_can_create_osr_invalid_epsg_0():
    assert not _can_create_osr('epsg:')


def test_has_wkt_property():
    assert CRS({'init': 'epsg:4326'}).wkt.startswith('GEOGCS["WGS 84",DATUM')


def test_repr():
    assert repr(CRS({'init': 'epsg:4326'})).startswith("CRS.from_epsg(4326)")


def test_dunder_str():
    assert str(CRS({'init': 'epsg:4326'})) == CRS({'init': 'epsg:4326'}).to_string()


def test_epsg_code_true():
    assert CRS({'init': 'epsg:4326'}).is_epsg_code


def test_epsg():
    assert CRS({'init': 'epsg:4326'}).to_epsg() == 4326
    assert CRS.from_string('+proj=longlat +datum=WGS84 +no_defs').to_epsg() == 4326


def test_epsg__no_code_available():
    lcc_crs = CRS.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc '
                              '+x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert lcc_crs.to_epsg() is None


def test_crs_OSR_equivalence():
    crs1 = CRS.from_string('+proj=longlat +datum=WGS84 +no_defs')
    crs2 = CRS.from_string('+proj=latlong +datum=WGS84 +no_defs')
    crs3 = CRS({'init': 'epsg:4326'})
    assert crs1 == crs2
    assert crs1 == crs3


def test_crs_OSR_no_equivalence():
    crs1 = CRS.from_string('+proj=longlat +datum=WGS84 +no_defs')
    crs2 = CRS.from_string('+proj=longlat +datum=NAD27 +no_defs')
    assert crs1 != crs2


def test_safe_osr_release(tmpdir):
    log = logging.getLogger('rasterio._gdal')
    log.setLevel(logging.DEBUG)
    logfile = str(tmpdir.join('test.log'))
    fh = logging.FileHandler(logfile)
    log.addHandler(fh)

    with rasterio.Env():
        CRS({}) == CRS({})

    log = open(logfile).read()
    assert "Pointer 'hSRS' is NULL in 'OSRRelease'" not in log


@requires_gdal21(reason="CRS equality is buggy pre-2.1")
def test_from_wkt():
    wgs84 = CRS.from_string('+proj=longlat +datum=WGS84 +no_defs')
    from_wkt = CRS.from_wkt(wgs84.wkt)
    assert wgs84.wkt == from_wkt.wkt


def test_from_wkt_invalid():
    with Env(), pytest.raises(CRSError):
        CRS.from_wkt('trash')


def test_from_user_input_epsg():
    assert 'init' in CRS.from_user_input('epsg:4326')


@requires_gdal_lt_3
@pytest.mark.parametrize('projection_string', [ESRI_PROJECTION_STRING])
def test_from_esri_wkt_no_fix(projection_string):
    """Test ESRI CRS morphing with no datum fixing"""
    with Env():
        crs = CRS.from_wkt(projection_string)
        assert 'DATUM["D_North_American_1983"' in crs.wkt


@requires_gdal_lt_3
@pytest.mark.parametrize('projection_string', [ESRI_PROJECTION_STRING])
def test_from_esri_wkt_fix_datum(projection_string):
    """Test ESRI CRS morphing with datum fixing"""
    with Env(GDAL_FIX_ESRI_WKT='DATUM'):
        crs = CRS.from_wkt(projection_string, morph_from_esri_dialect=True)
        assert 'DATUM["North_American_Datum_1983"' in crs.wkt


@requires_gdal_lt_3
def test_to_esri_wkt_fix_datum():
    """Morph to Esri form"""
    assert 'DATUM["D_North_American_1983"' in CRS(init='epsg:26913').to_wkt(morph_to_esri_dialect=True)


@requires_gdal3
@pytest.mark.parametrize("version", ["WKT2_2019", WktVersion.WKT2_2019])
def test_to_wkt__version(version):
    assert CRS.from_epsg(4326).to_wkt(version=version).startswith('GEOGCRS["WGS 84",')


@requires_gdal3
def test_to_wkt__env_version():
    with Env(OSR_WKT_FORMAT="WKT2_2018"):
        assert CRS.from_epsg(4326).to_wkt().startswith('GEOGCRS["WGS 84",')


@requires_gdal3
def test_to_wkt__version_invalid():
    with pytest.raises(ValueError):
        CRS.from_epsg(4326).to_wkt(version="INVALID")


@requires_gdal_lt_3
def test_to_wkt__version__warning_gdal2():
    with pytest.warns(UserWarning):
        CRS.from_epsg(4326).to_wkt(version=WktVersion.WKT2_2019)


def test_compound_crs():
    wkt = """COMPD_CS["unknown",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]],VERT_CS["unknown",VERT_DATUM["unknown",2005],UNIT["metre",1.0,AUTHORITY["EPSG","9001"]],AXIS["Up",UP]]]"""
    assert CRS.from_wkt(wkt).wkt.startswith('COMPD_CS')


def test_dataset_compound_crs():
    with rasterio.open("tests/data/compdcs.vrt") as dataset:
        assert dataset.crs.wkt.startswith('COMPD_CS')


@pytest.mark.wheel
def test_environ_patch(gdalenv, monkeypatch):
    """PROJ_LIB is patched when rasterio._crs is imported"""
    monkeypatch.delenv('GDAL_DATA', raising=False)
    monkeypatch.delenv('PROJ_LIB', raising=False)
    with env_ctx_if_needed():
        assert CRS.from_epsg(4326) != CRS(units='m', proj='aeqd', ellps='WGS84', datum='WGS84', lat_0=-17.0, lon_0=-44.0)


def test_exception():
    """Get the exception we expect"""
    with pytest.raises(CRSError):
        CRS.from_wkt("bogus")


def test_exception_proj4():
    """Get the exception message we expect"""
    with pytest.raises(CRSError):
        CRS.from_proj4("+proj=bogus")


@pytest.mark.parametrize('projection_string', [ESRI_PROJECTION_STRING])
def test_crs_private_wkt(projection_string):
    """Original WKT is saved"""
    CRS.from_wkt(projection_string)._wkt == projection_string


@pytest.mark.parametrize('projection_string', [ESRI_PROJECTION_STRING])
def test_implicit_proj_dict(projection_string):
    """Ensure that old behavior is preserved"""
    assert CRS.from_wkt(projection_string)['proj'] == 'aea'


def test_capitalized_epsg_init():
    """Ensure that old behavior is preserved"""
    assert CRS(init='EPSG:4326').to_epsg() == 4326


def test_issue1609_wktext_a():
    """Check on fix of issue 1609"""
    src_proj = {'ellps': 'WGS84',
            'proj': 'stere',
            'lat_0': -90.0,
            'lon_0': 0.0,
            'x_0': 0.0,
            'y_0': 0.0,
            'lat_ts': -70,
            'no_defs': True}
    wkt = CRS(src_proj).wkt
    assert 'PROJECTION["Polar_Stereographic"]' in wkt
    assert 'PARAMETER["latitude_of_origin",-70]' in wkt


@requires_gdal_lt_3
def test_issue1609_wktext_b():
    """Check on fix of issue 1609"""
    dst_proj = {'ellps': 'WGS84',
               'h': 9000000.0,
               'lat_0': -78.0,
               'lon_0': 0.0,
               'proj': 'nsper',
               'units': 'm',
               'x_0': 0,
               'y_0': 0,
               'wktext': True}
    wkt = CRS(dst_proj).wkt
    assert '+wktext' in wkt


def test_empty_crs_str():
    """str(CRS()) should be empty string"""
    assert str(CRS()) == ''


def test_issue1620():
    """Different forms of EPSG:3857 are equal"""
    assert CRS.from_wkt('PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]],PROJECTION["Mercator_1SP"],PARAMETER["central_meridian",0],PARAMETER["scale_factor",1],PARAMETER["false_easting",0],PARAMETER["false_northing",0],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["X",EAST],AXIS["Y",NORTH],EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext +no_defs"],AUTHORITY["EPSG","3857"]]') == CRS.from_dict(init='epsg:3857')


@pytest.mark.parametrize('factory,arg', [(CRS.from_epsg, 3857), (CRS.from_dict, {'ellps': 'WGS84', 'proj': 'stere', 'lat_0': -90.0, 'lon_0': 0.0, 'x_0': 0.0, 'y_0': 0.0, 'lat_ts': -70, 'no_defs': True})])
def test_pickle(factory, arg):
    """A CRS is pickleable"""
    crs1 = factory(arg)
    crs2 = pickle.loads(pickle.dumps(crs1))
    assert crs2 == crs1


def test_linear_units():
    """CRS linear units can be had"""
    assert CRS.from_epsg(3857).linear_units == 'metre'
    assert CRS.from_epsg(2261).linear_units == 'US survey foot'
    assert CRS.from_epsg(4326).linear_units == 'unknown'


def test_linear_units_factor():
    """CRS linear units can be had"""
    assert CRS.from_epsg(3857).linear_units_factor[0] == 'metre'
    assert CRS.from_epsg(3857).linear_units_factor[1] == 1.0
    assert CRS.from_epsg(2261).linear_units_factor[0] == 'US survey foot'
    assert CRS.from_epsg(2261).linear_units_factor[1] == pytest.approx(0.3048006096012192)
    with pytest.raises(CRSError):
        CRS.from_epsg(4326).linear_units_factor


def test_crs_copy():
    """CRS can be copied"""
    assert copy.copy(CRS.from_epsg(3857)).wkt.startswith('PROJCS["WGS 84 / Pseudo-Mercator",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84"')


def test_crs_hash():
    """hashes of equivalent CRS are equal"""
    assert hash(CRS.from_epsg(3857)) == hash(CRS.from_epsg(3857))


def test_crs_hash_unequal():
    """hashes of non-equivalent CRS are not equal"""
    assert hash(CRS.from_epsg(3857)) != hash(CRS.from_epsg(4326))


def test_crs84():
    """Create CRS from OGC code"""
    assert "WGS 84" in CRS.from_user_input("urn:ogc:def:crs:OGC::CRS84").wkt


@pytest.mark.parametrize("other", ["", 4.2, 0])
def test_equals_different_type(other):
    """Comparison to non-CRS objects is False"""
    assert CRS.from_epsg(4326) != other


def test_from_user_input_custom_crs_class():
    """Support comparison to foreign objects that provide to_wkt()"""
    assert CRS.from_user_input(CustomCRS()) == CRS.from_epsg(4326)


@pytest.mark.parametrize(
    "crs_obj",
    [
        CRS.from_user_input("http://www.opengis.net/def/crs/EPSG/0/4326"),
        pytest.param(
            CRS.from_epsg(4326),
            marks=pytest.mark.xfail(
                gdal_version.major < 3, reason="GDAL 2 always returns False"
            ),
        ),
    ],
)
def test_epsg_treats_as_latlong(crs_obj):
    """EPSG treats this CRS as lat, lon (see also PR #1943)."""
    assert epsg_treats_as_latlong(crs_obj)


@pytest.mark.parametrize(
    "crs_obj",
    [
        CRS.from_user_input("http://www.opengis.net/def/crs/OGC/1.3/CRS84"),
        CRS.from_user_input("http://www.opengis.net/def/crs/EPSG/0/2193"),
        CRS.from_epsg(3857),
        CRS.from_epsg(32618),
    ]
)
def test_epsg_treats_as_latlong_not(crs_obj):
    """EPSG does not treat this CRS as lat, lon (see also PR #1943)."""
    assert not epsg_treats_as_latlong(crs_obj)


@pytest.mark.parametrize(
    "crs_obj",
    [
        CRS.from_user_input("http://www.opengis.net/def/crs/EPSG/0/2193"),
        pytest.param(
            CRS.from_epsg(2193),
            marks=pytest.mark.xfail(
                gdal_version.major < 3, reason="GDAL 2 always returns False"
            ),
        ),
    ],
)
def test_epsg_treats_as_northingeasting(crs_obj):
    """EPSG treats this CRS as northing, easting"""
    assert epsg_treats_as_northingeasting(crs_obj)


@pytest.mark.parametrize(
    "crs_obj",
    [
        CRS.from_epsg(32618),
        CRS.from_epsg(3857),
        CRS.from_user_input("http://www.opengis.net/def/crs/OGC/1.3/CRS84"),
        CRS.from_user_input("http://www.opengis.net/def/crs/EPSG/0/4326"),
    ],
)
def test_epsg_treats_as_northingeasting_not(crs_obj):
    """EPSG does not treat this CRS as northing, easting"""
    assert not epsg_treats_as_northingeasting(crs_obj)


def test_from_string__wkt_with_proj():
    wkt = (
        'PROJCS["WGS 84 / Pseudo-Mercator",'
        'GEOGCS["WGS 84",'
        '    DATUM["WGS_1984",'
        '        SPHEROID["WGS 84",6378137,298.257223563,'
        '            AUTHORITY["EPSG","7030"]],'
        '        AUTHORITY["EPSG","6326"]],'
        '    PRIMEM["Greenwich",0,'
        '        AUTHORITY["EPSG","8901"]],'
        '    UNIT["degree",0.0174532925199433,'
        '        AUTHORITY["EPSG","9122"]],'
        '    AUTHORITY["EPSG","4326"]],'
        'PROJECTION["Mercator_1SP"],'
        'PARAMETER["central_meridian",0],'
        'PARAMETER["scale_factor",1],'
        'PARAMETER["false_easting",0],'
        'PARAMETER["false_northing",0],'
        'UNIT["metre",1,'
        '    AUTHORITY["EPSG","9001"]],'
        'AXIS["Easting",EAST],'
        'AXIS["Northing",NORTH],'
        'EXTENSION["PROJ4","+proj=merc +a=6378137 +b=6378137 +lat_ts=0 '
        '+lon_0=0 +x_0=0 +y_0=0 +k=1 +units=m +nadgrids=@null +wktext +no_defs"],'
        'AUTHORITY["EPSG","3857"]] '
    )
    assert CRS.from_string(wkt).to_epsg() == 3857


@requires_gdal3
def test_esri_auth__from_string():
    assert CRS.from_string('ESRI:54009').to_string() == 'ESRI:54009'


@requires_gdal3
def test_esri_auth__to_epsg():
    assert CRS.from_user_input('ESRI:54009').to_epsg() is None


@requires_gdal3
def test_esri_auth__to_authority():
    assert CRS.from_user_input('ESRI:54009').to_authority() == ('ESRI', '54009')


def test_from_authority__to_authority():
    assert CRS.from_authority("EPSG", 4326).to_authority() == ("EPSG", "4326")


def test_to_authority__no_code_available():
    lcc_crs = CRS.from_string('+lon_0=-95 +ellps=GRS80 +y_0=0 +no_defs=True +proj=lcc '
                              '+x_0=0 +units=m +lat_2=77 +lat_1=49 +lat_0=0')
    assert lcc_crs.to_authority() is None


@pytest.mark.parametrize(
    'crs_obj,result',
    [
        (CRS.from_user_input("http://www.opengis.net/def/crs/OGC/1.3/CRS84"), False),
        (CRS.from_user_input("http://www.opengis.net/def/crs/EPSG/0/2193"), False),
        (CRS.from_user_input("http://www.opengis.net/def/crs/EPSG/0/4326"), True),
    ]
)
def test_is_latlong(crs_obj, result):
    """Test if CRS should be treated as latlon."""
    assert epsg_treats_as_latlong(crs_obj) == result


@pytest.mark.parametrize(
    'crs_obj,result',
    [
        (CRS.from_user_input("http://www.opengis.net/def/crs/OGC/1.3/CRS84"), False),
        (CRS.from_user_input("http://www.opengis.net/def/crs/EPSG/0/2193"), True),
        (CRS.from_user_input("http://www.opengis.net/def/crs/EPSG/0/4326"), False),
    ]
)
def test_is_northingeasting(crs_obj, result):
    """Test if CRS should be treated as having northing/easting coordinate ordering."""
    assert epsg_treats_as_northingeasting(crs_obj) == result


@requires_gdal_lt_3
@pytest.mark.parametrize('crs_obj', [CRS.from_epsg(4326), CRS.from_epsg(2193)])
def test_latlong_northingeasting_gdal2(crs_obj):
    """Check CRS created from epsg with GDAL 2 always return False."""
    assert not epsg_treats_as_latlong(crs_obj)
    assert not epsg_treats_as_northingeasting(crs_obj)


@requires_gdal3
def test_latlong_northingeasting_gdal3():
    """Check CRS created from epsg with GDAL 3."""
    assert epsg_treats_as_latlong(CRS.from_epsg(4326))
    assert epsg_treats_as_northingeasting(CRS.from_epsg(2193))


@requires_gdal3
def test_tmerc_no_match():
    """Should not match an authority, see issue #2293."""
    s = "+proj=tmerc +lat_0=0 +lon_0=10.7584 +k=0.9996 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
    crs = CRS.from_string(s)
    assert crs.to_epsg() is None


@requires_gdal31
def test_crs_to_json_dict():
    aeqd_crs = CRS(proj="aeqd", lon_0=-80, lat_0=40.5)
    json_dict = aeqd_crs.to_dict(projjson=True)
    assert json_dict["type"] == "ProjectedCRS"


@requires_gdal31
def test_crs_to_json_dict__empty():
    crs = CRS()
    assert crs.to_dict(projjson=True) == {}


@requires_gdal31
def test_crs_from_json_dict():
    aeqd_crs = CRS(proj="aeqd", lon_0=-80, lat_0=40.5)
    assert CRS.from_dict(aeqd_crs.to_dict(projjson=True)) == aeqd_crs


@requires_gdal31
def test_crs_from_json_dict__user_input():
    aeqd_crs = CRS(proj="aeqd", lon_0=-80, lat_0=40.5)
    assert CRS.from_user_input(aeqd_crs.to_dict(projjson=True)) == aeqd_crs


@requires_gdal31
def test_crs_from_json_dict__init():
    aeqd_crs = CRS(proj="aeqd", lon_0=-80, lat_0=40.5)
    assert CRS(aeqd_crs.to_dict(projjson=True)) == aeqd_crs


@requires_gdal31
def test_crs_proj_json__user_input():
    aeqd_crs = CRS(proj="aeqd", lon_0=-80, lat_0=40.5)
    assert CRS.from_user_input(json.dumps(aeqd_crs.to_dict(projjson=True))) == aeqd_crs


@requires_gdal31
def test_crs_proj_json__from_string():
    aeqd_crs = CRS(proj="aeqd", lon_0=-80, lat_0=40.5)
    assert CRS.from_string(json.dumps(aeqd_crs.to_dict(projjson=True))) == aeqd_crs

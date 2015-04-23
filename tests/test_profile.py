import pytest

import rasterio
from rasterio.profiles import Profile, DefaultGTiffProfile
from rasterio.profiles import default_gtiff_profile


def test_base_profile():
    assert Profile()()['driver'] is None


def test_base_profile_kwarg():
    assert Profile()(foo='bar')['foo'] == 'bar'


def test_gtiff_profile_format():
    assert DefaultGTiffProfile()()['driver'] == 'GTiff'


def test_gtiff_profile_interleave():
    assert DefaultGTiffProfile()()['interleave'] == 'band'


def test_gtiff_profile_tiled():
    assert DefaultGTiffProfile()()['tiled'] == True


def test_gtiff_profile_blockxsize():
    assert DefaultGTiffProfile()()['blockxsize'] == 256


def test_gtiff_profile_blockysize():
    assert DefaultGTiffProfile()()['blockysize'] == 256


def test_gtiff_profile_compress():
    assert DefaultGTiffProfile()()['compress'] == 'lzw'


def test_gtiff_profile_nodata():
    assert DefaultGTiffProfile()()['nodata'] == 0


def test_gtiff_profile_dtype():
    assert DefaultGTiffProfile()()['dtype'] == rasterio.uint8


def test_gtiff_profile_other():
    assert DefaultGTiffProfile()(count=3)['count'] == 3


def test_gtiff_profile_dtype_override():
    assert DefaultGTiffProfile()(dtype='uint16')['dtype'] == rasterio.uint16


def test_gtiff_profile_protected_driver():
    """Overriding the driver is not allowed."""
    with pytest.raises(ValueError):
        DefaultGTiffProfile()(driver='PNG')


def test_open_with_profile(tmpdir):
        tiffname = str(tmpdir.join('foo.tif'))
        with rasterio.open(
                tiffname,
                'w',
                **default_gtiff_profile(
                    count=1, width=1, height=1)) as dst:
            data = dst.read()
            assert data.flatten().tolist() == [0]


def test_profile_overlay():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        kwds = src.meta
    kwds.update(**default_gtiff_profile())
    assert kwds['tiled']
    assert kwds['compress'] == 'lzw'
    assert kwds['count'] == 3

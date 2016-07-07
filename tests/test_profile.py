import warnings

import pytest

import rasterio
from rasterio.profiles import Profile, DefaultGTiffProfile
from rasterio.profiles import default_gtiff_profile


def test_base_profile():
    assert 'driver' not in Profile()


def test_base_profile_kwarg():
    assert Profile(foo='bar')['foo'] == 'bar'


def test_gtiff_profile_format(recwarn):
    assert DefaultGTiffProfile()['driver'] == 'GTiff'
    warnings.simplefilter('always')
    assert DefaultGTiffProfile()()['driver'] == 'GTiff'
    assert len(recwarn) == 1
    assert recwarn.pop(DeprecationWarning)


def test_gtiff_profile_interleave():
    assert DefaultGTiffProfile()['interleave'] == 'band'


def test_gtiff_profile_tiled():
    assert DefaultGTiffProfile()['tiled'] is True


def test_gtiff_profile_blockxsize():
    assert DefaultGTiffProfile()['blockxsize'] == 256


def test_gtiff_profile_blockysize():
    assert DefaultGTiffProfile()['blockysize'] == 256


def test_gtiff_profile_compress():
    assert DefaultGTiffProfile()['compress'] == 'lzw'


def test_gtiff_profile_nodata():
    assert DefaultGTiffProfile()['nodata'] == 0


def test_gtiff_profile_dtype():
    assert DefaultGTiffProfile()['dtype'] == rasterio.uint8


def test_gtiff_profile_other():
    assert DefaultGTiffProfile(count=3)['count'] == 3


def test_gtiff_profile_dtype_override():
    assert DefaultGTiffProfile(dtype='uint16')['dtype'] == rasterio.uint16


def test_open_with_profile(tmpdir):
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open(tiffname, 'w', **default_gtiff_profile(
            count=1, width=256, height=256)) as dst:
        assert not dst.closed


def test_blockxsize_guard(tmpdir):
    """blockxsize can't be greater than image width."""
    tiffname = str(tmpdir.join('foo.tif'))
    with pytest.raises(ValueError):
        rasterio.open(tiffname, 'w', **default_gtiff_profile(
            count=1, width=128, height=256))


def test_blockysize_guard(tmpdir):
    """blockysize can't be greater than image height."""
    tiffname = str(tmpdir.join('foo.tif'))
    with pytest.raises(ValueError):
        rasterio.open(tiffname, 'w', **default_gtiff_profile(
            count=1, width=256, height=128))


def test_profile_overlay():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        kwds = src.profile
    kwds.update(**default_gtiff_profile())
    assert kwds['tiled']
    assert kwds['compress'] == 'lzw'
    assert kwds['count'] == 3


def test_dataset_profile_property_tiled(data):
    """An tiled dataset's profile has block sizes"""
    with rasterio.open('tests/data/shade.tif') as src:
        assert src.profile['blockxsize'] == 256
        assert src.profile['blockysize'] == 256
        assert src.profile['tiled'] is True


def test_dataset_profile_property_untiled(data):
    """An untiled dataset's profile has no block sizes"""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        assert 'blockxsize' not in src.profile
        assert 'blockysize' not in src.profile
        assert src.profile['tiled'] is False


def test_dataset_profile_creation_kwds(data):
    """Updated creation keyword tags appear in profile"""
    tiffile = str(data.join('RGB.byte.tif'))
    with rasterio.open(tiffile, 'r+') as src:
        src.update_tags(ns='rio_creation_kwds', foo='bar')
        assert src.profile['tiled'] is False
        assert src.profile['foo'] == 'bar'


def test_profile_affine_stashing(recwarn):
    """Passing affine sets transform, with a warning"""
    warnings.simplefilter('always')
    profile = Profile(affine='foo')
    assert len(recwarn) == 1
    assert recwarn.pop(DeprecationWarning)
    assert 'affine' not in profile
    assert profile['transform'] == 'foo'


def test_profile_mixed_error():
    """Passing both affine and transform raises TypeError"""
    with pytest.raises(TypeError):
        Profile(affine='foo', transform='bar')


def test_profile_affine_alias(recwarn):
    """affine is an alias for transform, with a warning"""
    profile = Profile(transform='foo')
    warnings.simplefilter('always')
    assert profile['affine'] == 'foo'
    assert len(recwarn) == 1
    assert recwarn.pop(DeprecationWarning)


def test_profile_affine_set():
    """TypeError is raised on set of affine item"""
    profile = Profile()
    profile['transform'] = 'foo'
    with pytest.raises(TypeError):
        profile['affine'] = 'bar'

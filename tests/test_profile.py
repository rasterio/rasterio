import warnings

import pytest

import rasterio
from rasterio.errors import RasterioDeprecationWarning
from rasterio.profiles import Profile, DefaultGTiffProfile
from rasterio.profiles import default_gtiff_profile


def test_base_profile():
    assert 'driver' not in Profile()


def test_base_profile_kwarg():
    assert Profile(foo='bar')['foo'] == 'bar'


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
    profile = default_gtiff_profile.copy()
    profile.update(count=1, width=256, height=256)
    with rasterio.open(tiffname, 'w', **profile) as dst:
        assert not dst.closed


def test_blockxsize_guard(tmpdir):
    """blockxsize can't be greater than image width."""
    tiffname = str(tmpdir.join('foo.tif'))
    with pytest.raises(ValueError):
        profile = default_gtiff_profile.copy()
        profile.update(count=1, height=256, width=128)
        rasterio.open(tiffname, 'w', **profile)


def test_blockysize_guard(tmpdir):
    """blockysize can't be greater than image height."""
    tiffname = str(tmpdir.join('foo.tif'))
    with pytest.raises(ValueError):
        profile = default_gtiff_profile.copy()
        profile.update(count=1, width=256, height=128)
        rasterio.open(tiffname, 'w', **profile)


def test_profile_overlay():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        kwds = src.profile
    kwds.update(**default_gtiff_profile)
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


def test_profile_affine_set():
    """TypeError is raised on set of affine item"""
    profile = Profile()
    profile['transform'] = 'foo'
    with pytest.raises(TypeError):
        profile['affine'] = 'bar'


def test_creation_kwds_deprecation():
    """Rasterio creation kwds metadata is deprecated"""
    with pytest.warns(RasterioDeprecationWarning):
        with rasterio.open('tests/data/alpha.tif') as src:
            src.profile


def test_creation_kwds_ignore(monkeypatch):
    """Successfully opt in to metadata blackout"""
    monkeypatch.setenv('RIO_IGNORE_CREATION_KWDS', 'TRUE')
    with pytest.warns(None) as record:
        with rasterio.open('tests/data/alpha.tif') as src:
            src.profile
        assert len(record) == 0


def test_kwds_deprecation():
    """kwds property is deprecated"""
    with pytest.warns(RasterioDeprecationWarning):
        with rasterio.open('tests/data/alpha.tif') as src:
            assert src.kwds['tiled']

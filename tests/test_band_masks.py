import logging
import sys

import numpy as np
import pytest

import rasterio
from rasterio.enums import MaskFlags
from rasterio.errors import NodataShadowWarning

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


@pytest.fixture(scope='function')
def tiffs(tmpdir):
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        profile = src.profile

        shadowed_profile = profile.copy()
        shadowed_profile['count'] = 4
        with rasterio.open(
                str(tmpdir.join('shadowed.tif')), 'w',
                **shadowed_profile) as dst:

            for i, band in enumerate(src.read(masked=False), 1):
                dst.write(band, i)
            dst.write(band, 4)

        del profile['nodata']
        with rasterio.open(
                str(tmpdir.join('no-nodata.tif')), 'w',
                **profile) as dst:
            dst.write(src.read(masked=False))

        with rasterio.open(
                str(tmpdir.join('sidecar-masked.tif')), 'w',
                **profile) as dst:
            dst.write(src.read(masked=False))
            mask = np.zeros(src.shape, dtype='uint8')
            dst.write_mask(mask)

    return tmpdir

def test_mask_flags():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        for flags in src.mask_flags:
            assert flags & MaskFlags.nodata
            assert not flags & MaskFlags.per_dataset
            assert not flags & MaskFlags.alpha


def test_mask_flags_sidecar(tiffs):
    filename = str(tiffs.join('sidecar-masked.tif'))
    with rasterio.open(filename) as src:
        for flags in src.mask_flags:
            assert not flags & MaskFlags.nodata
            assert not flags & MaskFlags.alpha
            assert flags & MaskFlags.per_dataset


def test_mask_flags_shadow(tiffs):
    filename = str(tiffs.join('shadowed.tif'))
    with rasterio.open(filename) as src:
        for flags in src.mask_flags:
            assert flags & MaskFlags.nodata
            assert not flags & MaskFlags.alpha
            assert not flags & MaskFlags.per_dataset


def test_warning_no():
    """No shadow warning is raised"""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        try:
            rm, gm, bm = src.read_masks()
        except NodataShadowWarning:
            pytest.fail("Unexpected NodataShadowWarning raised")


def test_warning_shadow(tiffs):
    """Shadow warning is raised"""
    filename = str(tiffs.join('shadowed.tif'))
    with rasterio.open(filename) as src:
        with pytest.warns(NodataShadowWarning):
            src.read_masks()


def test_masks():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        rm, gm, bm = src.read_masks()
        r, g, b = src.read(masked=False)
        assert not r[rm == 0].any()
        assert not g[gm == 0].any()
        assert not b[bm == 0].any()


def test_masked_true():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        r, g, b = src.read(masked=True)
        rm, gm, bm = src.read_masks()
        assert (r.mask == ~rm.astype('bool')).all()
        assert (g.mask == ~gm.astype('bool')).all()
        assert (b.mask == ~bm.astype('bool')).all()


def test_masked_none():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        r, g, b = src.read(masked=True)
        rm, gm, bm = src.read_masks()
        assert (r.mask == ~rm.astype('bool')).all()
        assert (g.mask == ~gm.astype('bool')).all()
        assert (b.mask == ~bm.astype('bool')).all()


def test_masking_no_nodata(tiffs):
    # if the dataset has no defined nodata values, all data is
    # considered valid data. The GDAL masks bands are arrays of
    # 255 values. ``read()`` returns masked arrays where `mask`
    # is False.
    filename = str(tiffs.join('no-nodata.tif'))
    with rasterio.open(filename) as src:
        for flags in src.mask_flags:
            assert flags & MaskFlags.all_valid
            assert not flags & MaskFlags.alpha
            assert not flags & MaskFlags.nodata

        rgb = src.read(masked=False)
        assert not hasattr(rgb, 'mask')
        r = src.read(1, masked=False)
        assert not hasattr(r, 'mask')

        rgb = src.read(masked=True)
        assert hasattr(rgb, 'mask')
        assert not rgb.mask.any()
        r = src.read(1, masked=True)
        assert hasattr(r, 'mask')
        assert not r.mask.any()

        rgb = src.read(masked=True)
        assert hasattr(rgb, 'mask')
        assert not r.mask.any()
        r = src.read(1, masked=True)
        assert not r.mask.any()

        masks = src.read_masks()
        assert masks.all()


def test_masking_sidecar_mask(tiffs):
    # If the dataset has a .msk sidecar mask band file, all masks will
    # be derived from that file.
    with rasterio.open(str(tiffs.join('sidecar-masked.tif'))) as src:
        for flags in src.mask_flags:
            assert flags & MaskFlags.per_dataset
            assert not flags & MaskFlags.alpha
            assert not flags & MaskFlags.nodata
        rgb = src.read(masked=True)
        assert rgb.mask.all()
        r = src.read(1, masked=True)
        assert r.mask.all()
        masks = src.read_masks()
        assert not masks.any()

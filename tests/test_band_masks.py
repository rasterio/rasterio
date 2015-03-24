import logging
import sys

import numpy as np
from pytest import fixture

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_masks():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        rm, gm, bm = src.read_masks()
        r, g, b = src.read(masked=False)
        assert not r[rm==0].any()
        assert not g[gm==0].any()
        assert not b[bm==0].any()


def test_masked_true():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        r, g, b = src.read(masked=True)
        rm, gm, bm = src.read_masks()
        assert (r.mask==~rm.astype('bool')).all()
        assert (g.mask==~gm.astype('bool')).all()
        assert (b.mask==~bm.astype('bool')).all()


def test_masked_none():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        r, g, b = src.read(masked=True)
        rm, gm, bm = src.read_masks()
        assert (r.mask==~rm.astype('bool')).all()
        assert (g.mask==~gm.astype('bool')).all()
        assert (b.mask==~bm.astype('bool')).all()


@fixture(scope='function')
def tiffs(tmpdir):
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        kwds = src.meta
        
        del kwds['nodata']
        with rasterio.open(
                str(tmpdir.join('no-nodata.tif')), 'w',
                **kwds) as dst:
            dst.write(src.read(masked=False))

        with rasterio.open(
                str(tmpdir.join('sidecar-masked.tif')), 'w',
                **kwds) as dst:
            dst.write(src.read(masked=False))
            mask = np.zeros(src.shape, dtype='uint8')
            dst.write_mask(mask)

    return tmpdir


def test_masking_no_nodata(tiffs):
    # if the dataset has no defined nodata values, all data is
    # considered valid data. The GDAL masks bands are arrays of
    # 255 values. ``read()`` returns masked arrays where `mask`
    # is False.
    filename = str(tiffs.join('no-nodata.tif'))
    with rasterio.open(filename) as src:

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

        rgb = src.read()
        assert hasattr(rgb, 'mask')
        assert not r.mask.any()
        r = src.read(1)
        assert not r.mask.any()

        masks = src.read_masks()
        assert masks.all()


def test_masking_sidecar_mask(tiffs):
    # If the dataset has a .msk sidecar mask band file, all masks will
    # be derived from that file.
    with rasterio.open(str(tiffs.join('sidecar-masked.tif'))) as src:
        rgb = src.read()
        assert rgb.mask.all()
        r = src.read(1)
        assert r.mask.all()
        masks = src.read_masks()
        assert not masks.any()

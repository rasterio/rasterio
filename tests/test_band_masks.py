import numpy as np
from pytest import fixture

import rasterio


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

        kwds['nodata'] = -1.0e20
        with rasterio.open(
                str(tmpdir.join('out-of-range-nodata.tif')), 'w',
                **kwds) as dst:
            dst.write(src.read(masked=False))

        del kwds['nodata']
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
    # 255 values. ``read()`` returns unmasked arrays unless masked
    # arrays are demanded with ``masked=True``, in which case the
    # masks are uniformly False.
    with rasterio.open(str(tiffs.join('no-nodata.tif'))) as src:
        rgb = src.read()
        assert not hasattr(rgb, 'mask')
        r = src.read(1)
        assert not hasattr(r, 'mask')

        r = src.read(1, masked=True)
        assert not r.mask.any()

        masks = src.read_masks()
        assert masks.all()


def test_masking_out_of_range_nodata(tiffs):
    # If the dataset has defined nodata values outside the range of the
    # corresponding band data types (like -9999 for an 8-bit band), GDAL
    # masks bands are computed using the nearest valid data type value
    # (0 in the case above). ``read()`` returns masked arrays unless
    # explicitly not requested with ``masked=False``.
    with rasterio.open(str(tiffs.join('out-of-range-nodata.tif'))) as src:
        rgb = src.read()
        assert hasattr(rgb, 'mask')
        r = src.read(1)
        assert hasattr(r, 'mask')
        masks = src.read_masks()
        assert masks.any()


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

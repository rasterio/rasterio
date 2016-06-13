"""
Tests of band mask creation, both .msk sidecar and internal.
"""

import pytest
import rasterio
from rasterio.enums import MaskFlags


def test_create_internal_mask(data):
    """Write an internal mask to the fixture's RGB.byte.tif."""
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(str(data.join('RGB.byte.tif')), 'r+') as dst:
            blue = dst.read(1, masked=False)
            mask = 255 * (blue == 0).astype('uint8')
            dst.write_mask(mask)

    # There should be no .msk file
    assert data.join('RGB.byte.tif').exists()
    assert not data.join('RGB.byte.tif.msk').exists()

    # Check that the mask was saved correctly.
    with rasterio.open(str(data.join('RGB.byte.tif'))) as src:
        assert (mask == src.read_mask()).all()
        for flags in src.mask_flags:
            assert flags & MaskFlags.per_dataset
            assert not flags & MaskFlags.alpha
            assert not flags & MaskFlags.nodata


def test_create_sidecar_mask(data):
    """Write a .msk sidecar mask."""
    with rasterio.open(str(data.join('RGB.byte.tif')), 'r+') as dst:
        blue = dst.read(1, masked=False)
        mask = 255 * (blue == 0).astype('uint8')
        dst.write_mask(mask)

    # There should be a .msk file in this case.
    assert data.join('RGB.byte.tif').exists()
    assert data.join('RGB.byte.tif.msk').exists()

    # Check that the mask was saved correctly.
    with rasterio.open(str(data.join('RGB.byte.tif'))) as src:
        assert (mask == src.read_mask()).all()
        for flags in src.mask_flags:
            assert flags & MaskFlags.per_dataset
            assert not flags & MaskFlags.alpha
            assert not flags & MaskFlags.nodata

    # Check the .msk file, too.
    with rasterio.open(str(data.join('RGB.byte.tif.msk'))) as msk:
        assert (mask == msk.read(1, masked=False)).all()


def test_create_mask_windowed_sidecar(data):
    """Writing masks by window succeeds with sidecar mask
    """
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(str(data.join('RGB.byte.tif')), 'r+') as dst:
            for ij, window in dst.block_windows():
                blue = dst.read(1, window=window, masked=False)
                mask = 255 * (blue == 0).astype('uint8')
                dst.write_mask(mask, window=window)


@pytest.mark.xfail(reason="https://github.com/mapbox/rasterio/issues/781")
def test_create_mask_windowed_internal(data):
    """Writing masks by window with internal mask
    Currently fails with
        rasterio.errors.RasterioIOError: Failed to get mask.
    """
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(str(data.join('RGB.byte.tif')), 'r+') as dst:
            for ij, window in dst.block_windows():
                blue = dst.read(1, window=window, masked=False)
                mask = 255 * (blue == 0).astype('uint8')
                dst.write_mask(mask, window=window)

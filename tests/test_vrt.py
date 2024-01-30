"""Tests of the rasterio.vrt module"""

import rasterio
from rasterio.vrt import _boundless_vrt_doc, VirtualDataset


def test_boundless_vrt(path_rgb_byte_tif):
    with rasterio.open(path_rgb_byte_tif) as rgb:
        doc = _boundless_vrt_doc(rgb)
        assert doc.startswith("<VRTDataset")
        with rasterio.open(doc) as vrt:
            assert rgb.count == vrt.count
            assert rgb.dtypes == vrt.dtypes
            assert rgb.mask_flag_enums == vrt.mask_flag_enums


def test_boundless_msk_vrt(path_rgb_msk_byte_tif):
    with rasterio.open(path_rgb_msk_byte_tif) as msk:
        doc = _boundless_vrt_doc(msk)
        assert doc.startswith("<VRTDataset")
        with rasterio.open(doc) as vrt:
            assert msk.count == vrt.count
            assert msk.dtypes == vrt.dtypes
            assert msk.mask_flag_enums == vrt.mask_flag_enums


def test_virtual_dataset_fromstring(path_rgb_byte_tif):
    with rasterio.open(path_rgb_byte_tif) as rgb:
        doc = _boundless_vrt_doc(rgb)

        with VirtualDataset.fromstring(doc) as vrtfile, vrtfile.open() as vrt:
            assert rgb.count == vrt.count
            assert rgb.dtypes == vrt.dtypes
            assert rgb.mask_flag_enums == vrt.mask_flag_enums


def test_virtual_dataset_constructor():
    vrt = VirtualDataset(height=10, width=11)
    assert vrt.height == 10
    assert vrt.width == 11

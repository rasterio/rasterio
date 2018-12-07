"""Tests of the rasterio.vrt module"""

import rasterio
import rasterio.vrt


def test_boundless_vrt(path_rgb_byte_tif):
    with rasterio.open(path_rgb_byte_tif) as rgb:
        doc = rasterio.vrt._boundless_vrt_doc(rgb)
        assert doc.startswith('<VRTDataset')
        with rasterio.open(doc) as vrt:
            assert rgb.count == vrt.count
            assert rgb.dtypes == vrt.dtypes
            assert rgb.mask_flag_enums == vrt.mask_flag_enums


def test_boundless_msk_vrt(path_rgb_msk_byte_tif):
    with rasterio.open(path_rgb_msk_byte_tif) as msk:
        doc = rasterio.vrt._boundless_vrt_doc(msk)
        assert doc.startswith('<VRTDataset')
        with rasterio.open(doc) as vrt:
            assert msk.count == vrt.count
            assert msk.dtypes == vrt.dtypes
            assert msk.mask_flag_enums == vrt.mask_flag_enums

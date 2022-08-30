"""Tests of the rasterio.vrt module"""

from numpy.testing import assert_array_equal

import rasterio
import rasterio.vrt
from rasterio.enums import Resampling
from rasterio.coords import BoundingBox
from affine import Affine
import pytest


from .conftest import gdal_version


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


def test_build_vrt__attributes(path_rgb_byte_tif):
    with rasterio.vrt.BuildVRT(
        [path_rgb_byte_tif]
    ) as vrt, rasterio.open(path_rgb_byte_tif) as rds:
        assert vrt.name == ""
        assert rds.count == vrt.count
        assert rds.crs == vrt.crs
        assert rds.transform == vrt.transform
        if gdal_version.at_least("3.3"):
            assert rds.gcps == vrt.gcps
        assert rds.units == vrt.units
        assert rds.descriptions == vrt.descriptions
        assert rds.dtypes == vrt.dtypes
        assert rds.shape == vrt.shape
        assert rds.nodata == vrt.nodata
        vrt_profile = vrt.profile.copy()
        assert vrt_profile.pop("driver") == "VRT"
        assert vrt_profile.pop("blockxsize") == 128
        assert vrt_profile.pop("blockysize") == 128
        assert vrt_profile.pop("tiled") is True
        rds_profile = rds.profile.copy()
        rds_profile.pop("tiled")
        rds_profile.pop("blockysize")
        rds_profile.pop("driver")
        rds_profile.pop("interleave")
        assert rds_profile == vrt_profile
        assert vrt.block_shapes == [(128, 128), (128, 128), (128, 128)]
        assert_array_equal(vrt.read(), rds.read())


def test_build_vrt__dst_path(path_rgb_byte_tif, tmp_path):
    dst_file = tmp_path / "file.vrt"
    with rasterio.vrt.BuildVRT(
        file_paths=[path_rgb_byte_tif],
        dst_path=dst_file,
    ) as vrt:
        assert vrt.name == str(dst_file)

    with rasterio.open(dst_file) as vrt, rasterio.open(path_rgb_byte_tif) as rds:
        assert rds.count == vrt.count
        assert rds.crs == vrt.crs
        assert rds.transform == vrt.transform
        if gdal_version.at_least("3.3"):
            assert rds.gcps == vrt.gcps
        assert rds.units == vrt.units
        assert rds.descriptions == vrt.descriptions
        assert rds.dtypes == vrt.dtypes
        assert rds.shape == vrt.shape
        assert rds.nodata == vrt.nodata
        vrt_profile = vrt.profile.copy()
        assert vrt_profile.pop("driver") == "VRT"
        assert vrt_profile.pop("blockxsize") == 128
        assert vrt_profile.pop("blockysize") == 128
        assert vrt_profile.pop("tiled") is True
        rds_profile = rds.profile.copy()
        rds_profile.pop("tiled")
        rds_profile.pop("blockysize")
        rds_profile.pop("driver")
        rds_profile.pop("interleave")
        assert rds_profile == vrt_profile
        assert vrt.block_shapes == [(128, 128), (128, 128), (128, 128)]
        assert_array_equal(vrt.read(), rds.read())


def test_build_vrt__multi(directory_with_overlapping_rasters):
    with rasterio.vrt.BuildVRT(
        directory_with_overlapping_rasters.iterdir(),
    ) as vrt:
        assert vrt.name == ""
        assert vrt.count == 1
        assert vrt.shape == (15, 15)
        assert vrt.crs == 4326
        assert vrt.transform.almost_equals(
            Affine(0.2, 0.0, -114.0, 0.0, -0.2, 46.0)
        )
        assert vrt.bounds == BoundingBox(
            left=-114.0, bottom=43.0, right=-111.0, top=46.0
        )
        assert_array_equal(vrt.read()[:, 5:10, 5:10], 3)

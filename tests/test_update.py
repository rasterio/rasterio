
import shutil
import subprocess
import re

import affine
import numpy as np
import pytest

import rasterio

def test_update_tags(data):
    tiffname = str(data.join('RGB.byte.tif'))
    with rasterio.open(tiffname, 'r+') as f:
        f.update_tags(a='1', b='2')
        f.update_tags(1, c=3)
        with pytest.raises(IndexError):
            f.update_tags(4, d=4)
        assert f.tags() == {'AREA_OR_POINT': 'Area', 'a': '1', 'b': '2'}
        assert ('c', '3') in f.tags(1).items()
    info = subprocess.check_output(["gdalinfo", tiffname]).decode('utf-8')
    assert re.search("Metadata:\W+a=1\W+AREA_OR_POINT=Area\W+b=2", info)


def test_update_band(data):
    tiffname = str(data.join('RGB.byte.tif'))
    with rasterio.open(tiffname, 'r+') as f:
        f.write(np.zeros(f.shape, dtype=f.dtypes[0]), indexes=1)
    with rasterio.open(tiffname) as f:
        assert not f.read(1).any()


def test_update_spatial(data):
    tiffname = str(data.join('RGB.byte.tif'))
    with rasterio.open(tiffname, 'r+') as f:
        f.transform = affine.Affine.from_gdal(1.0, 1.0, 0.0, 0.0, 0.0, -1.0)
        f.crs = {'init': 'epsg:4326'}
    with rasterio.open(tiffname) as f:
        assert f.transform == affine.Affine.from_gdal(
            1.0, 1.0, 0.0,
            0.0, 0.0, -1.0)
        assert f.transform.to_gdal() == (1.0, 1.0, 0.0, 0.0, 0.0, -1.0)
        assert f.crs == {'init': 'epsg:4326'}


def test_update_spatial_epsg(data):
    tiffname = str(data.join('RGB.byte.tif'))
    with rasterio.open(tiffname, 'r+') as f:
        f.transform = affine.Affine.from_gdal(1.0, 1.0, 0.0, 0.0, 0.0, -1.0)
        f.crs = 'EPSG:4326'
    with rasterio.open(tiffname) as f:
        assert f.transform == affine.Affine.from_gdal(
            1.0, 1.0, 0.0,
            0.0, 0.0, -1.0)
        assert f.transform.to_gdal() == (1.0, 1.0, 0.0, 0.0, 0.0, -1.0)
        assert f.crs == {'init': 'epsg:4326'}


def test_update_nodatavals(data):
    tiffname = str(data.join('RGB.byte.tif'))
    with rasterio.open(tiffname, 'r+') as f:
        f.nodata = 255
    with rasterio.open(tiffname) as f:
        assert f.nodatavals == (255, 255, 255)


def test_update_nodatavals_error(data):
    """GDAL doesn't support un-setting nodata values."""
    tiffname = str(data.join('RGB.byte.tif'))
    with rasterio.open(tiffname, 'r+') as f:
        try:
            f.nodata = None
        except TypeError:
            pass


def test_update_mask_true(data):
    """Provide an option to set a uniformly valid mask."""
    tiffname = str(data.join('RGB.byte.tif'))
    with rasterio.open(tiffname, 'r+') as f:
        f.write_mask(True)
    with rasterio.open(tiffname) as f:
        assert f.read_masks().all()


def test_update_mask_false(data):
    """Provide an option to set a uniformly invalid mask."""
    tiffname = str(data.join('RGB.byte.tif'))
    with rasterio.open(tiffname, 'r+') as f:
        f.write_mask(False)
    with rasterio.open(tiffname) as f:
        assert not f.read_masks().any()

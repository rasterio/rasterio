"""Tests of r+ and w+ modes"""

import numpy as np
import pytest

import rasterio
from rasterio.errors import UnsupportedOperation
from rasterio.profiles import DefaultGTiffProfile


def test_read_wplus_mode(tmpdir):
    """A dataset opened in 'w+' mode can be read"""
    path = tmpdir.join('test.tif')
    profile = DefaultGTiffProfile(count=1, width=300, height=300)

    with rasterio.open(str(path), "w+", **profile) as dst:

        dst.write(255 * np.ones((1, 300, 300), dtype='uint8'))

        assert (dst.read() == 255).all()

        dst.write(3 * np.ones((1, 300, 300), dtype='uint8'))

        assert (dst.read() == 3).all()


def test_read_w_mode_warning(tmpdir):
    """Get an UnsupportedOperation exception reading from dataset opened in "w" mode"""
    path = tmpdir.join('test.tif')
    profile = DefaultGTiffProfile(count=1, width=300, height=300)

    with rasterio.open(str(path), "w", **profile) as dst:

        dst.write(255 * np.ones((1, 300, 300), dtype='uint8'))

        with pytest.raises(UnsupportedOperation):
            assert (dst.read() == 255).all()


with rasterio.Env() as env:
    HAVE_GPKG = "GPKG" in env.drivers().keys()

import os


@pytest.mark.skipif(not HAVE_GPKG, reason="GDAL not compiled with GPKG driver.")
@pytest.mark.parametrize("tiffs", [["RGB.byte.tif", "RGB.byte.tif"]])
def test_write_multilayer_geopackage(tmp_path, data_dir, tiffs):
    """ Validate if you can create multilayer."""
    gpkg = tmp_path.joinpath("test.gpkg")
    tables = ["{}({})".format(tiff, idx) for idx, tiff in enumerate(tiffs, 1)]

    for tiff, table in zip(tiffs, tables):

        with rasterio.open(os.path.join(data_dir, tiff)) as src:
            profile = src.meta
            profile["driver"] = "GPKG"
            profile["RASTER_TABLE"] = table
            profile["APPEND_SUBDATASET"] = True
            profile["TILE_FORMAT"] = "TIFF"

            with rasterio.open(gpkg, "w", **profile) as dst:
                dst.write(src.read())

    with rasterio.open(gpkg) as dst:
        assert len(dst.subdatasets) == 2

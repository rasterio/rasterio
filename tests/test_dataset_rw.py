"""Tests of r+ and w+ modes"""
import os

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
    HAVE_GPKG = 'GPKG' in env.drivers().keys()

@pytest.mark.skipif(not HAVE_GPKG,
                    reason="GDAL not compiled with GPKG driver.")
def test_write_multilayer_geopackage(tmpdir, data_dir):
    """ Validate if you can create multilayer """
    gpkg = str(tmpdir.join('test.gpkg'))
    files = ['KKa.tif', 'PGetr.tif', 'PMais.tif', 'PZR.tif','PZwifr.tif']
    for file in files:
        with rasterio.open(os.path.join(data_dir, file)) as src:
            meta = src.meta
            meta['driver'] = 'GPKG'
            meta['RASTER_TABLE'] = file
            meta['APPEND_SUBDATASET'] = 'YES'
            meta['TILE_FORMAT'] = 'TIFF'
            meta['dtype']='float32'
            with rasterio.open(str(gpkg), 'w', **meta) as dst:
                dst.write(np.float32(src.read()))

    for file in files:
        with rasterio.open(os.path.join(data_dir, file)) as src:
            with rasterio.open(str(gpkg), TABLE=file) as dst:
                assert  np.allclose(src.read(), dst.read(), equal_nan=True)


import logging
import subprocess
import sys

import affine
import numpy

import rasterio
from rasterio.warp import reproject, RESAMPLING

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_reproject():
    """Ndarry to ndarray"""
    with rasterio.drivers():
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
            source = src.read_band(1)
        dst_transform = affine.Affine.from_gdal(-8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0)
        dst_crs = dict(
                    proj='merc',
                    a=6378137,
                    b=6378137,
                    lat_ts=0.0,
                    lon_0=0.0,
                    x_0=0.0,
                    y_0=0,
                    k=1.0,
                    units='m',
                    nadgrids='@null',
                    wktext=True,
                    no_defs=True)
        destin = numpy.empty(src.shape, dtype=numpy.uint8)
        reproject(
            source, 
            destin,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform, 
            dst_crs=dst_crs,
            resampling=RESAMPLING.nearest )
    assert destin.any()
    try:
        import matplotlib.pyplot as plt
        plt.imshow(destin)
        plt.gray()
        plt.savefig('test_reproject.png')
    except:
        pass

def test_warp_from_file():
    """File to ndarray"""
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        dst_transform = affine.Affine.from_gdal(-8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0)
        dst_crs = dict(
                    proj='merc',
                    a=6378137,
                    b=6378137,
                    lat_ts=0.0,
                    lon_0=0.0,
                    x_0=0.0,
                    y_0=0,
                    k=1.0,
                    units='m',
                    nadgrids='@null',
                    wktext=True,
                    no_defs=True)
        destin = numpy.empty(src.shape, dtype=numpy.uint8)
        reproject(
            rasterio.band(src, 1), 
            destin, 
            dst_transform=dst_transform, 
            dst_crs=dst_crs)
    assert destin.any()
    try:
        import matplotlib.pyplot as plt
        plt.imshow(destin)
        plt.gray()
        plt.savefig('test_warp_from_filereproject.png')
    except:
        pass

def test_warp_from_to_file(tmpdir):
    """File to file"""
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        dst_transform = affine.Affine.from_gdal(-8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0)
        dst_crs = dict(
                    proj='merc',
                    a=6378137,
                    b=6378137,
                    lat_ts=0.0,
                    lon_0=0.0,
                    x_0=0.0,
                    y_0=0,
                    k=1.0,
                    units='m',
                    nadgrids='@null',
                    wktext=True,
                    no_defs=True)
        kwargs = src.meta.copy()
        kwargs.update(
            transform=dst_transform,
            crs=dst_crs)
        with rasterio.open(tiffname, 'w', **kwargs) as dst:
            for i in (1, 2, 3):
                reproject(rasterio.band(src, i), rasterio.band(dst, i))
    # subprocess.call(['open', tiffname])

def test_warp_from_to_file_multi(tmpdir):
    """File to file"""
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        dst_transform = affine.Affine.from_gdal(-8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0)
        dst_crs = dict(
                    proj='merc',
                    a=6378137,
                    b=6378137,
                    lat_ts=0.0,
                    lon_0=0.0,
                    x_0=0.0,
                    y_0=0,
                    k=1.0,
                    units='m',
                    nadgrids='@null',
                    wktext=True,
                    no_defs=True)
        kwargs = src.meta.copy()
        kwargs.update(
            transform=dst_transform,
            crs=dst_crs)
        with rasterio.open(tiffname, 'w', **kwargs) as dst:
            for i in (1, 2, 3):
                reproject(
                    rasterio.band(src, i), 
                    rasterio.band(dst, i),
                    num_threads=2)
    # subprocess.call(['open', tiffname])



import logging
import subprocess
import sys

import matplotlib.pyplot as plt
import numpy

import rasterio
from rasterio import _warp

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_reproject():
    """Ndarry to ndarray"""
    with rasterio.drivers():
        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
            source = src.read_band(1)
        dst_transform = [-8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0]
        dst_crs = {'init': 'EPSG:3857'}
        destin = numpy.empty(src.shape, dtype=numpy.uint8)
        _warp.reproject(
                    source, 
                    destin,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform, 
                    dst_crs=dst_crs)
    plt.imshow(destin)
    plt.gray()
    plt.savefig('test_reproject.png')
    assert destin.any()

def test_warp_from_file():
    """File to ndarray"""
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        dst_transform = [-8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0]
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
        _warp.reproject(
                    rasterio.band(src, 1), 
                    destin, 
                    dst_transform=dst_transform, 
                    dst_crs=dst_crs)
    
    plt.imshow(destin)
    plt.gray()
    plt.savefig('test_warp_from_file.png')
    assert destin.any()

def test_warp_from_to_file(tmpdir):
    """File to file"""
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        dst_transform = [-8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0]
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
                _warp.reproject(rasterio.band(src, i), rasterio.band(dst, i))
    subprocess.call(['open', tiffname])


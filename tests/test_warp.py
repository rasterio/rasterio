
import logging
import subprocess
import sys

import affine
import numpy

import rasterio
from rasterio.warp import reproject, RESAMPLING, transform_geom, transform


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_transform():
    """2D and 3D"""
    WGS84_crs = {'init': 'EPSG:4326'}
    WGS84_points = ([12.492269], [41.890169], [48.])
    ECEF_crs = {'init': 'EPSG:4978'}
    ECEF_points = ([4642610.], [1028584.], [4236562.])
    ECEF_result = transform(WGS84_crs, ECEF_crs, *WGS84_points)
    assert numpy.allclose(numpy.array(ECEF_result), numpy.array(ECEF_points))

    UTM33_crs = {'init': 'EPSG:32633'}
    UTM33_points = ([291952], [4640623])
    UTM33_result = transform(WGS84_crs, UTM33_crs, *WGS84_points[:2])
    assert numpy.allclose(numpy.array(UTM33_result), numpy.array(UTM33_points))


def test_reproject():
    """Ndarry to ndarray"""
    with rasterio.drivers():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            source = src.read_band(1)
        dst_transform = affine.Affine.from_gdal(
            -8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0)

        # Test using dictionary style CRS
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
        out1 = numpy.empty(src.shape, dtype=numpy.uint8)
        reproject(
            source,
            out1,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=RESAMPLING.nearest)
        assert out1.any()

        # Test using EPSG code
        dst_crs = {'init': 'EPSG:3857'}
        out2 = numpy.empty(src.shape, dtype=numpy.uint8)
        reproject(
            source,
            out2,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=RESAMPLING.nearest)
        assert out2.any()

        # Both results should be identical because projection parameters are equivalent
        assert numpy.array_equal(out1, out2)

        # Test using EPSG code not appropriate for the transform, should return blank image
        dst_crs = {'init': 'EPSG:32619'}
        out = numpy.empty(src.shape, dtype=numpy.uint8)
        reproject(
            source,
            out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=RESAMPLING.nearest)
        assert not out.any()


def test_reproject_multi():
    """Ndarry to ndarray"""
    with rasterio.drivers():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            source = src.read()
        dst_transform = affine.Affine.from_gdal(
            -8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0)
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
        destin = numpy.empty(source.shape, dtype=numpy.uint8)
        reproject(
            source,
            destin,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=RESAMPLING.nearest)
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
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        dst_transform = affine.Affine.from_gdal(
            -8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0)
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
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        dst_transform = affine.Affine.from_gdal(
            -8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0)
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
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        dst_transform = affine.Affine.from_gdal(
            -8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0)
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


def test_transform_geom():
    geom = {
        'type': 'Polygon',
        'coordinates': (
            ((798842.3090855901, 6569056.500655151),
                (756688.2826828464, 6412397.888771972),
                (755571.0617232556, 6408461.009397383),
                (677605.2284582685, 6425600.39266733),
                (677605.2284582683, 6425600.392667332),
                (670873.3791649605, 6427248.603432341),
                (664882.1106069803, 6407585.48425362),
                (663675.8662823177, 6403676.990080649),
                (485120.71963574126, 6449787.167760638),
                (485065.55660851026, 6449802.826920689),
                (485957.03982722526, 6452708.625101285),
                (487541.24541826674, 6457883.292107048),
                (531008.5797472061, 6605816.560367976),
                (530943.7197027118, 6605834.9333479265),
                (531888.5010308184, 6608940.750411527),
                (533299.5981959199, 6613962.642851984),
                (533403.6388841148, 6613933.172096095),
                (576345.6064638699, 6761983.708069147),
                (577649.6721159086, 6766698.137844516),
                (578600.3589008929, 6770143.99782289),
                (578679.4732294685, 6770121.638265098),
                (655836.640492081, 6749376.357102599),
                (659913.0791150068, 6764770.1314677475),
                (661105.8478791204, 6769515.168134831),
                (661929.4670843681, 6772800.8565198565),
                (661929.4670843673, 6772800.856519875),
                (661975.1582566603, 6772983.354777632),
                (662054.7979028501, 6772962.86384242),
                (841909.6014891531, 6731793.200435557),
                (840726.455490463, 6727039.8672589315),
                (798842.3090855901, 6569056.500655151)),
            )
    }

    result = transform_geom('EPSG:3373', 'EPSG:4326', geom)
    assert result['type'] == 'Polygon'
    assert len(result['coordinates']) == 1

    result = transform_geom(
        'EPSG:3373', 'EPSG:4326', geom, antimeridian_cutting=True)
    assert result['type'] == 'MultiPolygon'
    assert len(result['coordinates']) == 2

    result = transform_geom(
        'EPSG:3373', 
        'EPSG:4326', 
        geom, 
        antimeridian_cutting=True, 
        antimeridian_offset=0)
    assert result['type'] == 'MultiPolygon'
    assert len(result['coordinates']) == 2

    result = transform_geom('EPSG:3373', 'EPSG:4326',  geom,  precision=1)
    assert int(result['coordinates'][0][0][0] * 10) == -1778

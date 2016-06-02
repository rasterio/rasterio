
import logging
import sys
import pytest
from affine import Affine
import numpy as np

import rasterio
from rasterio.enums import Resampling
from rasterio.env import Env
from rasterio.warp import (
    reproject, transform_geom, transform, transform_bounds,
    calculate_default_transform)


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


DST_TRANSFORM = Affine.from_gdal(-8789636.708, 300.0, 0.0, 2943560.235, 0.0, -300.0)


class ReprojectParams(object):
    """ Class to assist testing reprojection by encapsulating parameters """
    def __init__(self, left, bottom, right, top, width, height, src_crs,
                 dst_crs):
        self.width = width
        self.height = height
        src_res = float(right - left) / float(width)
        self.src_transform = Affine(src_res, 0, left, 0, -src_res, top)
        self.src_crs = src_crs
        self.dst_crs = dst_crs

        with Env():
            dt, dw, dh = calculate_default_transform(
                src_crs, dst_crs, width, height, left, bottom, right, top)
            self.dst_transform = dt
            self.dst_width = dw
            self.dst_height = dh


def default_reproject_params():
    return ReprojectParams(
        left=-120,
        bottom=30,
        right=-80,
        top=70,
        width=80,
        height=80,
        src_crs={'init': 'EPSG:4326'},
        dst_crs={'init': 'EPSG:32610'})


def test_transform():
    """2D and 3D"""
    WGS84_crs = {'init': 'EPSG:4326'}
    WGS84_points = ([12.492269], [41.890169], [48.])
    ECEF_crs = {'init': 'EPSG:4978'}
    ECEF_points = ([4642610.], [1028584.], [4236562.])
    ECEF_result = transform(WGS84_crs, ECEF_crs, *WGS84_points)
    assert np.allclose(np.array(ECEF_result), np.array(ECEF_points))

    UTM33_crs = {'init': 'EPSG:32633'}
    UTM33_points = ([291952], [4640623])
    UTM33_result = transform(WGS84_crs, UTM33_crs, *WGS84_points[:2])
    assert np.allclose(np.array(UTM33_result), np.array(UTM33_points))


def test_transform_bounds():
    with Env():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            l, b, r, t = src.bounds
            assert np.allclose(
                transform_bounds(src.crs, {'init': 'EPSG:4326'}, l, b, r, t),
                (
                    -78.95864996545055, 23.564991210854686,
                    -76.57492370013823, 25.550873767433984
                )
            )


def test_transform_bounds_densify():
    # This transform is non-linear along the edges, so densification produces
    # a different result than otherwise
    src_crs = {'init': 'EPSG:4326'}
    dst_crs = {'init': 'EPSG:32610'}
    assert np.allclose(
        transform_bounds(
            src_crs,
            dst_crs,
            -120, 40, -80, 64,
            densify_pts=0
        ),
        (
            646695.227266598, 4432069.056898901,
            4201818.984205882, 7807592.187464975
        )
    )

    assert np.allclose(
        transform_bounds(
            src_crs,
            dst_crs,
            -120, 40, -80, 64,
            densify_pts=100
        ),
        (
            646695.2272665979, 4432069.056898901,
            4201818.984205882, 7807592.187464977
        )
    )


def test_transform_bounds_no_change():
    """ Make sure that going from and to the same crs causes no change """
    with Env():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            l, b, r, t = src.bounds
            assert np.allclose(
                transform_bounds(src.crs, src.crs, l, b, r, t),
                src.bounds
            )


def test_transform_bounds_densify_out_of_bounds():
    with pytest.raises(ValueError):
        transform_bounds(
            {'init': 'EPSG:4326'},
            {'init': 'EPSG:32610'},
            -120, 40, -80, 64,
            densify_pts=-10
        )


def test_calculate_default_transform():
    target_transform = Affine(
        0.0028535715391804096, 0.0, -78.95864996545055,
        0.0, -0.0028535715391804096, 25.550873767433984)

    with Env():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            wgs84_crs = {'init': 'EPSG:4326'}
            dst_transform, width, height = calculate_default_transform(
                src.crs, wgs84_crs, src.width, src.height, *src.bounds)

            assert dst_transform.almost_equals(target_transform)
            assert width == 835
            assert height == 696


def test_calculate_default_transform_single_resolution():
    with Env():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            target_resolution = 0.1
            target_transform = Affine(
                target_resolution, 0.0, -78.95864996545055,
                0.0, -target_resolution, 25.550873767433984
            )
            dst_transform, width, height = calculate_default_transform(
                src.crs, {'init': 'EPSG:4326'}, src.width, src.height,
                *src.bounds, resolution=target_resolution
            )

            assert dst_transform.almost_equals(target_transform)
            assert width == 24
            assert height == 20


def test_calculate_default_transform_multiple_resolutions():
    with Env():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            target_resolution = (0.2, 0.1)
            target_transform = Affine(
                target_resolution[0], 0.0, -78.95864996545055,
                0.0, -target_resolution[1], 25.550873767433984
            )

            dst_transform, width, height = calculate_default_transform(
                src.crs, {'init': 'EPSG:4326'}, src.width, src.height,
                *src.bounds, resolution=target_resolution
            )

            assert dst_transform.almost_equals(target_transform)
            assert width == 12
            assert height == 20


def test_reproject_ndarray():
    with Env():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            source = src.read(1)

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
        out = np.empty(src.shape, dtype=np.uint8)
        reproject(
            source,
            out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=DST_TRANSFORM,
            dst_crs=dst_crs,
            resampling=Resampling.nearest)
        assert (out > 0).sum() == 438146


def test_reproject_epsg():
    with Env():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            source = src.read(1)

        dst_crs = {'init': 'EPSG:3857'}
        out = np.empty(src.shape, dtype=np.uint8)
        reproject(
            source,
            out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=DST_TRANSFORM,
            dst_crs=dst_crs,
            resampling=Resampling.nearest)
        assert (out > 0).sum() == 438146


def test_reproject_out_of_bounds():
    # using EPSG code not appropriate for the transform should return blank image
    with Env():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            source = src.read(1)

        dst_crs = {'init': 'EPSG:32619'}
        out = np.empty(src.shape, dtype=np.uint8)
        reproject(
            source,
            out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=DST_TRANSFORM,
            dst_crs=dst_crs,
            resampling=Resampling.nearest)
        assert not out.any()


def test_reproject_nodata():
    params = default_reproject_params()
    nodata = 215

    with Env():
        source = np.ones((params.width, params.height), dtype=np.uint8)
        out = np.zeros((params.dst_width, params.dst_height),
                          dtype=source.dtype)
        out.fill(120)  # Fill with arbitrary value

        reproject(
            source,
            out,
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            src_nodata=nodata,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
            dst_nodata=nodata
        )

        assert (out == 1).sum() == 6215
        assert (out == nodata).sum() == (params.dst_width *
                                         params.dst_height - 6215)


def test_reproject_nodata_nan():
    params = default_reproject_params()

    with Env():
        source = np.ones((params.width, params.height), dtype=np.float32)
        out = np.zeros((params.dst_width, params.dst_height),
                          dtype=source.dtype)
        out.fill(120)  # Fill with arbitrary value

        reproject(
            source,
            out,
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            src_nodata=np.nan,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
            dst_nodata=np.nan
        )

        assert (out == 1).sum() == 6215
        assert np.isnan(out).sum() == (params.dst_width *
                                          params.dst_height - 6215)


def test_reproject_dst_nodata_default():
    """
    If nodata is not provided, destination will be filled with 0
    instead of nodata
    """

    params = default_reproject_params()

    with Env():
        source = np.ones((params.width, params.height), dtype=np.uint8)
        out = np.zeros((params.dst_width, params.dst_height),
                          dtype=source.dtype)
        out.fill(120)  # Fill with arbitrary value

        reproject(
            source,
            out,
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs
        )

        assert (out == 1).sum() == 6215
        assert (out == 0).sum() == (params.dst_width *
                                    params.dst_height - 6215)


def test_reproject_invalid_dst_nodata():
    """ dst_nodata must be in value range of data type """
    params = default_reproject_params()

    with Env():
        source = np.ones((params.width, params.height), dtype=np.uint8)
        out = source.copy()

        with pytest.raises(ValueError):
            reproject(
                source,
                out,
                src_transform=params.src_transform,
                src_crs=params.src_crs,
                src_nodata=0,
                dst_transform=params.dst_transform,
                dst_crs=params.dst_crs,
                dst_nodata=999999999
            )


def test_reproject_missing_src_nodata():
    """ src_nodata is required if dst_nodata is not None """
    params = default_reproject_params()

    with Env():
        source = np.ones((params.width, params.height), dtype=np.uint8)
        out = source.copy()

        with pytest.raises(ValueError):
            reproject(
                source,
                out,
                src_transform=params.src_transform,
                src_crs=params.src_crs,
                dst_transform=params.dst_transform,
                dst_crs=params.dst_crs,
                dst_nodata=215
            )


def test_reproject_invalid_src_nodata():
    """ src_nodata must be in range for data type """
    params = default_reproject_params()

    with Env():
        source = np.ones((params.width, params.height), dtype=np.uint8)
        out = source.copy()

        with pytest.raises(ValueError):
            reproject(
                source,
                out,
                src_transform=params.src_transform,
                src_crs=params.src_crs,
                src_nodata=999999999,
                dst_transform=params.dst_transform,
                dst_crs=params.dst_crs,
                dst_nodata=215
            )


def test_reproject_multi():
    """Ndarry to ndarray"""
    with Env():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            source = src.read()
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
        destin = np.empty(source.shape, dtype=np.uint8)
        reproject(
            source,
            destin,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=DST_TRANSFORM,
            dst_crs=dst_crs,
            resampling=Resampling.nearest)
    assert destin.any()


def test_warp_from_file():
    """File to ndarray"""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
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
        destin = np.empty(src.shape, dtype=np.uint8)
        reproject(
            rasterio.band(src, 1),
            destin,
            dst_transform=DST_TRANSFORM,
            dst_crs=dst_crs)
    assert destin.any()


def test_warp_from_to_file(tmpdir):
    """File to file"""
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open('tests/data/RGB.byte.tif') as src:
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
            transform=DST_TRANSFORM,
            crs=dst_crs)
        with rasterio.open(tiffname, 'w', **kwargs) as dst:
            for i in (1, 2, 3):
                reproject(rasterio.band(src, i), rasterio.band(dst, i))


def test_warp_from_to_file_multi(tmpdir):
    """File to file"""
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open('tests/data/RGB.byte.tif') as src:
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
            transform=DST_TRANSFORM,
            crs=dst_crs)
        with rasterio.open(tiffname, 'w', **kwargs) as dst:
            for i in (1, 2, 3):
                reproject(
                    rasterio.band(src, i),
                    rasterio.band(dst, i),
                    num_threads=2)


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
                (798842.3090855901, 6569056.500655151)),)}

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

    result = transform_geom('EPSG:3373', 'EPSG:4326', geom, precision=1)
    assert int(result['coordinates'][0][0][0] * 10) == -1778


def test_reproject_unsupported_resampling():
    """Values not in enums.Resampling are not supported."""
    with Env():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            source = src.read(1)

        dst_crs = {'init': 'EPSG:32619'}
        out = np.empty(src.shape, dtype=np.uint8)
        with pytest.raises(ValueError):
            reproject(
                source,
                out,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=DST_TRANSFORM,
                dst_crs=dst_crs,
                resampling=99)


def test_reproject_unsupported_resampling_guass():
    """Resampling.gauss is unsupported."""
    with Env():
        with rasterio.open('tests/data/RGB.byte.tif') as src:
            source = src.read(1)

        dst_crs = {'init': 'EPSG:32619'}
        out = np.empty(src.shape, dtype=np.uint8)
        with pytest.raises(ValueError):
            reproject(
                source,
                out,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=DST_TRANSFORM,
                dst_crs=dst_crs,
                resampling=Resampling.gauss)


def test_reproject_crs_none():
    """Reproject with crs is None should not cause segfault"""
    src = np.random.random(25).reshape((1, 5, 5))
    srcaff = Affine(1.1, 0.0, 0.0, 0.0, 1.1, 0.0)
    srccrs = None
    dst = np.empty(shape=(1, 11, 11))
    dstaff = Affine(0.5, 0.0, 0.0, 0.0, 0.5, 0.0)
    dstcrs = None

    with Env():
        reproject(
            src, dst,
            src_transform=srcaff,
            src_crs=srccrs,
            dst_transform=dstaff,
            dst_crs=dstcrs,
            resampling=Resampling.nearest)

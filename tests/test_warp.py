
import logging
import sys

import pytest
from affine import Affine
import numpy as np
from packaging.version import parse

import rasterio
from rasterio.control import GroundControlPoint
from rasterio.enums import Resampling
from rasterio.errors import CRSError
from rasterio.warp import (
    reproject, transform_geom, transform, transform_bounds,
    calculate_default_transform)
from rasterio import windows
from rasterio.plot import show

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


DST_TRANSFORM = Affine(300.0, 0.0, -8789636.708,
                       0.0, -300.0, 2943560.235)


def flatten_coords(coordinates):
    """Yield a flat sequence of coordinates to help testing"""
    for elem in coordinates:
        if isinstance(elem, (float, int)):
            yield elem
        else:
            for x in flatten_coords(elem):
                yield x


def supported_resampling(method):
    if method == Resampling.gauss:
        return False
    gdal110plus_only = (
        Resampling.mode, Resampling.average)
    gdal2plus_only = (
        Resampling.max, Resampling.min, Resampling.med,
        Resampling.q1, Resampling.q3)
    version = parse(rasterio.__gdal_version__)
    if version < parse('1.10'):
        return method not in gdal2plus_only and method not in gdal110plus_only
    if version < parse('2.0'):
        return method not in gdal2plus_only
    return True


reproj_expected = (
    ({'CHECK_WITH_INVERT_PROJ': False}, 7608),
    ({'CHECK_WITH_INVERT_PROJ': True}, 2216))


class ReprojectParams(object):
    """Class to assist testing reprojection by encapsulating parameters."""

    def __init__(self, left, bottom, right, top, width, height, src_crs,
                 dst_crs):
        self.width = width
        self.height = height
        src_res = float(right - left) / float(width)
        self.src_transform = Affine(src_res, 0, left, 0, -src_res, top)
        self.src_crs = src_crs
        self.dst_crs = dst_crs

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
        dst_crs={'init': 'EPSG:2163'})


def uninvertable_reproject_params():
    return ReprojectParams(
        left=-120,
        bottom=30,
        right=-80,
        top=70,
        width=80,
        height=80,
        src_crs={'init': 'EPSG:4326'},
        dst_crs={'init': 'EPSG:26836'})


def test_transform():
    """2D and 3D."""
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
    dst_crs = {'init': 'EPSG:2163'}
    assert np.allclose(
        transform_bounds(
            src_crs,
            dst_crs,
            -120, 40, -80, 64,
            densify_pts=0),
        (-1684649.41338, -350356.81377, 1684649.41338, 2234551.18559))

    assert np.allclose(
        transform_bounds(
            src_crs,
            dst_crs,
            -120, 40, -80, 64,
            densify_pts=100),
        (-1684649.41338, -555777.79210, 1684649.41338, 2234551.18559))


def test_transform_bounds_no_change():
    """Make sure that going from and to the same crs causes no change."""
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

    with rasterio.open('tests/data/RGB.byte.tif') as src:
        wgs84_crs = {'init': 'EPSG:4326'}
        dst_transform, width, height = calculate_default_transform(
            src.crs, wgs84_crs, src.width, src.height, *src.bounds)

        assert dst_transform.almost_equals(target_transform)
        assert width == 835
        assert height == 696


def test_calculate_default_transform_single_resolution():
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
    assert (out > 0).sum() == 438113


def test_reproject_view():
    """Source views are reprojected properly"""
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        source = src.read(1)

    window = windows.Window(100, 100, 500, 500)
    # window = windows.get_data_window(source)
    reduced_array = source[window.toslices()]
    reduced_transform = windows.transform(window, src.transform)

    # Assert that we're working with a view.
    assert reduced_array.base is source

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
        reduced_array,
        out,
        src_transform=reduced_transform,
        src_crs=src.crs,
        dst_transform=DST_TRANSFORM,
        dst_crs=dst_crs,
        resampling=Resampling.nearest)

    assert (out > 0).sum() == 299199


def test_reproject_epsg():
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
    assert (out > 0).sum() == 438113


def test_reproject_out_of_bounds():
    """Using EPSG code is not appropriate for the transform.

    Should return blank image.
    """
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        source = src.read(1)

    dst_crs = {'init': 'EPSG:32619'}
    out = np.zeros(src.shape, dtype=np.uint8)
    reproject(
        source,
        out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=DST_TRANSFORM,
        dst_crs=dst_crs,
        resampling=Resampling.nearest)
    assert not out.any()


@pytest.mark.parametrize("options, expected", reproj_expected)
def test_reproject_nodata(options, expected):
    nodata = 215

    with rasterio.Env(**options):
        params = uninvertable_reproject_params()
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

        assert (out == 1).sum() == expected
        assert (out == nodata).sum() == (params.dst_width *
                                         params.dst_height - expected)


@pytest.mark.parametrize("options, expected", reproj_expected)
def test_reproject_nodata_nan(options, expected):

    with rasterio.Env(**options):
        params = uninvertable_reproject_params()
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

        assert (out == 1).sum() == expected
        assert np.isnan(out).sum() == (params.dst_width *
                                       params.dst_height - expected)


@pytest.mark.parametrize("options, expected", reproj_expected)
def test_reproject_dst_nodata_default(options, expected):
    """If nodata is not provided, destination will be filled with 0."""

    with rasterio.Env(**options):
        params = uninvertable_reproject_params()
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

        assert (out == 1).sum() == expected
        assert (out == 0).sum() == (params.dst_width *
                                    params.dst_height - expected)


def test_reproject_invalid_dst_nodata():
    """dst_nodata must be in value range of data type."""
    params = default_reproject_params()

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
    """src_nodata is required if dst_nodata is not None."""
    params = default_reproject_params()

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
    """src_nodata must be in range for data type."""
    params = default_reproject_params()

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


def test_reproject_init_nodata_tofile(tmpdir):
    """Test that nodata is being initialized."""
    params = default_reproject_params()

    tiffname = str(tmpdir.join('foo.tif'))

    source1 = np.zeros((params.width, params.height), dtype=np.uint8)
    source2 = source1.copy()

    # fill both sources w/ arbitrary values
    rows, cols = source1.shape
    source1[:rows // 2, :cols // 2] = 200
    source2[rows // 2:, cols // 2:] = 100

    kwargs = {
        'count': 1,
        'width': params.width,
        'height': params.height,
        'dtype': np.uint8,
        'driver': 'GTiff',
        'crs': params.dst_crs,
        'transform': params.dst_transform
    }

    with rasterio.open(tiffname, 'w', **kwargs) as dst:
        reproject(
            source1,
            rasterio.band(dst, 1),
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            src_nodata=0.0,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
            dst_nodata=0.0
        )

        # 200s should be overwritten by 100s
        reproject(
            source2,
            rasterio.band(dst, 1),
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            src_nodata=0.0,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
            dst_nodata=0.0
        )

    with rasterio.open(tiffname) as src:
        assert src.read().max() == 100


def test_reproject_no_init_nodata_tofile(tmpdir):
    """Test that nodata is not being initialized."""
    params = default_reproject_params()

    tiffname = str(tmpdir.join('foo.tif'))

    source1 = np.zeros((params.width, params.height), dtype=np.uint8)
    source2 = source1.copy()

    # fill both sources w/ arbitrary values
    rows, cols = source1.shape
    source1[:rows // 2, :cols // 2] = 200
    source2[rows // 2:, cols // 2:] = 100

    kwargs = {
        'count': 1,
        'width': params.width,
        'height': params.height,
        'dtype': np.uint8,
        'driver': 'GTiff',
        'crs': params.dst_crs,
        'transform': params.dst_transform
    }

    with rasterio.open(tiffname, 'w', **kwargs) as dst:
        reproject(
            source1,
            rasterio.band(dst, 1),
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            src_nodata=0.0,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
            dst_nodata=0.0
        )

        reproject(
            source2,
            rasterio.band(dst, 1),
            src_transform=params.src_transform,
            src_crs=params.src_crs,
            src_nodata=0.0,
            dst_transform=params.dst_transform,
            dst_crs=params.dst_crs,
            dst_nodata=0.0,
            init_dest_nodata=False
        )

    # 200s should not be overwritten by 100s
    with rasterio.open(tiffname) as src:
        assert src.read().max() == 200


def test_reproject_no_init_nodata_toarray():
    """Test that nodata is being initialized."""
    params = default_reproject_params()

    source1 = np.zeros((params.width, params.height))
    source2 = source1.copy()
    out = source1.copy()

    # fill both sources w/ arbitrary values
    rows, cols = source1.shape
    source1[:rows // 2, :cols // 2] = 200
    source2[rows // 2:, cols // 2:] = 100

    reproject(
        source1,
        out,
        src_transform=params.src_transform,
        src_crs=params.src_crs,
        src_nodata=0.0,
        dst_transform=params.dst_transform,
        dst_crs=params.dst_crs,
        dst_nodata=0.0
    )

    assert out.max() == 200
    assert out.min() == 0

    reproject(
        source2,
        out,
        src_transform=params.src_transform,
        src_crs=params.src_crs,
        src_nodata=0.0,
        dst_transform=params.dst_transform,
        dst_crs=params.dst_crs,
        dst_nodata=0.0,
        init_dest_nodata=False
    )

    # 200s should NOT be overwritten by 100s
    assert out.max() == 200
    assert out.min() == 0


def test_reproject_multi():
    """Ndarry to ndarray."""
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
    """File to ndarray."""
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
    """File to file."""
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
    """File to file."""
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


@pytest.fixture(scope='function')
def polygon_3373():
    """An EPSG:3373 polygon."""
    return {
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


def test_transform_geom_polygon_cutting(polygon_3373):
    geom = polygon_3373
    result = transform_geom(
        'EPSG:3373', 'EPSG:4326', geom, antimeridian_cutting=True)
    assert result['type'] == 'MultiPolygon'
    assert len(result['coordinates']) == 2


def test_transform_geom_polygon_offset(polygon_3373):
    geom = polygon_3373
    result = transform_geom(
        'EPSG:3373',
        'EPSG:4326',
        geom,
        antimeridian_cutting=True,
        antimeridian_offset=0)
    assert result['type'] == 'MultiPolygon'
    assert len(result['coordinates']) == 2


def test_transform_geom_polygon_precision(polygon_3373):
    geom = polygon_3373
    result = transform_geom('EPSG:3373', 'EPSG:4326', geom, precision=1, antimeridian_cutting=True)
    assert all(round(x, 1) == x for x in flatten_coords(result['coordinates']))


def test_transform_geom_linestring_precision(polygon_3373):
    ring = polygon_3373['coordinates'][0]
    geom = {'type': 'LineString', 'coordinates': ring}
    result = transform_geom('EPSG:3373', 'EPSG:4326', geom, precision=1, antimeridian_cutting=True)
    assert all(round(x, 1) == x for x in flatten_coords(result['coordinates']))


def test_transform_geom_linestring_precision_iso(polygon_3373):
    ring = polygon_3373['coordinates'][0]
    geom = {'type': 'LineString', 'coordinates': ring}
    result = transform_geom('EPSG:3373', 'EPSG:3373', geom, precision=1)
    assert int(result['coordinates'][0][0] * 10) == 7988423


def test_transform_geom_linestring_precision_z(polygon_3373):
    ring = polygon_3373['coordinates'][0]
    x, y = zip(*ring)
    ring = zip(x, y, [0.0 for i in range(len(x))])
    geom = {'type': 'LineString', 'coordinates': ring}
    result = transform_geom('EPSG:3373', 'EPSG:3373', geom, precision=1)
    assert int(result['coordinates'][0][0] * 10) == 7988423
    assert int(result['coordinates'][0][2] * 10) == 0


def test_transform_geom_multipolygon(polygon_3373):
    geom = {
        'type': 'MultiPolygon', 'coordinates': [polygon_3373['coordinates']]}
    result = transform_geom('EPSG:3373', 'EPSG:4326', geom, precision=1)
    assert all(round(x, 1) == x for x in flatten_coords(result['coordinates']))


def test_reproject_unsupported_resampling():
    """Values not in enums. Resampling are not supported."""
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


@pytest.mark.parametrize("method", Resampling)
def test_resample_default_invert_proj(method):
    """Nearest and bilinear should produce valid results
    with the default Env
    """
    if not supported_resampling(method):
        pytest.skip()

    with rasterio.open('tests/data/world.rgb.tif') as src:
        source = src.read(1)
        profile = src.profile.copy()

    dst_crs = {'init': 'EPSG:32619'}

    # Calculate the ideal dimensions and transformation in the new crs
    dst_affine, dst_width, dst_height = calculate_default_transform(
        src.crs, dst_crs, src.width, src.height, *src.bounds)

    profile['height'] = dst_height
    profile['width'] = dst_width

    out = np.empty(shape=(dst_height, dst_width), dtype=np.uint8)

    out = np.empty(src.shape, dtype=np.uint8)
    reproject(
        source,
        out,
        src_transform=src.transform,
        src_crs=src.crs,
        dst_transform=dst_affine,
        dst_crs=dst_crs,
        resampling=method)

    assert out.mean() > 0


@pytest.mark.xfail()
@pytest.mark.parametrize("method", Resampling)
def test_resample_no_invert_proj(method):
    """Nearest and bilinear should produce valid results with
    CHECK_WITH_INVERT_PROJ = False
    """
    if not supported_resampling(method):
        pytest.skip()

    with rasterio.Env(CHECK_WITH_INVERT_PROJ=False):
        with rasterio.open('tests/data/world.rgb.tif') as src:
            source = src.read(1)
            profile = src.profile.copy()

        dst_crs = {'init': 'EPSG:32619'}

        # Calculate the ideal dimensions and transformation in the new crs
        dst_affine, dst_width, dst_height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds)

        profile['height'] = dst_height
        profile['width'] = dst_width

        out = np.empty(shape=(dst_height, dst_width), dtype=np.uint8)

        # see #614, some resamplin methods succeed but produce blank images
        out = np.empty(src.shape, dtype=np.uint8)
        reproject(
            source,
            out,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_affine,
            dst_crs=dst_crs,
            resampling=method)

        assert out.mean() > 0


def test_reproject_crs_none():
    """Reproject with crs is None should not cause segfault"""
    src = np.random.random(25).reshape((1, 5, 5))
    srcaff = Affine(1.1, 0.0, 0.0, 0.0, 1.1, 0.0)
    srccrs = None
    dst = np.empty(shape=(1, 11, 11))
    dstaff = Affine(0.5, 0.0, 0.0, 0.0, 0.5, 0.0)
    dstcrs = None

    with pytest.raises(ValueError):
        reproject(
            src, dst,
            src_transform=srcaff,
            src_crs=srccrs,
            dst_transform=dstaff,
            dst_crs=dstcrs,
            resampling=Resampling.nearest)


def test_reproject_identity():
    """Reproject with an identity matrix."""
    # note the affines are both positive e, src is identity
    src = np.random.random(25).reshape((1, 5, 5))
    srcaff = Affine(1.0, 0.0, 0.0, 0.0, 1.0, 0.0)  # Identity
    srccrs = {'init': 'epsg:3857'}

    dst = np.empty(shape=(1, 10, 10))
    dstaff = Affine(0.5, 0.0, 0.0, 0.0, 0.5, 0.0)
    dstcrs = {'init': 'epsg:3857'}

    reproject(
        src, dst,
        src_transform=srcaff,
        src_crs=srccrs,
        dst_transform=dstaff,
        dst_crs=dstcrs,
        resampling=Resampling.nearest)

    # note the affines are both positive e, dst is identity
    src = np.random.random(100).reshape((1, 10, 10))
    srcaff = Affine(0.5, 0.0, 0.0, 0.0, 0.5, 0.0)
    srccrs = {'init': 'epsg:3857'}

    dst = np.empty(shape=(1, 5, 5))
    dstaff = Affine(1.0, 0.0, 0.0, 0.0, 1.0, 0.0)  # Identity
    dstcrs = {'init': 'epsg:3857'}

    reproject(
        src, dst,
        src_transform=srcaff,
        src_crs=srccrs,
        dst_transform=dstaff,
        dst_crs=dstcrs,
        resampling=Resampling.nearest)


@pytest.fixture(scope='function')
def rgb_byte_profile():
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        return src.profile


def test_reproject_gcps_transform_exclusivity():
    """gcps and transform can't be used together."""
    with pytest.raises(ValueError):
        reproject(1, 1, gcps=[0], src_transform=[0])


def test_reproject_gcps(rgb_byte_profile):
    """Reproject using ground control points for the source"""
    source = np.ones((3, 800, 800), dtype=np.uint8) * 255
    out = np.zeros((3, rgb_byte_profile['height'], rgb_byte_profile['height']), dtype=np.uint8)
    src_gcps = [
        GroundControlPoint(row=0, col=0, x=156113, y=2818720, z=0),
        GroundControlPoint(row=0, col=800, x=338353, y=2785790, z=0),
        GroundControlPoint(row=800, col=800, x=297939, y=2618518, z=0),
        GroundControlPoint(row=800, col=0, x=115698, y=2651448, z=0)]
    reproject(
        source,
        out,
        src_crs='epsg:32618',
        gcps=src_gcps,
        dst_transform=rgb_byte_profile['transform'],
        dst_crs=rgb_byte_profile['crs'],
        resampling=Resampling.nearest)

    assert not out.all()
    assert not out[:, 0, 0].any()
    assert not out[:, 0, -1].any()
    assert not out[:, -1, -1].any()
    assert not out[:, -1, 0].any()

import os

import pytest

import rasterio
from rasterio._warp import _calculate_default_transform
from rasterio.errors import CRSError
from rasterio.transform import from_bounds
from rasterio.warp import transform_bounds


def test_identity():
    """Get the same transform and dimensions back for same crs."""
    # Tile: [53, 96, 8]
    src_crs = dst_crs = 'EPSG:3857'
    width = height = 1000
    left, bottom, right, top = (
        -11740727.544603072, 4852834.0517692715, -11584184.510675032,
        5009377.085697309)
    transform = from_bounds(left, bottom, right, top, width, height)

    with rasterio.Env():
        res_transform, res_width, res_height = _calculate_default_transform(
            src_crs, dst_crs, width, height, left, bottom, right, top)

    assert res_width == width
    assert res_height == height
    for res, exp in zip(res_transform, transform):
        assert round(res, 7) == round(exp, 7)


def test_transform_bounds():
    """CRSError is raised."""
    with rasterio.Env():
        left, bottom, right, top = (
            -11740727.544603072, 4852834.0517692715, -11584184.510675032,
            5009377.085697309)
        src_crs = 'EPSG:3857'
        dst_crs = {'proj': 'foobar'}
        with pytest.raises(CRSError):
            transform_bounds(src_crs, dst_crs, left, bottom, right, top)


def test_gdal_transform_notnull():
    with rasterio.Env():
        dt, dw, dh = _calculate_default_transform(
            src_crs={'init': 'EPSG:4326'},
            dst_crs={'init': 'EPSG:32610'},
            width=80,
            height=80,
            left=-120,
            bottom=30,
            right=-80,
            top=70)
    assert True


def test_gdal_transform_fail_dst_crs():
    with rasterio.Env():
        dt, dw, dh = _calculate_default_transform(
            {'init': 'EPSG:4326'},
            '+proj=foobar',
            width=80,
            height=80,
            left=-120,
            bottom=30,
            right=-80,
            top=70)


def test_gdal_transform_fail_src_crs():
    with rasterio.Env():
        dt, dw, dh = _calculate_default_transform(
            '+proj=foobar',
            {'init': 'EPSG:32610'},
            width=80,
            height=80,
            left=-120,
            bottom=30,
            right=-80,
            top=70)


@pytest.mark.xfail(
    os.environ.get('GDALVERSION', 'a.b.c').startswith('1.9'),
                   reason="GDAL 1.9 doesn't catch this error")
def test_gdal_transform_fail_dst_crs_xfail():
    with rasterio.Env():
        with pytest.raises(CRSError):
            dt, dw, dh = _calculate_default_transform(
                {'init': 'EPSG:4326'},
                {'proj': 'foobar'},
                width=80,
                height=80,
                left=-120,
                bottom=30,
                right=-80,
                top=70)

import os

import pytest

from rasterio._warp import _calculate_default_transform
from rasterio.control import GroundControlPoint
from rasterio.crs import CRS
from rasterio.errors import CRSError
from rasterio.transform import from_bounds
from rasterio.warp import calculate_default_transform, transform_bounds


def test_gcps_bounds_exclusivity():
    """gcps and bounds parameters are mutually exclusive"""
    with pytest.raises(ValueError):
        calculate_default_transform(
            'epsg:4326', 'epsg:3857', width=1, height=1, left=1.0, gcps=[1])


def test_resolution_dimensions_exclusivity():
    """resolution and dimensions parameters are mutually exclusive"""
    with pytest.raises(ValueError):
        calculate_default_transform(
            'epsg:4326', 'epsg:3857', width=1, height=1, gcps=[1],
            resolution=1, dst_width=1, dst_height=1)


def test_dimensions_missing_params():
    """dst_width and dst_height must be specified together"""
    with pytest.raises(ValueError):
        calculate_default_transform(
            'epsg:4326', 'epsg:3857', width=1, height=1, gcps=[1],
            resolution=1, dst_width=1, dst_height=None)

    with pytest.raises(ValueError):
        calculate_default_transform(
            'epsg:4326', 'epsg:3857', width=1, height=1, gcps=[1],
            resolution=1, dst_width=None, dst_height=1)


def test_one_of_gcps_bounds():
    """at least one of gcps or bounds parameters must be provided"""
    with pytest.raises(ValueError):
        calculate_default_transform(
            'epsg:4326', 'epsg:3857', width=1, height=1)


def test_identity():
    """Get the same transform and dimensions back for same crs."""
    # Tile: [53, 96, 8]
    src_crs = dst_crs = 'EPSG:3857'
    width = height = 1000
    left, bottom, right, top = (
        -11740727.544603072, 4852834.0517692715, -11584184.510675032,
        5009377.085697309)
    transform = from_bounds(left, bottom, right, top, width, height)

    res_transform, res_width, res_height = _calculate_default_transform(
        src_crs, dst_crs, width, height, left, bottom, right, top)

    assert res_width == width
    assert res_height == height
    for res, exp in zip(res_transform, transform):
        assert round(res, 7) == round(exp, 7)


def test_identity_gcps():
    """Define an identity transform using GCPs"""
    # Tile: [53, 96, 8]
    src_crs = dst_crs = 'EPSG:3857'
    width = height = 1000
    left, bottom, right, top = (
        -11740727.544603072, 4852834.0517692715, -11584184.510675032,
        5009377.085697309)
    # For comparison only, these are not used to calculate the transform.
    transform = from_bounds(left, bottom, right, top, width, height)

    # Define 4 ground control points at the corners of the image.
    gcps = [
        GroundControlPoint(row=0, col=0, x=left, y=top, z=0.0),
        GroundControlPoint(row=0, col=1000, x=right, y=top, z=0.0),
        GroundControlPoint(row=1000, col=1000, x=right, y=bottom, z=0.0),
        GroundControlPoint(row=1000, col=0, x=left, y=bottom, z=0.0)]

    # Compute an output transform.
    res_transform, res_width, res_height = _calculate_default_transform(
        src_crs, dst_crs, height=height, width=width, gcps=gcps)

    assert res_width == width
    assert res_height == height
    for res, exp in zip(res_transform, transform):
        assert round(res, 7) == round(exp, 7)


def test_transform_bounds():
    """CRSError is raised."""
    left, bottom, right, top = (
        -11740727.544603072, 4852834.0517692715, -11584184.510675032,
        5009377.085697309)
    src_crs = 'EPSG:3857'
    dst_crs = {'proj': 'foobar'}
    with pytest.raises(CRSError):
        transform_bounds(src_crs, dst_crs, left, bottom, right, top)


def test_gdal_transform_notnull():
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
    with pytest.raises(CRSError):
        _calculate_default_transform(
            {'init': 'EPSG:4326'},
            '+proj=foobar',
            width=80,
            height=80,
            left=-120,
            bottom=30,
            right=-80,
            top=70)


def test_gdal_transform_fail_src_crs():
    with pytest.raises(CRSError):
        _calculate_default_transform(
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


def test_gcps_calculate_transform():
    src_gcps = [
        GroundControlPoint(row=0, col=0, x=156113, y=2818720, z=0),
        GroundControlPoint(row=0, col=800, x=338353, y=2785790, z=0),
        GroundControlPoint(row=800, col=800, x=297939, y=2618518, z=0),
        GroundControlPoint(row=800, col=0, x=115698, y=2651448, z=0)]
    _, width, height = calculate_default_transform(
        'epsg:3857', 'epsg:4326', width=800, height=800, gcps=src_gcps)
    assert width == 1087
    assert height == 895


def test_transform_bounds_identity():
    """Confirm fix of #1411"""
    bounds = (12978395.906596646, 146759.09430753812, 12983287.876406897, 151651.06411778927)
    assert transform_bounds("+init=epsg:3857", "+init=epsg:3857", *bounds) == bounds


def test_issue1131():
    """Confirm that we don't run out of memory"""
    transform, w, h = calculate_default_transform(CRS.from_epsg(4326), CRS.from_epsg(3857), 455880, 454450, 13.0460235139, 42.6925552354, 13.2511695428, 42.8970561511)
    assert (w, h) == (381595, 518398)

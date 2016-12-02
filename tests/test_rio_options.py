import os.path
import uuid

import click
import pytest

from rasterio.rio.options import (
    bounds_handler, file_in_handler, like_handler, nodata_handler)


class MockContext:

    def __init__(self):
        self.obj = {}


class MockOption:

    def __init__(self, name):
        self.name = name


def test_bounds_handler_3_items():
    """fail if less than 4 numbers in the bbox"""
    ctx = MockContext()
    with pytest.raises(click.BadParameter):
        bounds_handler(ctx, 'bounds', '1.0 0.0 1.0')


def test_bounds_handler_3_items():
    """fail if there's a non-number in the bbox"""
    ctx = MockContext()
    with pytest.raises(click.BadParameter):
        bounds_handler(ctx, 'bounds', '1.0 surprise! 1.0')


def test_bounds_handler_floats():
    """handle non-JSON bbox"""
    ctx = MockContext()
    retval = bounds_handler(ctx, 'bounds', '1.0 0.0 1.0 0.0')
    assert retval == (1.0, 0.0, 1.0, 0.0)


def test_bounds_handler_floats():
    """handle non-JSON bbox with commas"""
    ctx = MockContext()
    retval = bounds_handler(ctx, 'bounds', '1.0, 0.0, 1.0 , 0.0')
    assert retval == (1.0, 0.0, 1.0, 0.0)


def test_bounds_handler_json():
    """handle JSON bbox"""
    ctx = MockContext()
    retval = bounds_handler(ctx, 'bounds', '[1.0, 0.0, 1.0, 0.0]')
    assert retval == (1.0, 0.0, 1.0, 0.0)


def test_file_in_handler_no_vfs_nonexistent():
    """file does not exist"""
    ctx = MockContext()
    with pytest.raises(click.BadParameter):
        file_in_handler(ctx, 'INPUT', '{0}.tif'.format(uuid.uuid4()))


def test_file_in_handler_no_vfs():
    """file path is expanded to abspath"""
    from rasterio.rio.options import abspath_forward_slashes
    ctx = MockContext()
    retval = file_in_handler(ctx, 'INPUT', 'tests/data/RGB.byte.tif')
    assert retval == abspath_forward_slashes('tests/data/RGB.byte.tif')


def test_file_in_handler_bad_scheme():
    """lolwut scheme is not supported"""
    ctx = MockContext()
    with pytest.raises(click.BadParameter):
        file_in_handler(ctx, 'INPUT', 'lolwut://bogus')


def test_file_in_handler_with_vfs_nonexistent():
    """archive does not exist"""
    ctx = MockContext()
    with pytest.raises(click.BadParameter):
        file_in_handler(
            ctx, 'INPUT', 'zip://{0}/files.zip!/inputs/RGB.byte.tif'.format(
                uuid.uuid4()))


def test_file_in_handler_with_vfs():
    """vfs file path path is expanded"""
    ctx = MockContext()
    retval = file_in_handler(
        ctx, 'INPUT', 'zip://tests/data/files.zip!/inputs/RGB.byte.tif')
    assert retval.endswith('tests/data/files.zip!/inputs/RGB.byte.tif')


def test_file_in_handler_with_vfs_file():
    """vfs file path path is expanded"""
    ctx = MockContext()
    retval = file_in_handler(ctx, 'INPUT', 'file://tests/data/RGB.byte.tif')
    assert retval.endswith('tests/data/RGB.byte.tif')


def test_like_dataset_callback(data):
    ctx = MockContext()
    like_handler(ctx, 'like', str(data.join('RGB.byte.tif')))
    assert ctx.obj['like']['crs'] == {'init': 'epsg:32618'}


def test_nodata_callback_err(data):
    ctx = MockContext()
    ctx.obj['like'] = {'nodata': 'lolwut'}
    with pytest.raises(click.BadParameter):
        nodata_handler(ctx, MockOption('nodata'), 'lolwut')


def test_nodata_callback_pass(data):
    """Always return None if the value is None"""
    ctx = MockContext()
    ctx.obj['like'] = {'nodata': -1}
    assert nodata_handler(ctx, MockOption('nodata'), None) is None


def test_nodata_callback_0(data):
    ctx = MockContext()
    assert nodata_handler(ctx, MockOption('nodata'), '0') == 0.0


def test_nodata_callback(data):
    ctx = MockContext()
    ctx.obj['like'] = {'nodata': -1}
    assert nodata_handler(ctx, MockOption('nodata'), 'like') == -1.0

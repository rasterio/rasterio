"""Tests for ``$ rio edit-info``."""


import json

import click
import pytest

import rasterio
from rasterio.enums import ColorInterp
from rasterio.env import GDALVersion
from rasterio.rio.edit_info import (
    all_handler, crs_handler, tags_handler, transform_handler,
    colorinterp_handler)
from rasterio.rio.main import main_group
import rasterio.shutil

from .conftest import requires_gdal21


PARAM_HANDLER = {
    'crs': crs_handler,
    'tags': tags_handler,
    'transform': transform_handler,
    'colorinterp': colorinterp_handler
}


class MockContext:

    def __init__(self):
        self.obj = {}


class MockOption:

    def __init__(self, name):
        self.name = name


def test_delete_nodata_exclusive_opts(data, runner):
    """--unset-nodata and --nodata can't be used together"""
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--unset-nodata', '--nodata', '0'])
    assert result.exit_code == 2


def test_delete_crs_exclusive_opts(data, runner):
    """--unset-crs and --crs can't be used together"""
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--unset-crs', '--crs', 'epsg:4326'])
    assert result.exit_code == 2


def test_edit_nodata_err(data, runner):
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(main_group,
                           ['edit-info', inputfile, '--nodata', '-1'])
    assert result.exit_code == 2


@requires_gdal21
def test_delete_nodata(data, runner):
    """Delete a dataset's nodata value"""
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--unset-nodata'])
    assert result.exit_code == 0


def test_edit_nodata(data, runner):
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--nodata', '255'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.nodata == 255.0


def test_edit_crs_err(data, runner):
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--crs', 'LOL:WUT'])
    assert result.exit_code == 2


def test_edit_crs_epsg(data, runner):
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--crs', 'EPSG:32618'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32618'}


def test_edit_crs_proj4(data, runner):
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--crs', '+init=epsg:32618'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32618'}


def test_edit_crs_obj(data, runner):
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group,
        ['edit-info', inputfile, '--crs', '{"init": "epsg:32618"}'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs.to_dict() == {'init': 'epsg:32618'}


def test_edit_transform_err_not_json(data, runner):
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--transform', 'LOL'])
    assert result.exit_code == 2


def test_edit_transform_err_bad_array(data, runner):
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--transform', '[1,2]'])
    assert result.exit_code == 2


def test_edit_transform_affine(data, runner):
    inputfile = str(data.join('RGB.byte.tif'))
    input_t = '[300.038, 0.0, 101985.0, 0.0, -300.042, 2826915.0]'
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--transform', input_t])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        for a, b in zip(src.transform, json.loads(input_t)):
            assert round(a, 6) == round(b, 6)


def test_edit_transform_gdal(data, runner):
    inputfile = str(data.join('RGB.byte.tif'))
    gdal_geotransform = '[101985.0, 300.038, 0.0, 2826915.0, 0.0, -300.042]'
    result = runner.invoke(main_group, [
        'edit-info', inputfile, '--transform', gdal_geotransform])
    assert result.exit_code != 0
    assert 'not recognized as an Affine array' in result.output
    assert gdal_geotransform in result.output


def test_edit_tags(data, runner):
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(main_group, [
        'edit-info', inputfile, '--tag', 'lol=1', '--tag', 'wut=2'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.tags()['lol'] == '1'
        assert src.tags()['wut'] == '2'


@requires_gdal21(reason="decription setting requires GDAL 2.1+")
def test_edit_band_description(data, runner):
    """Edit band descriptions"""
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(main_group, [
        'edit-info', inputfile, '--bidx', '3', '--description',
        'this is another test'])

    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.descriptions[2] == 'this is another test'


def test_edit_units(data, runner):
    """Edit units"""
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(main_group, [
        'edit-info', inputfile, '--bidx', '1', '--units', 'DN'],
        catch_exceptions=False)

    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.units[0] == 'DN'


def test_edit_crs_like(data, runner):
    # Set up the file to be edited.
    inputfile = str(data.join('RGB.byte.tif'))
    with rasterio.open(inputfile, 'r+') as dst:
        dst.crs = {'init': 'epsg:32617'}
        dst.nodata = 1.0

    # Double check.
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32617'}
        assert src.nodata == 1.0

    # The test.
    templatefile = 'tests/data/RGB.byte.tif'
    result = runner.invoke(
        main_group,
        ['edit-info', inputfile, '--like', templatefile, '--crs', 'like'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs.to_epsg() == 32618
        assert src.nodata == 1.0


def test_edit_nodata_like(data, runner):
    # Set up the file to be edited.
    inputfile = str(data.join('RGB.byte.tif'))
    with rasterio.open(inputfile, 'r+') as dst:
        dst.crs = {'init': 'epsg:32617'}
        dst.nodata = 1.0

    # Double check.
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32617'}
        assert src.nodata == 1.0

    # The test.
    templatefile = 'tests/data/RGB.byte.tif'
    result = runner.invoke(
        main_group,
        ['edit-info', inputfile, '--like', templatefile, '--nodata', 'like'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32617'}
        assert src.nodata == 0.0


def test_edit_all_like(data, runner):
    inputfile = str(data.join('RGB.byte.tif'))
    with rasterio.open(inputfile, 'r+') as dst:
        dst.crs = {'init': 'epsg:32617'}
        dst.nodata = 1.0

    # Double check.
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32617'}
        assert src.nodata == 1.0

    templatefile = 'tests/data/RGB.byte.tif'
    # Dropping '--all' right after 'edit-info' guards against a regression.
    # Previously specifying '--all' before '--like' would raise an exception.
    result = runner.invoke(
        main_group, ['edit-info', '--all', inputfile, '--like', templatefile])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs.to_epsg() == 32618
        assert src.nodata == 0.0


@pytest.mark.parametrize("param", PARAM_HANDLER.keys())
def test_like_handler_pass(param):
    ctx = MockContext()
    ctx.obj['like'] = {param: 'foo'}
    assert PARAM_HANDLER[param](ctx, MockOption(param), None) is None


@pytest.mark.parametrize("param", PARAM_HANDLER.keys())
def test_like_handler_get(param):
    ctx = MockContext()
    ctx.obj['like'] = {param: 'foo'}
    assert PARAM_HANDLER[param](ctx, MockOption(param), 'like') == 'foo'


@pytest.mark.parametrize("param", PARAM_HANDLER.keys())
def test_like_handler_err(param):
    ctx = MockContext()
    ctx.obj['like'] = {param: 'foo'}
    with pytest.raises(click.BadParameter):
        PARAM_HANDLER[param](ctx, MockOption(param), '?')


def test_all_callback_pass(data):
    ctx = MockContext()
    ctx.obj['like'] = {'transform': 'foo'}
    assert all_handler(ctx, None, None) is None


def test_all_callback(data):
    ctx = MockContext()
    ctx.obj['like'] = {'transform': 'foo'}
    assert all_handler(ctx, None, True) == {'transform': 'foo'}


def test_all_callback_None(data):
    ctx = MockContext()
    assert all_handler(ctx, None, None) is None


@pytest.mark.parametrize("setci", (
    'red,green,blue,alpha,undefined',
    'red'
))
def test_colorinterp_wrong_band_count(runner, path_3band_no_colorinterp, setci):
    """Provide the wrong band count."""
    result = runner.invoke(main_group, [
        'edit-info', path_3band_no_colorinterp,
        '--colorinterp', setci])
    assert result.exit_code != 0
    assert "Must set color interpretation for all bands" in result.output
    assert "Found 3 bands" in result.output


@pytest.mark.parametrize("setci,expected", [
    ('RGB', (ColorInterp.red, ColorInterp.green, ColorInterp.blue)),
    ('red,green,blue', (ColorInterp.red, ColorInterp.green, ColorInterp.blue)),
])
def test_colorinterp_rgb(setci, expected, path_3band_no_colorinterp, runner):
    """Set 3 band color interpretation."""
    result = runner.invoke(main_group, [
        'edit-info', path_3band_no_colorinterp,
        '--colorinterp', setci])
    assert result.exit_code == 0
    with rasterio.open(path_3band_no_colorinterp) as src:
        assert src.colorinterp == expected


@pytest.mark.parametrize("setci,expected", [
    ('red,green,blue,undefined', (ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.undefined)),
    ('RGBA', (ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.alpha)),
    ('red,green,blue,alpha', (ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.alpha)),
])
def test_colorinterp_4band(setci, expected, path_4band_no_colorinterp, runner):
    """Set 4 band color interpretation."""
    result = runner.invoke(main_group, [
        'edit-info', path_4band_no_colorinterp,
        '--colorinterp', setci])
    assert result.exit_code == 0
    with rasterio.open(path_4band_no_colorinterp) as src:
        assert src.colorinterp == expected


def test_colorinterp_bad_instructions(runner):
    """Can't combine shorthand and normal band instructions."""
    result = runner.invoke(main_group, [
        'edit-info', 'path-to-something',
        '--colorinterp', 'RGB,alpha'])
    assert result.exit_code != 0
    assert "color interpretation 'RGB' is invalid"


def test_colorinterp_like(path_4band_no_colorinterp, path_rgba_byte_tif, runner):
    """Set color interpretation from a ``--like`` image."""
    result = runner.invoke(main_group, [
        'edit-info', path_4band_no_colorinterp,
        '--like', path_rgba_byte_tif,
        '--colorinterp', 'like'])
    assert result.exit_code == 0
    with rasterio.open(path_4band_no_colorinterp) as src:
        assert src.colorinterp == (
            ColorInterp.red,
            ColorInterp.green,
            ColorInterp.blue,
            ColorInterp.alpha)


def test_like_band_count_mismatch(runner, data):
    """Ensure a mismatch in the number of bands for '--colorinterp like' and
    the target image raises an exception.
    """
    # Isolate to avoid potential '.aux.xml' creation.
    rgba = str(data.join('RGBA.byte.tif'))
    rgb = str(data.join('RGB.byte.tif'))
    result = runner.invoke(main_group, [
        'edit-info', rgb, '--colorinterp', 'like', '--like', rgba])
    assert result.exit_code != 0
    assert "When using '--like' for color interpretation" in result.output


@requires_gdal21
def test_colorinterp_like_all(
        runner, path_4band_no_colorinterp, path_rgba_byte_tif, tmpdir):
    """Test setting colorinterp via '--like template --all'."""
    noci = str(tmpdir.join('test_colorinterp_like_all.tif'))
    rasterio.shutil.copy(path_4band_no_colorinterp, noci)
    result = runner.invoke(main_group, [
        'edit-info', noci, '--like', path_rgba_byte_tif, '--all'])
    assert result.exit_code == 0
    with rasterio.open(noci) as src:
        assert src.colorinterp == (
            ColorInterp.red,
            ColorInterp.green,
            ColorInterp.blue,
            ColorInterp.alpha)


def test_transform_callback_pass(data):
    """Always return None if the value is None"""
    ctx = MockContext()
    ctx.obj['like'] = {'transform': 'foo'}
    assert transform_handler(ctx, MockOption('transform'), None) is None


def test_transform_callback_err(data):
    ctx = MockContext()
    ctx.obj['like'] = {'transform': 'foo'}
    with pytest.raises(click.BadParameter):
        transform_handler(ctx, MockOption('transform'), '?')


def test_transform_callback(data):
    ctx = MockContext()
    ctx.obj['like'] = {'transform': 'foo'}
    assert transform_handler(ctx, MockOption('transform'), 'like') == 'foo'


def test_crs_callback_pass(data):
    """Always return None if the value is None."""
    ctx = MockContext()
    ctx.obj['like'] = {'crs': 'foo'}
    assert crs_handler(ctx, MockOption('crs'), None) is None


def test_crs_callback(data):
    ctx = MockContext()
    ctx.obj['like'] = {'crs': 'foo'}
    assert crs_handler(ctx, MockOption('crs'), 'like') == 'foo'


def test_tags_callback_err(data):
    ctx = MockContext()
    ctx.obj['like'] = {'tags': {'foo': 'bar'}}
    with pytest.raises(click.BadParameter):
        tags_handler(ctx, MockOption('tags'), '?') == {'foo': 'bar'}


def test_tags_callback(data):
    ctx = MockContext()
    ctx.obj['like'] = {'tags': {'foo': 'bar'}}
    assert tags_handler(ctx, MockOption('tags'), 'like') == {'foo': 'bar'}

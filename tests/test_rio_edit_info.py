"""Tests for ``$ rio edit-info``."""


import json

import click
from click.testing import CliRunner
from packaging.version import Version, parse
import pytest

import rasterio
from rasterio.enums import ColorInterp
from rasterio.rio.edit_info import (
    all_handler, crs_handler, tags_handler, transform_handler,
    colorinterp_handler)
from rasterio.rio.main import main_group


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


def test_delete_nodata_exclusive_opts(data):
    """--unset-nodata and --nodata can't be used together"""
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--unset-nodata', '--nodata', '0'])
    assert result.exit_code == 2


def test_delete_crs_exclusive_opts(data):
    """--unset-crs and --crs can't be used together"""
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--unset-crs', '--crs', 'epsg:4326'])
    assert result.exit_code == 2


@pytest.mark.skip(
    parse(rasterio.__gdal_version__) < parse('1.10'),
    reason='GDAL version >= 1.10 required')
def test_unset_crs(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(main_group,
                           ['edit-info', inputfile, '--unset-crs'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs is None


@pytest.mark.skip(
    parse(rasterio.__gdal_version__) >= parse('1.10'),
    reason='Test applies to GDAL version < 1.10')
def test_unset_crs_gdal19(data):
    """unsetting crs doesn't work for geotiff and gdal 1.9
    and should emit an warning"""
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    with rasterio.open(inputfile) as src:
        orig_crs = src.crs
    with pytest.warns(UserWarning):
        result = runner.invoke(main_group,
                               ['edit-info', inputfile, '--unset-crs'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs == orig_crs  # nochange


def test_edit_nodata_err(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(main_group,
                           ['edit-info', inputfile, '--nodata', '-1'])
    assert result.exit_code == 2


@pytest.mark.xfail(
    Version(rasterio.__gdal_version__) < Version('2.1'),
    reason='GDAL version >= 2.1 required')
def test_delete_nodata(data):
    """Delete a dataset's nodata value"""
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--unset-nodata'])
    assert result.exit_code == 0


def test_edit_nodata(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--nodata', '255'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.nodata == 255.0


def test_edit_crs_err(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--crs', 'LOL:WUT'])
    assert result.exit_code == 2


def test_edit_crs_epsg(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--crs', 'EPSG:32618'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32618'}


def test_edit_crs_proj4(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--crs', '+init=epsg:32618'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32618'}


def test_edit_crs_obj(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group,
        ['edit-info', inputfile, '--crs', '{"init": "epsg:32618"}'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs.to_dict() == {'init': 'epsg:32618'}


def test_edit_transform_err_not_json(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--transform', 'LOL'])
    assert result.exit_code == 2


def test_edit_transform_err_bad_array(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--transform', '[1,2]'])
    assert result.exit_code == 2


def test_edit_transform_affine(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    input_t = '[300.038, 0.0, 101985.0, 0.0, -300.042, 2826915.0]'
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--transform', input_t])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        for a, b in zip(src.transform, json.loads(input_t)):
            assert round(a, 6) == round(b, 6)


def test_edit_transform_gdal(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    gdal_geotransform = '[101985.0, 300.038, 0.0, 2826915.0, 0.0, -300.042]'
    result = runner.invoke(main_group, [
        'edit-info', inputfile, '--transform', gdal_geotransform])
    assert result.exit_code != 0
    assert 'not recognized as an Affine array' in result.output
    assert gdal_geotransform in result.output


def test_edit_tags(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(main_group, [
        'edit-info', inputfile, '--tag', 'lol=1', '--tag', 'wut=2'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.tags()['lol'] == '1'
        assert src.tags()['wut'] == '2'


def test_edit_band_description(data):
    """Edit band descriptions"""
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(main_group, [
        'edit-info', inputfile, '--bidx', '3', '--description',
        'this is another test'])

    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.descriptions[2] == 'this is another test'


def test_edit_units(data):
    """Edit units"""
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(main_group, [
        'edit-info', inputfile, '--bidx', '1', '--units', 'DN'],
        catch_exceptions=False)

    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.units[0] == 'DN'


def test_edit_crs_like(data):
    runner = CliRunner()

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
        assert src.crs == {'init': 'epsg:32618'}
        assert src.nodata == 1.0


def test_edit_nodata_like(data):
    runner = CliRunner()

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


def test_edit_all_like(data):
    runner = CliRunner()

    inputfile = str(data.join('RGB.byte.tif'))
    with rasterio.open(inputfile, 'r+') as dst:
        dst.crs = {'init': 'epsg:32617'}
        dst.nodata = 1.0

    # Double check.
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32617'}
        assert src.nodata == 1.0

    templatefile = 'tests/data/RGB.byte.tif'
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--like', templatefile, '--all'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32618'}
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


def test_colorinterp_simple(path_4band_no_colorinterp):
    """Set color interpretation for a single band."""
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'edit-info', path_4band_no_colorinterp,
        '--colorinterp', '4=alpha'])
    assert result.exit_code == 0
    with rasterio.open(path_4band_no_colorinterp) as src:
        assert src.colorinterp[3] == ColorInterp.alpha


def test_colorinterp_complex(path_4band_no_colorinterp):
    """Set color interpretation for all bands."""
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'edit-info', path_4band_no_colorinterp,
        '--colorinterp', '4=alpha,3=red,2=blue,1=green'])
    assert result.exit_code == 0
    with rasterio.open(path_4band_no_colorinterp) as src:
        assert src.colorinterp == [
            ColorInterp.green,
            ColorInterp.blue,
            ColorInterp.red,
            ColorInterp.alpha]


@pytest.mark.parametrize("shorthand,expected", [
    ('RGB', [ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.undefined]),
    ('RGBA', [ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.alpha])
])
def test_colorinterp_shorthand(shorthand, expected, path_4band_no_colorinterp):
    """Set color interpretation from 'RGB' and 'RGBA' shorthand."""
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'edit-info', path_4band_no_colorinterp,
        '--colorinterp', shorthand])
    assert result.exit_code == 0
    with rasterio.open(path_4band_no_colorinterp) as src:
        assert src.colorinterp == expected


def test_colorinterp_bad_instructions():
    """Can't combine shorthand and normal band instructions."""
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'edit-info', 'path-to-something',
        '--colorinterp', 'RGB,4=alpha'])
    assert result.exit_code != 0
    assert 'could not parse: RGB,4=alpha' in result.output


def test_colorinterp_like(path_4band_no_colorinterp, path_rgba_byte_tif):
    """Set color interpretation from a ``--like`` image."""
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'edit-info', path_4band_no_colorinterp,
        '--like', path_rgba_byte_tif,
        '--colorinterp', 'like'])
    assert result.exit_code == 0
    with rasterio.open(path_4band_no_colorinterp) as src:
        assert src.colorinterp == [
            ColorInterp.red,
            ColorInterp.green,
            ColorInterp.blue,
            ColorInterp.alpha]


def test_colorinterp_bad_name():
    """Refernce an invalid ``ColorInterp``."""
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'edit-info', 'whatever', '--colorinterp', '1=trash'])
    assert result.exit_code != 0
    for ci in ColorInterp.__members__.keys():
        assert ci in result.output
    assert "'trash' is an unrecognized color interpretation" in result.output

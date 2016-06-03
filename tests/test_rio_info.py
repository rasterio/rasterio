import json
import logging
import sys

import click
from click.testing import CliRunner
import pytest

import rasterio
from rasterio.rio.edit_info import (edit, all_handler, crs_handler,
                                    tags_handler, transform_handler)
from rasterio.rio.main import main_group


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_edit_nodata_err(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(edit, [inputfile, '--nodata', '-1'])
    assert result.exit_code == 2


def test_edit_nodata(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(edit, [inputfile, '--nodata', '255'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.nodata == 255.0


def test_edit_crs_err(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(edit, [inputfile, '--crs', 'LOL:WUT'])
    assert result.exit_code == 2


def test_edit_crs_epsg(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(edit, [inputfile, '--crs', 'EPSG:32618'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32618'}


def test_edit_crs_proj4(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(edit, [inputfile, '--crs', '+init=epsg:32618'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32618'}


def test_edit_crs_obj(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        edit, [inputfile, '--crs', '{"init": "epsg:32618"}'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs == {'init': 'epsg:32618'}


def test_edit_transform_err_not_json(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(edit, [inputfile, '--transform', 'LOL'])
    assert result.exit_code == 2


def test_edit_transform_err_bad_array(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(edit, [inputfile, '--transform', '[1,2]'])
    assert result.exit_code == 2


def test_edit_transform_affine(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    input_t = '[300.038, 0.0, 101985.0, 0.0, -300.042, 2826915.0]'
    result = runner.invoke(edit, [inputfile, '--transform', input_t])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        for a, b in zip(src.affine, json.loads(input_t)):
            assert round(a, 6) == round(b, 6)


def test_edit_transform_gdal(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    input_t = '[300.038, 0.0, 101985.0, 0.0, -300.042, 2826915.0]'
    result = runner.invoke(edit, [
        inputfile,
        '--transform', '[101985.0, 300.038, 0.0, 2826915.0, 0.0, -300.042]'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        for a, b in zip(src.affine, json.loads(input_t)):
            assert round(a, 6) == round(b, 6)


def test_edit_tags(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(edit, [
        inputfile, '--tag', 'lol=1', '--tag', 'wut=2'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.tags()['lol'] == '1'
        assert src.tags()['wut'] == '2'


class MockContext:

    def __init__(self):
        self.obj = {}


class MockOption:

    def __init__(self, name):
        self.name = name


def test_all_callback_pass(data):
    ctx = MockContext()
    ctx.obj['like'] = {'transform': 'foo'}
    assert all_handler(ctx, None, None) == None


def test_all_callback(data):
    ctx = MockContext()
    ctx.obj['like'] = {'transform': 'foo'}
    assert all_handler(ctx, None, True) == {'transform': 'foo'}


def test_all_callback_None(data):
    ctx = MockContext()
    assert all_handler(ctx, None, None) is None


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
    """Always return None if the value is None"""
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


def test_env():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'env',
        '--formats'
    ])
    assert result.exit_code == 0
    assert 'GTiff' in result.output


def test_info_err():
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests'])
    assert result.exit_code == 1


def test_info():
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0
    assert '"count": 3' in result.output


def test_info_verbose():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        '-v',
        'info',
        'tests/data/RGB.byte.tif'
    ])
    assert result.exit_code == 0


def test_info_quiet():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        '-q',
        'info',
        'tests/data/RGB.byte.tif'
    ])
    assert result.exit_code == 0


def test_info_count():
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif', '--count'])
    assert result.exit_code == 0
    assert result.output == '3\n'


def test_info_nodatavals():
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif', '--bounds'])
    assert result.exit_code == 0
    assert result.output == '101985.0 2611485.0 339315.0 2826915.0\n'


def test_info_tags():
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif', '--tags'])
    assert result.exit_code == 0
    assert result.output == '{"AREA_OR_POINT": "Area"}\n'


def test_info_res():
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif', '--res'])
    assert result.exit_code == 0
    assert result.output.startswith('300.037')


def test_info_lnglat():
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif', '--lnglat'])
    assert result.exit_code == 0
    assert result.output.startswith('-77.757')


def test_mo_info():
    runner = CliRunner()
    result = runner.invoke(main_group, ['info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0
    assert '"res": [300.037' in result.output
    assert '"lnglat": [-77.757' in result.output


def test_info_stats():
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif', '--tell-me-more'])
    assert result.exit_code == 0
    assert '"max": 255.0' in result.output
    assert '"min": 1.0' in result.output
    assert '"mean": 44.4344' in result.output


def test_info_stats_only():
    runner = CliRunner()
    result = runner.invoke(
        main_group,
        ['info', 'tests/data/RGB.byte.tif', '--stats', '--bidx', '2'])
    assert result.exit_code == 0
    assert result.output.startswith('1.000000 255.000000 66.02')


def test_transform_err():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'transform'
    ], "[-78.0]")
    assert result.exit_code == 1


def test_transform_point():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'transform',
        '--dst-crs', 'EPSG:32618',
        '--precision', '2'
    ], "[-78.0, 23.0]", catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == '[192457.13, 2546667.68]'


def test_transform_point_dst_file():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'transform',
        '--dst-crs', 'tests/data/RGB.byte.tif', '--precision', '2'
    ], "[-78.0, 23.0]")
    assert result.exit_code == 0
    assert result.output.strip() == '[192457.13, 2546667.68]'


def test_transform_point_src_file():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'transform',
        '--src-crs',
        'tests/data/RGB.byte.tif',
        '--precision', '2'
    ], "[192457.13, 2546667.68]")
    assert result.exit_code == 0
    assert result.output.strip() == '[-78.0, 23.0]'


def test_transform_point_2():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'transform',
        '[-78.0, 23.0]',
        '--dst-crs', 'EPSG:32618',
        '--precision', '2'
    ])
    assert result.exit_code == 0
    assert result.output.strip() == '[192457.13, 2546667.68]'


def test_transform_point_multi():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'transform',
        '--dst-crs', 'EPSG:32618',
        '--precision', '2'
    ], "[-78.0, 23.0]\n[-78.0, 23.0]", catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == (
        '[192457.13, 2546667.68]\n[192457.13, 2546667.68]')


def test_bounds_defaults():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif'
    ])
    assert result.exit_code == 0
    assert 'FeatureCollection' in result.output


def test_bounds_err():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'bounds',
        'tests'
    ])
    assert result.exit_code == 1


def test_bounds_feature():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif',
        '--feature'
    ])
    assert result.exit_code == 0
    assert result.output.count('Polygon') == 1


def test_bounds_obj_bbox():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif',
        '--bbox',
        '--precision', '2'
    ])
    assert result.exit_code == 0
    assert result.output.strip() == '[-78.96, 23.56, -76.57, 25.55]'


def test_bounds_compact():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif',
        '--bbox',
        '--precision', '2',
        '--compact'
    ])
    assert result.exit_code == 0
    assert result.output.strip() == '[-78.96,23.56,-76.57,25.55]'


def test_bounds_indent():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif',
        '--bbox',
        '--indent', '2',
        '--precision', '2'
    ])
    assert result.exit_code == 0
    assert len(result.output.split('\n')) == 7


def test_bounds_obj_bbox_mercator():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif',
        '--bbox',
        '--mercator',
        '--precision', '3'
    ])
    assert result.exit_code == 0
    assert result.output.strip() == (
        '[-8789636.708, 2700489.278, -8524281.514, 2943560.235]')


def test_bounds_obj_bbox_projected():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif',
        '--bbox',
        '--projected',
        '--precision', '3'
    ])
    assert result.exit_code == 0
    assert result.output.strip() == (
        '[101985.0, 2611485.0, 339315.0, 2826915.0]')


def test_bounds_crs_bbox():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif',
        '--bbox',
        '--dst-crs', 'EPSG:32618',
        '--precision', '3'
    ])
    assert result.exit_code == 0
    assert result.output.strip() == (
        '[101985.0, 2611485.0, 339315.0, 2826915.0]')


def test_bounds_seq():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif',
        'tests/data/RGB.byte.tif',
        '--sequence'
    ])
    assert result.exit_code == 0
    assert result.output.count('Polygon') == 2

    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif',
        'tests/data/RGB.byte.tif',
        '--sequence',
        '--bbox',
        '--precision', '2'
    ])
    assert result.exit_code == 0
    assert result.output == (
        '[-78.96, 23.56, -76.57, 25.55]\n[-78.96, 23.56, -76.57, 25.55]\n')
    assert '\x1e' not in result.output


def test_bounds_seq_rs():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif',
        'tests/data/RGB.byte.tif',
        '--sequence',
        '--rs',
        '--bbox',
        '--precision', '2'
    ])
    assert result.exit_code == 0
    assert result.output == (
        '\x1e[-78.96, 23.56, -76.57, 25.55]\n\x1e[-78.96, 23.56, -76.57, 25.55]\n')


def test_info_checksums():
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif', '--tell-me-more'])
    assert result.exit_code == 0
    assert '"checksum": [25420, 29131, 37860]' in result.output


def test_info_checksums_only():
    runner = CliRunner()
    result = runner.invoke(
        main_group,
        ['info', 'tests/data/RGB.byte.tif', '--checksum', '--bidx', '2'])
    assert result.exit_code == 0
    assert result.output.strip() == '29131'

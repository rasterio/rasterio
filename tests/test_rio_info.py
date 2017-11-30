import json

from click.testing import CliRunner
import pytest

import numpy as np
import rasterio
from rasterio.rio.main import main_group
from rasterio.env import GDALVersion

from .conftest import requires_gdal110, requires_less_than_gdal110, requires_gdal21


with rasterio.Env() as env:
    HAVE_NETCDF = 'NetCDF' in env.drivers().keys()


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


@requires_gdal110
def test_unset_crs(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(main_group,
                           ['edit-info', inputfile, '--unset-crs'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.crs is None


@requires_less_than_gdal110
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


@requires_gdal21
def test_delete_nodata(data):
    """Delete a dataset's nodata value"""
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--unset-nodata'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.nodata is None


def test_edit_nodata(data):
    runner = CliRunner()
    inputfile = str(data.join('RGB.byte.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--nodata', '255'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert src.nodata == 255.0


def test_edit_nodata_nan(data):
    runner = CliRunner()
    inputfile = str(data.join('float_nan.tif'))
    result = runner.invoke(
        main_group, ['edit-info', inputfile, '--nodata', 'NaN'])
    assert result.exit_code == 0
    with rasterio.open(inputfile) as src:
        assert np.isnan(src.nodata)


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


def test_env():
    runner = CliRunner()
    result = runner.invoke(main_group, [
        'env',
        '--formats'
    ])
    assert result.exit_code == 0
    assert 'GTiff' in result.output


def test_info_err():
    """Trying to get info of a directory raises an exception"""
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests'])
    assert result.exit_code != 0
    assert result.exception
    # Note: text of exception changed after 2.1, don't test on full string
    assert 'not' in result.output and ' a valid input file' in result.output


def test_info():
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0
    info = json.loads(result.output)
    assert info['count'] == 3
    assert info['dtype'] == 'uint8'
    assert info['crs'] == 'EPSG:32618'

    result = runner.invoke(
        main_group, ['info', 'tests/data/float.tif'])
    assert result.exit_code == 0
    info = json.loads(result.output)
    assert info['count'] == 1
    assert info['dtype'] == 'float64'
    assert info['crs'] is None


def test_info_units():
    """Find a units item"""
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0
    assert '"units": [null, null, null]' in result.output


def test_info_indexes():
    """Find an indexes item"""
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0
    assert '"indexes": [1, 2, 3]' in result.output


def test_info_descriptions():
    """Find description items"""
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0
    assert '"descriptions"' in result.output


def test_info_mask_flags():
    """Find description items"""
    runner = CliRunner()
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0
    assert '"mask_flags": [["nodata"], ["nodata"], ["nodata"]]' in result.output


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


def test_info_colorinterp():
    runner = CliRunner()
    result = runner.invoke(main_group, ['info', 'tests/data/alpha.tif'])
    assert result.exit_code == 0
    assert '"colorinterp": ["red", "green", "blue", "alpha"]' in result.output


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
        '\x1e[-78.96, 23.56, -76.57, 25.55]\n'
        '\x1e[-78.96, 23.56, -76.57, 25.55]\n')


def test_insp():
    runner = CliRunner()
    result = runner.invoke(main_group, ['insp', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0


def test_insp_err():
    runner = CliRunner()
    result = runner.invoke(main_group, ['insp', 'tests'])
    assert result.exit_code != 0


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


@requires_gdal21(reason="NetCDF requires GDAL 2.1+")
@pytest.mark.skipif(not HAVE_NETCDF,
                    reason="GDAL not compiled with NetCDF driver.")
def test_info_subdatasets():
    runner = CliRunner()
    result = runner.invoke(
        main_group,
        ['info', 'netcdf:tests/data/RGB.nc', '--subdatasets'])
    assert result.exit_code == 0
    assert len(result.output) == 93
    assert result.output.startswith('netcdf:tests/data/RGB.nc:Band1')

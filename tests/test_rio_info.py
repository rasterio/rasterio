import json

from click.testing import CliRunner
import pytest

import numpy as np
import rasterio
from rasterio.rio.main import main_group
from rasterio.env import GDALVersion

from .conftest import requires_gdal21


with rasterio.Env() as env:
    HAVE_NETCDF = 'NetCDF' in env.drivers().keys()


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


def test_info_no_credentials(tmpdir, monkeypatch):
    credentials_file = tmpdir.join('credentials')
    monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', str(credentials_file))
    monkeypatch.delenv('AWS_ACCESS_KEY_ID', raising=False)
    runner = CliRunner()
    result = runner.invoke(
        main_group,
        ['info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0

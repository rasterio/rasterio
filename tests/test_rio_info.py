import json

import pytest

import rasterio
from rasterio.rio.main import main_group

from .conftest import credentials


with rasterio.Env() as env:
    HAVE_NETCDF = "netCDF" in env.drivers().keys()


def test_env(runner):
    result = runner.invoke(main_group, [
        'env',
        '--formats'
    ])
    assert result.exit_code == 0
    assert 'GTiff' in result.output


def test_info_err(runner):
    """Trying to get info of a directory raises an exception"""
    result = runner.invoke(
        main_group, ['info', 'tests'])
    assert result.exit_code != 0
    assert result.exception


def test_info(runner):
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


def test_info_units(runner):
    """Find a units item"""
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0
    assert '"units": [null, null, null]' in result.output


def test_info_indexes(runner):
    """Find an indexes item"""
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0
    assert '"indexes": [1, 2, 3]' in result.output


def test_info_descriptions(runner):
    """Find description items"""
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0
    assert '"descriptions"' in result.output


def test_info_mask_flags(runner):
    """Find description items"""
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0
    assert '"mask_flags": [["nodata"], ["nodata"], ["nodata"]]' in result.output


def test_info_verbose(runner):
    result = runner.invoke(main_group, [
        '-v',
        'info',
        'tests/data/RGB.byte.tif'
    ])
    assert result.exit_code == 0


def test_info_quiet(runner):
    result = runner.invoke(main_group, [
        '-q',
        'info',
        'tests/data/RGB.byte.tif'
    ])
    assert result.exit_code == 0


def test_info_gcps(runner):
    result = runner.invoke(main_group, [
        'info',
        'tests/data/white-gemini-iv.vrt'
    ])
    assert result.exit_code == 0


def test_info_count(runner):
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif', '--count'])
    assert result.exit_code == 0
    assert result.output == '3\n'


def test_info_nodatavals(runner):
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif', '--bounds'])
    assert result.exit_code == 0
    assert result.output == '101985.0 2611485.0 339315.0 2826915.0\n'


def test_info_tags(runner):
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif', '--tags'])
    assert result.exit_code == 0
    assert result.output == '{"AREA_OR_POINT": "Area"}\n'


def test_info_res(runner):
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif', '--res'])
    assert result.exit_code == 0
    assert result.output.startswith('300.037')


def test_info_lnglat(runner):
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif', '--lnglat'])
    assert result.exit_code == 0
    assert result.output.startswith('-77.757')


def test_mo_info(runner):
    result = runner.invoke(main_group, ['info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0
    assert '"res": [300.037' in result.output
    assert '"lnglat": [-77.757' in result.output


def test_info_stats(runner):
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif', '--tell-me-more'])
    assert result.exit_code == 0
    assert '"max": 255.0' in result.output
    assert '"min": 1.0' in result.output


def test_info_stats_only(runner):
    result = runner.invoke(
        main_group,
        ['info', 'tests/data/RGB.byte.tif', '--stats', '--bidx', '2'])
    assert result.exit_code == 0
    assert result.output.startswith("1.0 255.0")


def test_info_colorinterp(runner):
    result = runner.invoke(main_group, ['info', 'tests/data/alpha.tif'])
    assert result.exit_code == 0
    assert '"colorinterp": ["red", "green", "blue", "alpha"]' in result.output


def test_transform_err(runner):
    result = runner.invoke(main_group, [
        'transform'
    ], "[-78.0]")
    assert result.exit_code == 1


def test_transform_point(runner):
    result = runner.invoke(main_group, [
        'transform',
        '--dst-crs', 'EPSG:32618',
        '--precision', '2'
    ], "[-78.0, 23.0]", catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == '[192457.13, 2546667.68]'


def test_transform_point_dst_file(runner):
    result = runner.invoke(main_group, [
        'transform',
        '--dst-crs', 'tests/data/RGB.byte.tif', '--precision', '2'
    ], "[-78.0, 23.0]")
    assert result.exit_code == 0
    assert result.output.strip() == '[192457.13, 2546667.68]'


def test_transform_point_src_file(runner):
    result = runner.invoke(main_group, [
        'transform',
        '--src-crs',
        'tests/data/RGB.byte.tif',
        '--precision', '2'
    ], "[192457.13, 2546667.68]")
    assert result.exit_code == 0
    assert result.output.strip() == '[-78.0, 23.0]'


def test_transform_point_2(runner):
    result = runner.invoke(main_group, [
        'transform',
        '[-78.0, 23.0]',
        '--dst-crs', 'EPSG:32618',
        '--precision', '2'
    ])
    assert result.exit_code == 0
    assert result.output.strip() == '[192457.13, 2546667.68]'


def test_transform_point_multi(runner):
    result = runner.invoke(main_group, [
        'transform',
        '--dst-crs', 'EPSG:32618',
        '--precision', '2'
    ], "[-78.0, 23.0]\n[-78.0, 23.0]", catch_exceptions=False)
    assert result.exit_code == 0
    assert result.output.strip() == (
        '[192457.13, 2546667.68]\n[192457.13, 2546667.68]')


def test_bounds_defaults(runner):
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif'
    ])
    assert result.exit_code == 0
    assert 'Feature' in result.output


def test_bounds_err(runner):
    result = runner.invoke(main_group, [
        'bounds',
        'tests'
    ])
    assert result.exit_code == 1


def test_bounds_feature(runner):
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif',
        '--feature'
    ])
    assert result.exit_code == 0
    assert result.output.count('Polygon') == 1


def test_bounds_obj_bbox(runner):
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif',
        '--bbox',
        '--precision', '2'
    ])
    assert result.exit_code == 0
    assert result.output.strip() == '[-78.96, 23.56, -76.57, 25.55]'


def test_bounds_compact(runner):
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif',
        '--bbox',
        '--precision', '2',
        '--compact'
    ])
    assert result.exit_code == 0
    assert result.output.strip() == '[-78.96,23.56,-76.57,25.55]'


def test_bounds_indent(runner):
    result = runner.invoke(main_group, [
        'bounds',
        'tests/data/RGB.byte.tif',
        '--bbox',
        '--indent', '2',
        '--precision', '2'
    ])
    assert result.exit_code == 0
    assert len(result.output.split('\n')) == 7


def test_bounds_obj_bbox_mercator(runner):
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


def test_bounds_obj_bbox_projected(runner):
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


def test_bounds_crs_bbox(runner):
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


def test_bounds_seq(runner):
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


def test_bounds_seq_rs(runner):
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


def test_insp(runner):
    result = runner.invoke(main_group, ['insp', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0


def test_insp_err(runner):
    result = runner.invoke(main_group, ['insp', 'tests'])
    assert result.exit_code != 0


def test_info_checksums(runner):
    result = runner.invoke(
        main_group, ['info', 'tests/data/RGB.byte.tif', '--tell-me-more'])
    assert result.exit_code == 0
    assert '"checksum": [25420, 29131, 37860]' in result.output


def test_info_checksums_only(runner):
    result = runner.invoke(
        main_group,
        ['info', 'tests/data/RGB.byte.tif', '--checksum', '--bidx', '2'])
    assert result.exit_code == 0
    assert result.output.strip() == '29131'


@pytest.mark.skipif(not HAVE_NETCDF,
                    reason="GDAL not compiled with NetCDF driver.")
def test_info_subdatasets(runner):
    result = runner.invoke(
        main_group,
        ['info', 'netcdf:tests/data/RGB.nc', '--subdatasets'])
    assert result.exit_code == 0
    assert len(result.output) == 93
    assert result.output.startswith('netcdf:tests/data/RGB.nc:Band1')


def test_info_no_credentials(tmpdir, monkeypatch, runner):
    credentials_file = tmpdir.join('credentials')
    monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', str(credentials_file))
    monkeypatch.delenv('AWS_ACCESS_KEY_ID', raising=False)
    result = runner.invoke(
        main_group,
        ['info', 'tests/data/RGB.byte.tif'])
    assert result.exit_code == 0

@credentials
@pytest.mark.network
def test_info_aws_unsigned(runner):
    """Unsigned access to public dataset works (see #1637)"""
    result = runner.invoke(main_group, ['--aws-no-sign-requests', 'info', 's3://sentinel-cogs/sentinel-s2-l2a-cogs/45/C/VQ/2022/11/S2B_45CVQ_20221102_0_L2A/B01.tif'])
    assert result.exit_code == 0


@pytest.mark.network
@pytest.mark.skip(reason="Undiagnosed problem accessing this file")
def test_info_azure_unsigned(monkeypatch, runner):
    """Unsigned access to public dataset works"""
    monkeypatch.setenv('AZURE_NO_SIGN_REQUEST', 'YES')
    monkeypatch.setenv('AZURE_STORAGE_ACCOUNT', 'naipblobs')
    result = runner.invoke(main_group, ['info', 'az://naip/v002/md/2017/md_100cm_2017/39077/m_3907744_ne_18_1_20170628.tif'])
    assert result.exit_code == 0

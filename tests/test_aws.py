# Tests requiring S3 credentials.
# Collected here to make them easier to skip/xfail.

import logging
import sys

from packaging.version import parse
import pytest

import rasterio
from rasterio.aws import Session
from rasterio.rio.main import main_group


# Custom markers.
mingdalversion = pytest.mark.skipif(
    parse(rasterio.__gdal_version__) < parse('2.1.0dev'),
    reason="S3 raster access requires GDAL 2.1")

credentials = pytest.mark.skipif(
    not(Session()._creds), reason="S3 raster access requires credentials")


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

L8TIF = "s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF"


def test_session():
    """Create a session with arguments."""
    s = Session(aws_access_key_id='id', aws_secret_access_key='key',
                aws_session_token='token', region_name='null-island-1')
    assert s._creds.access_key == 'id'
    assert s._creds.secret_key == 'key'
    assert s._creds.token == 'token'
    assert s._session.region_name == 'null-island-1'


def test_session_env(monkeypatch):
    """Create a session with env vars."""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'id')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'key')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'token')
    s = Session()
    assert s._creds.access_key == 'id'
    assert s._creds.secret_key == 'key'
    assert s._creds.token == 'token'
    monkeypatch.undo()


@mingdalversion
@credentials
def test_with_session():
    """Enter and exit a session."""
    with Session():
        with rasterio.open(L8TIF) as f:
            assert f.count == 1


@mingdalversion
@credentials
def test_open_with_session():
    """Enter and exit a session."""
    s = Session()
    with s.open(L8TIF) as f:
        assert f.count == 1


@mingdalversion
@credentials
def test_open_with_session_minus_mode():
    """Enter and exit a session, reading in 'r-' mode"""
    s = Session()
    with s.open(L8TIF, 'r-') as f:
        assert f.count == 1


# CLI tests.

@mingdalversion
@credentials
def test_rio_info(runner):
    """S3 is supported by rio-info"""
    result = runner.invoke(main_group, ['info', L8TIF])
    assert result.exit_code == 0
    assert '"crs": "EPSG:32645"' in result.output


@mingdalversion
@credentials
def test_rio_insp(runner):
    """S3 is supported by rio-insp"""
    result = runner.invoke(main_group, ['insp', L8TIF])
    assert result.exit_code == 0
    assert 'Interactive Inspector' in result.output


@mingdalversion
@credentials
def test_rio_bounds(runner):
    """S3 is supported by rio-bounds"""
    result = runner.invoke(main_group, ['bounds', '--bbox', L8TIF])
    assert result.exit_code == 0
    assert '[85.8' in result.output


@mingdalversion
@credentials
def test_rio_shapes(runner):
    """S3 is supported by rio-shapes"""
    result = runner.invoke(
        main_group, ['shapes', '--as-mask', '--sampling', '16', L8TIF])
    assert result.exit_code == 0
    assert 'FeatureCollection' in result.output


@mingdalversion
@credentials
def test_rio_sample(runner):
    """S3 is supported by rio-sample"""
    result = runner.invoke(
        main_group, ['sample', L8TIF], input="[420000, 2350000]")
    assert result.exit_code == 0
    assert '[10680]' in result.output


@mingdalversion
@credentials
def test_rio_clip(runner, tmpdir):
    """S3 is supported by rio-clip"""
    outputfile = tmpdir.join('clipped.tif')
    result = runner.invoke(
        main_group, ['clip', '--bounds', '420000', '2350000', '420060', '2350060',
                     '-o', str(outputfile), L8TIF])
    assert result.exit_code == 0

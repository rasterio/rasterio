# Tests requiring S3 credentials.
# Collected here to make them easier to skip/xfail.

import logging
import sys

import boto3
from packaging.version import parse
import pytest

import rasterio
import rasterio.env
from rasterio.errors import EnvError
from rasterio.rio.main import main_group


# Custom markers.
mingdalversion = pytest.mark.skipif(
    parse(rasterio.__gdal_version__) < parse('2.1.0dev'),
    reason="S3 raster access requires GDAL 2.1")

credentials = pytest.mark.skipif(
    not(boto3.Session()._session.get_credentials()),
    reason="S3 raster access requires credentials")


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

L8TIF = "s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF"
httpstif = "https://landsat-pds.s3.amazonaws.com/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF"


def test_open_with_default_env():
    """Read from a dataset with a default env."""
    with rasterio.open('tests/data/RGB.byte.tif') as dataset:
        assert rasterio.env._env
        assert dataset.count == 3


def test_env_single():
    """Our env is effectively a singleton."""
    with rasterio.env.Env():
        with pytest.raises(EnvError):
            rasterio.env.Env()


def test_open_with_env():
    """Read from a dataset with an explicit env."""
    with rasterio.env.Env() as env:
        assert rasterio.env._env is env
        with rasterio.open('tests/data/RGB.byte.tif') as dataset:
            assert dataset.count == 3


def test_aws_session():
    """Create an Env with a boto3 session."""
    aws_session = boto3.Session(
        aws_access_key_id='id', aws_secret_access_key='key',
        aws_session_token='token', region_name='null-island-1')
    s = rasterio.env.Env(aws_session=aws_session)
    assert rasterio.env._env is s
    assert s._creds.access_key == 'id'
    assert s._creds.secret_key == 'key'
    assert s._creds.token == 'token'
    assert s.aws_session.region_name == 'null-island-1'


def test_session_lazy():
    """Create an Env with lazy boto3 session."""
    with rasterio.env.Env(
            aws_access_key_id='id', aws_secret_access_key='key',
            aws_session_token='token', region_name='null-island-1') as s:
        assert s._creds is None
        s.get_aws_credentials()
        assert s._creds.access_key == 'id'
        assert s._creds.secret_key == 'key'
        assert s._creds.token == 'token'
        assert s.aws_session.region_name == 'null-island-1'


def test_session_env_lazy(monkeypatch):
    """Create an Env with AWS env vars."""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'id')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'key')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'token')
    with rasterio.env.Env() as s:
        assert s._creds is None
        s.get_aws_credentials()
        assert s._creds.access_key == 'id'
        assert s._creds.secret_key == 'key'
        assert s._creds.token == 'token'
    monkeypatch.undo()


@mingdalversion
@credentials
def test_s3_open_with_session():
    """Read from S3 demonstrating lazy credentials."""
    with rasterio.env.Env() as env:
        assert env._creds is None
        with rasterio.open(L8TIF) as dataset:
            assert env._creds
            assert dataset.count == 1


@mingdalversion
@credentials
def test_s3_open_with_default_session():
    """Read from S3 using default env."""
    with rasterio.open(L8TIF) as dataset:
        assert dataset.count == 1


@mingdalversion
def test_open_https_vsicurl():
    """Read from HTTPS URL"""
    with rasterio.env.Env():
        with rasterio.open(httpstif) as dataset:
            assert dataset.count == 1


# CLI tests.

@mingdalversion
@credentials
def test_s3_rio_info(runner):
    """S3 is supported by rio-info"""
    result = runner.invoke(main_group, ['info', L8TIF])
    assert result.exit_code == 0
    assert '"crs": "EPSG:32645"' in result.output


@mingdalversion
@credentials
def test_https_rio_info(runner):
    """HTTPS is supported by rio-info"""
    result = runner.invoke(main_group, ['info', httpstif])
    assert result.exit_code == 0
    assert '"crs": "EPSG:32645"' in result.output

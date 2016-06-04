# Tests requiring S3 credentials.
# Collected here to make them easier to skip/xfail.

import logging
import sys

import boto3
import pytest
from packaging.version import parse

import rasterio
from rasterio._drivers import del_gdal_config, get_gdal_config, set_gdal_config
from rasterio.env import defenv, delenv, ensure_env, getenv, setenv
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


def test_gdal_config_accessers():
    """Low level GDAL config access."""
    assert get_gdal_config('foo') is None
    set_gdal_config('foo', 'bar')
    assert get_gdal_config('foo') == 'bar'
    del_gdal_config('foo')
    assert get_gdal_config('foo') is None


# The 'gdalenv' fixture ensures that gdal configuration is deleted
# at the end of the test, making tests as isolates as GDAL allows.

def test_env_accessors(gdalenv):
    """High level GDAL env access."""
    defenv()
    setenv(foo='1', bar='2')
    assert getenv() == rasterio.env._env.options == {'foo': '1', 'bar': '2'}
    assert get_gdal_config('foo') == '1'
    assert get_gdal_config('bar') == '2'
    delenv()
    assert getenv() == rasterio.env._env.options == {}
    assert get_gdal_config('foo') is None
    assert get_gdal_config('bar') is None
    rasterio.env._env = None
    with pytest.raises(EnvError):
        delenv()
    with pytest.raises(EnvError):
        setenv()
    with pytest.raises(EnvError):
        getenv()


def test_ensure_env_decorator(gdalenv):
    def f(x):
        return x
    wrapper = ensure_env(f)
    assert wrapper == f


def test_no_aws_gdal_config(gdalenv):
    """Trying to set AWS-specific GDAL config options fails."""
    with pytest.raises(EnvError):
        rasterio.Env(AWS_ACCESS_KEY_ID='x')
    with pytest.raises(EnvError):
        rasterio.Env(AWS_SECRET_ACCESS_KEY='y')


def test_env_options(gdalenv):
    """Test env options."""
    env = rasterio.Env(foo='x')
    assert env.options == {'foo': 'x'}
    assert not env.previous_options
    assert getenv() == rasterio.env._env.options == {}
    with env:
        assert getenv() == rasterio.env._env.options == {'foo': 'x'}
    assert getenv() == rasterio.env._env.options == {}


def test_aws_session(gdalenv):
    """Create an Env with a boto3 session."""
    aws_session = boto3.Session(
        aws_access_key_id='id', aws_secret_access_key='key',
        aws_session_token='token', region_name='null-island-1')
    s = rasterio.env.Env(aws_session=aws_session)
    assert s._creds.access_key == 'id'
    assert s._creds.secret_key == 'key'
    assert s._creds.token == 'token'
    assert s.aws_session.region_name == 'null-island-1'


def test_aws_session_credentials(gdalenv):
    """Create an Env with a boto3 session."""
    aws_session = boto3.Session(
        aws_access_key_id='id', aws_secret_access_key='key',
        aws_session_token='token', region_name='null-island-1')
    s = rasterio.env.Env(aws_session=aws_session)
    assert getenv() == rasterio.env._env.options == {}
    s.get_aws_credentials()
    assert getenv() == rasterio.env._env.options == {
        'aws_access_key_id': 'id', 'aws_region': 'null-island-1',
        'aws_secret_access_key': 'key', 'aws_session_token': 'token'}


def test_with_aws_session_credentials(gdalenv):
    """Create an Env with a boto3 session."""
    with rasterio.Env(aws_access_key_id='id', aws_secret_access_key='key',
             aws_session_token='token', region_name='null-island-1') as s:
        assert getenv() == rasterio.env._env.options == {}
        s.get_aws_credentials()
        assert getenv() == rasterio.env._env.options == {
            'aws_access_key_id': 'id', 'aws_region': 'null-island-1',
            'aws_secret_access_key': 'key', 'aws_session_token': 'token'}


def test_session_env_lazy(monkeypatch, gdalenv):
    """Create an Env with AWS env vars."""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'id')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'key')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'token')
    with rasterio.Env() as s:
        s.get_aws_credentials()
        assert getenv() == rasterio.env._env.options
        expected = {
            'aws_access_key_id': 'id',
            'aws_secret_access_key': 'key',
            'aws_session_token': 'token'}
        for k, v in expected.items():
            assert getenv()[k] == v

    monkeypatch.undo()


def test_open_with_default_env(gdalenv):
    """Read from a dataset with a default env."""
    with rasterio.open('tests/data/RGB.byte.tif') as dataset:
        assert dataset.count == 3


def test_open_with_env(gdalenv):
    """Read from a dataset with an explicit env."""
    with rasterio.Env():
        with rasterio.open('tests/data/RGB.byte.tif') as dataset:
            assert dataset.count == 3


@mingdalversion
@credentials
def test_s3_open_with_session(gdalenv):
    """Read from S3 demonstrating lazy credentials."""
    with rasterio.Env():
        with rasterio.open(L8TIF) as dataset:
            assert dataset.count == 1


@mingdalversion
@credentials
def test_s3_open_with_default_session(gdalenv):
    """Read from S3 using default env."""
    with rasterio.open(L8TIF) as dataset:
        assert dataset.count == 1


@mingdalversion
def test_open_https_vsicurl(gdalenv):
    """Read from HTTPS URL."""
    with rasterio.Env():
        with rasterio.open(httpstif) as dataset:
            assert dataset.count == 1


# CLI tests.

@mingdalversion
@credentials
def test_s3_rio_info(runner):
    """S3 is supported by rio-info."""
    result = runner.invoke(main_group, ['info', L8TIF])
    assert result.exit_code == 0
    assert '"crs": "EPSG:32645"' in result.output


@mingdalversion
@credentials
def test_https_rio_info(runner):
    """HTTPS is supported by rio-info."""
    result = runner.invoke(main_group, ['info', httpstif])
    assert result.exit_code == 0
    assert '"crs": "EPSG:32645"' in result.output

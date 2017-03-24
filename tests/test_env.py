# Tests requiring S3 credentials.
# Collected here to make them easier to skip/xfail.

import logging
import sys

import boto3
from packaging.version import parse
import pytest

import rasterio
from rasterio._env import del_gdal_config, get_gdal_config, set_gdal_config
from rasterio.env import defenv, delenv, getenv, setenv, ensure_env
from rasterio.env import default_options
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


def test_gdal_config_accessors_no_normalize():
    """Disables casting keys to upper case and normalizing values to boolean
    Python values.
    """
    assert get_gdal_config('foo') is None
    set_gdal_config('foo', 'ON', normalize=False)
    assert get_gdal_config('foo', normalize=False) == 'ON'
    del_gdal_config('foo')
    assert get_gdal_config('foo') is None


def test_gdal_config_accessors_capitalization():
    """GDAL normalizes config names to upper case so Rasterio does not
    need to do it on its own.  This test serves as a canary in case GDAL
    changes its behavior, which is an important part of reinstating
    discovered environment variables when ``rasterio.Env()`` starts.
    GDAL does not alter config values.
    """
    assert get_gdal_config('foo') is None
    assert get_gdal_config('FOO') is None

    set_gdal_config('foo', 'bar')

    assert get_gdal_config('foo') == 'bar'
    assert get_gdal_config('FOO') == 'bar'

    del_gdal_config('foo')
    assert get_gdal_config('foo') is None
    assert get_gdal_config('FOO') is None

    set_gdal_config('upper', 'UPPER')
    assert get_gdal_config('upper') == 'UPPER'
    del_gdal_config('upper')


# The 'gdalenv' fixture ensures that gdal configuration is deleted
# at the end of the test, making tests as isolates as GDAL allows.

def test_env_accessors(gdalenv):
    """High level GDAL env access."""
    defenv()
    setenv(foo='1', bar='2')
    expected = default_options.copy()
    expected.update({'foo': '1', 'bar': '2'})
    assert getenv() == rasterio.env.local._env.options
    assert getenv() == expected
    assert get_gdal_config('foo') == '1'
    assert get_gdal_config('bar') == '2'
    delenv()
    with pytest.raises(EnvError):
        getenv()
    assert get_gdal_config('foo') is None
    assert get_gdal_config('bar') is None


def test_env_accessors_no_env():
    """Sould all raise an exception."""
    with pytest.raises(EnvError):
        delenv()
    with pytest.raises(EnvError):
        setenv()
    with pytest.raises(EnvError):
        getenv()


def test_ensure_env_decorator(gdalenv):
    @ensure_env
    def f():
        return getenv()['RASTERIO_ENV']
    assert f() is True


def test_no_aws_gdal_config(gdalenv):
    """Trying to set AWS-specific GDAL config options fails."""
    with pytest.raises(EnvError):
        rasterio.Env(AWS_ACCESS_KEY_ID='x')
    with pytest.raises(EnvError):
        rasterio.Env(AWS_SECRET_ACCESS_KEY='y')


def test_env_defaults(gdalenv):
    """Test env defaults."""
    env = rasterio.Env(foo='x')
    assert env.options['foo'] == 'x'
    assert not env.context_options
    with env:
        assert get_gdal_config('CHECK_WITH_INVERT_PROJ') is True
        assert get_gdal_config('GTIFF_IMPLICIT_JPEG_OVR') is False
        assert get_gdal_config("RASTERIO_ENV") is True


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
    with rasterio.env.Env(aws_session=aws_session) as s:
        s.get_aws_credentials()
        assert getenv()['aws_access_key_id'] == 'id'
        assert getenv()['aws_region'] == 'null-island-1'
        assert getenv()['aws_secret_access_key'] == 'key'
        assert getenv()['aws_session_token'] == 'token'


def test_with_aws_session_credentials(gdalenv):
    """Create an Env with a boto3 session."""
    with rasterio.Env(
            aws_access_key_id='id', aws_secret_access_key='key',
            aws_session_token='token', region_name='null-island-1') as s:
        expected = default_options.copy()
        assert getenv() == rasterio.env.local._env.options == expected
        s.get_aws_credentials()
        expected.update({
            'aws_access_key_id': 'id', 'aws_region': 'null-island-1',
            'aws_secret_access_key': 'key', 'aws_session_token': 'token'})
        assert getenv() == rasterio.env.local._env.options == expected


def test_session_env_lazy(monkeypatch, gdalenv):
    """Create an Env with AWS env vars."""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'id')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'key')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'token')
    with rasterio.Env() as s:
        s.get_aws_credentials()
        assert getenv() == rasterio.env.local._env.options
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


def test_rio_env_credentials_options(tmpdir, monkeypatch, runner):
    """Confirm that --aws-profile option works."""
    credentials_file = tmpdir.join('credentials')
    credentials_file.write("[testing]\n"
                           "aws_access_key_id = foo\n"
                           "aws_secret_access_key = bar\n"
                           "aws_session_token = baz")
    monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', str(credentials_file))
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'ignore_me')
    result = runner.invoke(
        main_group, ['--aws-profile', 'testing', 'env', '--credentials'])
    assert result.exit_code == 0
    assert '"aws_access_key_id": "foo"' in result.output
    assert '"aws_secret_access_key": "bar"' in result.output
    assert '"aws_session_token": "baz"' in result.output
    monkeypatch.undo()


def test_ensure_defaults_teardown(gdalenv):

    """This test guards against a regression.  Previously ``rasterio.Env()``
    would quietly reinstate any ``rasterio.env.default_options`` that was
    not modified by the environment.

    https://github.com/mapbox/rasterio/issues/968
    """

    def _check_defaults():
        for key in default_options.keys():
            assert get_gdal_config(key) is None

    _check_defaults()
    with rasterio.Env():
        pass

    _check_defaults()
    assert rasterio.env.local._env is None


@pytest.mark.parametrize("key,val", [
    ('key', 'ON'),
    ('CHECK_WITH_INVERT_PROJ', 'ON'),
    ('key', 'OFF'),
    ('CHECK_WITH_INVERT_PROJ', 'OFF')])
def test_env_discovery(key, val):
    """When passing options to ``rasterio.Env()`` Rasterio first checks
    to see if they were set in the environment and reinstates on exit.
    The discovered environment should only be reinstated when the outermost
    environment exits.  It's really important that this test use an
    environment default.
    """

    assert rasterio.env.local._discovered_options is None, \
        "Something has gone horribly wrong."

    try:
        # This should persist when all other environment managers exit.
        set_gdal_config(key, val)

        # Start an environment and overwrite the value that should persist
        with rasterio.Env(**{key: True}):
            assert get_gdal_config(key) is True
            assert rasterio.env.local._discovered_options == {key: val}

            # Start another nested environment, again overwriting the value
            # that should persist
            with rasterio.Env(**{key: False}):
                assert rasterio.env.local._discovered_options == {key: val}
                assert get_gdal_config(key) is False

            # Ensure the outer state is restored.
            assert rasterio.env.local._discovered_options == {key: val}
            assert get_gdal_config(key) is True

        # Ensure the discovered value remains unchanged.
        assert rasterio.env.local._discovered_options is None
        assert get_gdal_config(key, normalize=False) == val

    # Leaving this option in the GDAL environment could cause a problem
    # for other tests.
    finally:
        del_gdal_config(key)

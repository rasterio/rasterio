import logging
import os
import sys

import pytest

import rasterio
from rasterio.aws import Session


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


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


@pytest.mark.xfail(
    (not(os.environ.get('GDALVERSION', '2.1').startswith('2.1')) or
        'AWS_ACCESS_KEY_ID' not in os.environ or
        'AWS_SECRET_ACCESS_KEY' not in os.environ),
    reason="S3 raster access requires GDAL 2.1")
def test_with_session():
    """Enter and exit a session."""
    with Session() as s:
        with rasterio.open("s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF") as f:
            assert f.count == 1


@pytest.mark.xfail(
    (not(os.environ.get('GDALVERSION', '2.1').startswith('2.1')) or
        'AWS_ACCESS_KEY_ID' not in os.environ or
        'AWS_SECRET_ACCESS_KEY' not in os.environ),
    reason="S3 raster access requires GDAL 2.1")
def test_open_with_session():
    """Enter and exit a session."""
    s = Session()
    with s.open("s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF") as f:
        assert f.count == 1


@pytest.mark.xfail(
    (not(os.environ.get('GDALVERSION', '2.1').startswith('2.1')) or
        'AWS_ACCESS_KEY_ID' not in os.environ or
        'AWS_SECRET_ACCESS_KEY' not in os.environ),
    reason="S3 raster access requires GDAL 2.1")
def test_open_with_session_minus_mode():
    """Enter and exit a session, reading in 'r-' mode"""
    s = Session()
    with s.open("s3://landsat-pds/L8/139/045/LC81390452014295LGN00/LC81390452014295LGN00_B1.TIF", 'r-') as f:
        assert f.count == 1

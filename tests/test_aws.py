import logging
import sys

from rasterio.aws import Session


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_session():
    """Create a session with arguments."""
    s = Session(aws_access_key_id='id', aws_secret_access_key='key',
                 aws_session_token='token', region_name='null-island-1')
    assert s.aws_access_key_id == 'id'
    assert s.aws_secret_access_key == 'key'
    assert s.aws_session_token == 'token'
    assert s.region_name == 'null-island-1'


def test_session_env(monkeypatch):
    """Create a session with env vars."""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'id')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'key')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'token')
    s = Session()
    assert s.aws_access_key_id == 'id'
    assert s.aws_secret_access_key == 'key'
    assert s.aws_session_token == 'token'
    assert s.region_name == 'us-east-1'
    monkeypatch.undo()


def test_session_config(tmpdir):
    """Create a session with config files."""
    credentials = tmpdir.join('credentials')
    credentials.write(
        "[default]\n"
        "aws_access_key_id = id\n"
        "aws_secret_access_key = key\n")
    config = tmpdir.join('config')
    config.write(
        "[default]\n"
        "region = null-island-1\n")
    s = Session(config_dir=str(tmpdir))
    assert s.aws_access_key_id == 'id'
    assert s.aws_secret_access_key == 'key'
    assert s.region_name == 'null-island-1'


def test_with_session():
    """Enter and exit a session."""
    s = Session(aws_access_key_id='id', aws_secret_access_key='key',
                 aws_session_token='token', region_name='null-island-1')
    with s:
        pass

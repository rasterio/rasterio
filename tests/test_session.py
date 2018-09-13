"""Tests of session module"""

import pytest

from rasterio.session import DummySession, AWSSession, Session


def test_dummy_session():
    """DummySession works"""
    sesh = DummySession()
    assert sesh._session is None
    assert sesh.get_credential_options() == {}


def test_aws_session_class():
    """AWSSession works"""
    sesh = AWSSession(aws_access_key_id='foo', aws_secret_access_key='bar')
    assert sesh._session
    assert sesh.get_credential_options()['AWS_ACCESS_KEY_ID'] == 'foo'
    assert sesh.get_credential_options()['AWS_SECRET_ACCESS_KEY'] == 'bar'


def test_aws_session_class_session():
    """AWSSession works"""
    boto3 = pytest.importorskip("boto3")
    sesh = AWSSession(session=boto3.session.Session(aws_access_key_id='foo', aws_secret_access_key='bar'))
    assert sesh._session
    assert sesh.get_credential_options()['AWS_ACCESS_KEY_ID'] == 'foo'
    assert sesh.get_credential_options()['AWS_SECRET_ACCESS_KEY'] == 'bar'


def test_aws_session_class_unsigned():
    """AWSSession works"""
    pytest.importorskip("boto3")
    sesh = AWSSession(aws_unsigned=True)
    assert sesh._session
    assert sesh.get_credential_options()['AWS_NO_SIGN_REQUEST'] == 'YES'


def test_aws_session_class_profile(tmpdir, monkeypatch):
    """Confirm that profile_name kwarg works."""
    pytest.importorskip("boto3")
    credentials_file = tmpdir.join('credentials')
    credentials_file.write("[testing]\n"
                           "aws_access_key_id = foo\n"
                           "aws_secret_access_key = bar\n"
                           "aws_session_token = baz")
    monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', str(credentials_file))
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'ignore_me')
    sesh = AWSSession(profile_name='testing')
    assert sesh._session
    assert sesh.get_credential_options()['AWS_ACCESS_KEY_ID'] == 'foo'
    assert sesh.get_credential_options()['AWS_SECRET_ACCESS_KEY'] == 'bar'
    assert sesh.get_credential_options()['AWS_SESSION_TOKEN'] == 'baz'
    monkeypatch.undo()


def test_session_factory_unparsed():
    """Get a DummySession for unparsed paths"""
    sesh = Session.from_path("/vsicurl/lolwut")
    assert isinstance(sesh, DummySession)


def test_session_factory_empty():
    """Get a DummySession for no path"""
    sesh = Session.from_path("")
    assert isinstance(sesh, DummySession)


def test_session_factory_local():
    """Get a DummySession for local paths"""
    sesh = Session.from_path("file:///lolwut")
    assert isinstance(sesh, DummySession)


def test_session_factory_unknown():
    """Get a DummySession for unknown paths"""
    sesh = Session.from_path("https://fancy-cloud.com/lolwut")
    assert isinstance(sesh, DummySession)


def test_session_factory_s3():
    """Get an AWSSession for s3:// paths"""
    pytest.importorskip("boto3")
    sesh = Session.from_path("s3://lol/wut")
    assert isinstance(sesh, AWSSession)


def test_session_factory_s3_kwargs():
    """Get an AWSSession for s3:// paths with keywords"""
    pytest.importorskip("boto3")
    sesh = Session.from_path("s3://lol/wut", aws_access_key_id='foo', aws_secret_access_key='bar')
    assert isinstance(sesh, AWSSession)
    assert sesh._session.get_credentials().access_key == 'foo'
    assert sesh._session.get_credentials().secret_key == 'bar'


def test_foreign_session_factory_dummy():
    sesh = Session.from_foreign_session(None)
    assert isinstance(sesh, DummySession)


def test_foreign_session_factory_s3():
    boto3 = pytest.importorskip("boto3")
    aws_session = boto3.Session(aws_access_key_id='foo', aws_secret_access_key='bar')
    sesh = Session.from_foreign_session(aws_session, cls=AWSSession)
    assert isinstance(sesh, AWSSession)
    assert sesh._session.get_credentials().access_key == 'foo'
    assert sesh._session.get_credentials().secret_key == 'bar'

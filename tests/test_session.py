"""Tests of session module"""

import pytest

from rasterio.session import DummySession, AWSSession, Session, OSSSession, GSSession


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


def test_requester_pays():
    """GDAL is configured with requester pays"""
    sesh = AWSSession(aws_access_key_id='foo', aws_secret_access_key='bar', requester_pays=True)
    assert sesh._session
    assert sesh.get_credential_options()['AWS_REQUEST_PAYER'] == 'requester'


def test_oss_session_class():
    """OSSSession works"""
    oss_session = OSSSession(
        oss_access_key_id='foo', 
        oss_secret_access_key='bar', 
        oss_endpoint='null-island-1')
    assert oss_session._creds
    assert oss_session.get_credential_options()['OSS_ACCESS_KEY_ID'] == 'foo'
    assert oss_session.get_credential_options()['OSS_SECRET_ACCESS_KEY'] == 'bar'


def test_session_factory_oss_kwargs():
    """Get an OSSSession for oss:// paths with keywords"""
    sesh = Session.from_path("oss://lol/wut", oss_access_key_id='foo', oss_secret_access_key='bar')
    assert isinstance(sesh, OSSSession)
    assert sesh.get_credential_options()['OSS_ACCESS_KEY_ID'] == 'foo'
    assert sesh.get_credential_options()['OSS_SECRET_ACCESS_KEY'] == 'bar'

def test_gs_session_class():
    """GSSession works"""
    gs_session = GSSession(
        google_application_credentials='foo')
    assert gs_session._creds
    assert gs_session.get_credential_options()['GOOGLE_APPLICATION_CREDENTIALS'] == 'foo'

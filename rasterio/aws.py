"""Amazon Web Service sessions and S3 raster access.

Reuses concepts from awscli and boto including environment variable
names and the .aws/config and /.aws/credentials files.

Raster datasets on S3 may be accessed using ``aws.Session.open()``

    from rasterio.aws import Session

    with Session().open('s3://bucket/foo.tif') as src:
        ...

or by calling ``rasterio.open()`` from within a session block

    with Session() as sess:
        with rasterio.open('s3://bucket/foo.tif') as src:
            ...
"""

import boto3

from rasterio._drivers import ConfigEnv
from rasterio.five import string_types


class Session(ConfigEnv):
    """A credentialed AWS S3 raster access session."""

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 aws_session_token=None, region_name=None, profile_name=None,
                 **options):
        self._session = boto3.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=region_name,
            profile_name=profile_name)
        self._creds = self._session._session.get_credentials()
        self.options = options.copy()
        if self._creds.access_key:
            self.options['AWS_ACCESS_KEY_ID'] = self._creds.access_key
        if self._creds.secret_key:
            self.options['AWS_SECRET_ACCESS_KEY'] = self._creds.secret_key
        if self._creds.token:
            self.options['AWS_SESSION_TOKEN'] = self._creds.token
        if self._session.region_name:
            self.options['AWS_REGION'] = self._session.region_name
        self.prev_options = {}

    def open(self, path, mode='r'):
        """Read-only access to rasters on S3."""
        if not isinstance(path, string_types):
            raise TypeError("invalid path: %r" % path)
        if mode == 'r-':
            from rasterio._base import DatasetReader
            s = DatasetReader(path, options=self.options)
        else:
            from rasterio._io import RasterReader
            s = RasterReader(path, options=self.options)
        s.start()
        return s

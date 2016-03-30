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

import os

from rasterio._drivers import ConfigEnv
from rasterio.five import configparser, string_types


class Session(ConfigEnv):
    """An authenticated AWS S3 raster access session."""

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 aws_session_token=None, region_name=None,
                 config_dir='~/.aws', profile=None, **options):
        # Set GDAL config options for AWS. Precedence order:
        # 1. Constructor args.
        # 2. Well-known environment variables.
        # 3. Config files in ~/.aws/
        defaults = {
            'aws_access_key_id': '',
            'aws_secret_access_key': '',
            'aws_session_token': '',
            'region': 'us-east-1'}
        section = profile or 'default'
        parser = configparser.ConfigParser(defaults)
        parser.read(
            os.path.join(os.path.expanduser(config_dir), 'credentials'))
        self.aws_access_key_id = (
            aws_access_key_id or
            os.environ.get('AWS_ACCESS_KEY_ID') or
            parser.get(section, 'aws_access_key_id'))
        self.aws_secret_access_key = (
            aws_secret_access_key or
            os.environ.get('AWS_SECRET_ACCESS_KEY') or
            parser.get(section, 'aws_secret_access_key'))
        self.aws_session_token = (
            aws_session_token or
            os.environ.get('AWS_SESSION_TOKEN') or
            parser.get(section, 'aws_session_token'))

        parser.read(
            os.path.join(os.path.expanduser(config_dir), 'config'))
        self.region_name = region_name or parser.get(section, 'region')

        self.options = options.copy()
        if self.aws_access_key_id:
            self.options['AWS_ACCESS_KEY_ID'] = self.aws_access_key_id
        if self.aws_secret_access_key:
            self.options['AWS_SECRET_ACCESS_KEY'] = self.aws_secret_access_key
        if self.aws_session_token:
            self.options['AWS_SESSION_TOKEN'] = self.aws_session_token
        if self.region_name:
            self.options['AWS_REGION'] = self.region_name
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

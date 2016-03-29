import os

from rasterio._drivers import ConfigEnv
from rasterio.five import configparser, string_types


class Session(ConfigEnv):

    def __init__(self, aws_access_key_id=None, aws_secret_access_key=None,
                 aws_session_token=None, region_name=None,
                 config_dir='~/.aws', **options):
        # Set GDAL config options for AWS. Precedence order:
        # 1. Constructor args.
        # 2. Well-known environment variables.
        # 3. Config files in ~/.aws/
        rv = {}
        parser = configparser.ConfigParser()
        parser.read(os.path.abspath(os.path.join(config_dir, 'credentials')))
        for section in parser.sections():
            for key, value in parser.items(section):
                rv['{0}.{1}'.format(section, key)] = value
        parser.read(os.path.abspath(os.path.join(config_dir, 'config')))
        for section in parser.sections():
            for key, value in parser.items(section):
                rv['{0}.{1}'.format(section, key)] = value

        self.aws_access_key_id = (aws_access_key_id or
                                  os.environ.get('AWS_ACCESS_KEY_ID') or
                                  rv.get('default.aws_access_key_id'))
        self.aws_secret_access_key = (aws_secret_access_key or
                                      os.environ.get('AWS_SECRET_ACCESS_KEY') or
                                      rv.get('default.aws_secret_access_key'))
        self.aws_session_token = (aws_session_token or
                                  os.environ.get('AWS_SESSION_TOKEN') or
                                  rv.get('default.aws_session_token'))
        self.region_name = (region_name or rv.get('default.region') or
                            'us-east-1')
        self.options = options.copy()
        self.options['AWS_ACCESS_KEY_ID'] = self.aws_access_key_id
        self.options['AWS_SECRET_ACCESS_KEY'] = self.aws_secret_access_key
        self.options['AWS_SESSION_TOKEN'] = self.aws_session_token
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

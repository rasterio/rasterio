"""Rasterio's GDAL/AWS environment"""

import logging

from rasterio._drivers import GDALEnv
from rasterio.dtypes import check_dtype
from rasterio.errors import EnvError
from rasterio.five import string_types
from rasterio.transform import guard_transform
from rasterio.vfs import parse_path, vsi_path


# The currently active GDAL/AWS environment is a private attribute.
_env = None

log = logging.getLogger(__name__)


class Env(GDALEnv):
    """Abstraction for GDAL and AWS configuration

    The GDAL library is stateful: it has a registry of format drivers,
    an error stack, and dozens of configuration options.

    Rasterio's approach to working with GDAL is to wrap all the state
    up using a Python context manager (see PEP 343,
    https://www.python.org/dev/peps/pep-0343/). When the context is
    entered GDAL drivers are registered, error handlers are
    configured, and configuration options are set. When the context
    is exited, drivers are removed from the registry and other
    configurations are removed.

    Example:

        with Env(GDAL_CACHEMAX=512) as env:
            # All drivers are registered, GDAL's raster block cache
            # size is set to 512MB.
            # Commence processing...
            ...
            # End of processing.

        # At this point, configuration options are set to their
        # previous (possible unset) values.

    A boto3 session or boto3 session constructor arguments
    `aws_access_key_id`, `aws_secret_access_key`, `aws_session_token`
    may be passed to Env's constructor. In the latter case, a session
    will be created as soon as needed. AWS credentials are configured
    for GDAL as needed.
    """

    def __init__(self, aws_session=None, **options):
        """Create a new GDAL/AWS environment.

        Note: this class is a context manager. GDAL isn't configured
        until the context is entered via `with Env():`

        Parameters
        ----------
        aws_session: object, optional
            A boto3 session.
        **options: optional
            A mapping of boto3 session constructor keyword arguments
            and GDAL configuration options.

        Returns
        -------
        A new instance of Env.
        """
        global _env
        if _env and _env.managing:
            raise EnvError("GDAL is currently configured. "
                           "Multiple configuration is not allowed.")
        super(Env, self).__init__(**options)
        self.aws_session = aws_session
        self._creds = (
            self.aws_session._session.get_credentials()
            if self.aws_session else None)
        self.start()
        self.managing = False
        _env = self

    def get_aws_credentials(self):
        """Get credentials and configure GDAL."""
        import boto3
        self.aws_session = boto3.Session(
            aws_access_key_id=self.options.get('aws_access_key_id'),
            aws_secret_access_key=self.options.get('aws_secret_access_key'),
            aws_session_token=self.options.get('aws_session_token'),
            region_name=self.options.get('region_name'),
            profile_name=self.options.get('profile_name'))
        self._creds = self.aws_session._session.get_credentials()

        # Pass these credentials to the GDAL environment.
        options = {}
        if self._creds.access_key:  # pragma: no branch
            options.update(AWS_ACCESS_KEY_ID=self._creds.access_key)
        if self._creds.secret_key:  # pragma: no branch
            options.update(AWS_SECRET_ACCESS_KEY=self._creds.secret_key)
        if self._creds.token:
            options.update(AWS_SESSION_TOKEN=self._creds.token)
        if self.aws_session.region_name:
            options.update(AWS_REGION=self.aws_session.region_name)
        self.update_config_options(**options)

    def __enter__(self):
        self.enter_config_options()
        self.managing = True
        log.debug("Entering env %r context", self)
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        global _env
        self.exit_config_options()
        self.stop()
        self.managing = False
        _env = None
        log.debug("Exiting env %r context", self)


def setenv():
    """Assert that there is a GDAL environment, creating it if needed

    This is the function to be called by methods like `rasterio.open()`
    that need a default environment.
    """
    global _env
    if not _env:
        _env = Env()
        log.debug("New GDAL environment created %r", _env)

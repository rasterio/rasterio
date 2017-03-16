"""Rasterio's GDAL/AWS environment"""

from functools import wraps
import itertools as it
import logging

from rasterio._env import (
    GDALEnv, del_gdal_config, get_gdal_config, set_gdal_config)
from rasterio.dtypes import check_dtype
from rasterio.errors import EnvError
from rasterio.compat import string_types
from rasterio.transform import guard_transform
from rasterio.vfs import parse_path, vsi_path
import threading

# The currently active GDAL/AWS environment is a private attribute.
class ThreadEnv(threading.local):
    def __init__(self):
        self._env = None # Initialises in each thread
local = ThreadEnv()


# When the outermost 'rasterio.Env()' executes '__enter__' it probes the
# GDAL environment to see if any of the supplied config options already
# exist, the assumption being that they were set with
# 'osgeo.gdal.SetConfigOption()' or possibly 'rasterio.env.set_gdal_config()'.
# The discovered options are reinstated when the outermost Rasterio environment
# exits.  Without this check any environment options that are present in the
# GDAL environment and are also passed to 'rasterio.Env()' will be unset
# when 'rasterio.Env()' tears down, regardless of their value.  For example:
#
#   from osgeo import gdal
#   import rasterio
#
#   gdal.SetConfigOption('key', 'value')
#   with rasterio.Env(key='something'):
#       pass
#
# The config option 'key' would be unset when 'Env()' exits.  A more
# comprehensive solution would also leverage https://trac.osgeo.org/gdal/changeset/37273
# but this gets Rasterio + older versions of GDAL halfway there.  One major
# assumption is that environment variables are not set directly with
# 'osgeo.gdal.SetConfigOption()' OR 'rasterio.env.set_gdal_config()' inside
# of a 'rasterio.Env()'.
_discovered_options = None


log = logging.getLogger(__name__)

# Rasterio defaults
default_options = {
    'CHECK_WITH_INVERT_PROJ': True,
    'GTIFF_IMPLICIT_JPEG_OVR': False,
    "I'M_ON_RASTERIO": True
}

class Env(object):
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

        with rasterio.Env(GDAL_CACHEMAX=512) as env:
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

    def __init__(self, aws_session=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None,
                 region_name=None, profile_name=None, **options):
        """Create a new GDAL/AWS environment.

        Note: this class is a context manager. GDAL isn't configured
        until the context is entered via `with rasterio.Env():`

        Parameters
        ----------
        aws_session: object, optional
            A boto3 session.
        aws_access_key_id: string, optional
            An access key id, as per boto3.
        aws_secret_access_key: string, optional
            A secret access key, as per boto3.
        aws_session_token: string, optional
            A session token, as per boto3.
        region_name: string, optional
            A region name, as per boto3.
        profile_name: string, optional
            A shared credentials profile name, as per boto3.
        **options: optional
            A mapping of GDAL configuration options, e.g.,
            `CPL_DEBUG=True, CHECK_WITH_INVERT_PROJ=False`.

        Returns
        -------
        A new instance of Env.

        Note: We raise EnvError if the GDAL config options
        AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY are given. AWS
        credentials are handled exclusively by boto3.
        """
        if ('AWS_ACCESS_KEY_ID' in options or
                'AWS_SECRET_ACCESS_KEY' in options):
            raise EnvError(
                "GDAL's AWS config options can not be directly set. "
                "AWS credentials are handled exclusively by boto3.")
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.aws_session_token = aws_session_token
        self.region_name = region_name
        self.profile_name = profile_name
        self.aws_session = aws_session
        self._creds = (
            self.aws_session._session.get_credentials()
            if self.aws_session else None)
        self.options = options.copy()
        self.context_options = {}

    def get_aws_credentials(self):
        """Get credentials and configure GDAL."""
        import boto3
        options = {}
        if not self.aws_session:
            self.aws_session = boto3.Session(
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                aws_session_token=self.aws_session_token,
                region_name=self.region_name,
                profile_name=self.profile_name)
        self._creds = self.aws_session._session.get_credentials()

        # Pass these credentials to the GDAL environment.
        if self._creds.access_key:  # pragma: no branch
            options.update(aws_access_key_id=self._creds.access_key)
        if self._creds.secret_key:  # pragma: no branch
            options.update(aws_secret_access_key=self._creds.secret_key)
        if self._creds.token:
            options.update(aws_session_token=self._creds.token)
        if self.aws_session.region_name:
            options.update(aws_region=self.aws_session.region_name)

        # Pass these credentials to the GDAL environment.
        local._env.update_config_options(**options)

    def drivers(self):
        """Return a mapping of registered drivers."""
        return local._env.drivers()

    def __enter__(self):
        global _discovered_options
        log.debug("Entering env context: %r", self)

        # No parent Rasterio environment exists.
        if local._env is None:
            logging.debug("Starting outermost env")
            self._has_parent_env = False

            # See note directly above where _discovered_options is globally
            # defined.  This MUST happen before calling 'defenv()'.
            _discovered_options = {}
            # Don't want to reinstate the "I'M_ON_RASTERIO" option.
            probe_env = {k for k in default_options if k != "I'M_ON_RASTERIO"}
            probe_env |= set(self.options.keys())
            for key in probe_env:
                val = get_gdal_config(key, normalize=False)
                if val is not None:
                    _discovered_options[key] = val
                    logging.debug("Discovered option: %s=%s", key, val)

            defenv()
            self.context_options = {}
        else:
            self._has_parent_env = True
            self.context_options = getenv()
        setenv(**self.options)
        log.debug("Entered env context: %r", self)
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        global _discovered_options
        log.debug("Exiting env context: %r", self)
        delenv()
        if self._has_parent_env:
            defenv()
            setenv(**self.context_options)
        else:
            logging.debug("Exiting outermost env")
            # See note directly above where _discovered_options is globally
            # defined.
            while _discovered_options:
                key, val = _discovered_options.popitem()
                set_gdal_config(key, val, normalize=False)
                logging.debug(
                    "Set discovered option back to: '%s=%s", key, val)
            _discovered_options = None
        log.debug("Exited env context: %r", self)


def defenv():
    """Create a default environment if necessary."""
    if local._env:
        log.debug("GDAL environment exists: %r", local._env)
    else:
        log.debug("No GDAL environment exists")
        local._env = GDALEnv()
        local._env.update_config_options(**default_options)
        log.debug(
            "New GDAL environment %r created", local._env)
    local._env.start()


def getenv():
    """Get a mapping of current options."""
    if not local._env:
        raise EnvError("No GDAL environment exists")
    else:
        log.debug("Got a copy of environment %r options", local._env)
        return local._env.options.copy()


def setenv(**options):
    """Set options in the existing environment."""
    if not local._env:
        raise EnvError("No GDAL environment exists")
    else:
        local._env.update_config_options(**options)
        log.debug("Updated existing %r with options %r", local._env, options)


def delenv():
    """Delete options in the existing environment."""
    if not local._env:
        raise EnvError("No GDAL environment exists")
    else:
        local._env.clear_config_options()
        log.debug("Cleared existing %r options", local._env)
    local._env.stop()
    local._env = None


def ensure_env(f):
    """A decorator that ensures an env exists before a function
    calls any GDAL C functions."""
    @wraps(f)
    def wrapper(*args, **kwds):
        with Env(WITH_RASTERIO_ENV=True):
            return f(*args, **kwds)
    return wrapper

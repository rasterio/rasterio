"""Rasterio's GDAL/AWS environment"""

from functools import wraps
import logging
import threading

import rasterio
from rasterio._env import (
    GDALEnv, del_gdal_config, get_gdal_config, set_gdal_config)
from rasterio.compat import string_types
from rasterio.dtypes import check_dtype
from rasterio.errors import EnvError
from rasterio.transform import guard_transform
from rasterio.vfs import parse_path, vsi_path


class ThreadEnv(threading.local):
    def __init__(self):
        self._env = None  # Initialises in each thread

        # When the outermost 'rasterio.Env()' executes '__enter__' it
        # probes the GDAL environment to see if any of the supplied
        # config options already exist, the assumption being that they
        # were set with 'osgeo.gdal.SetConfigOption()' or possibly
        # 'rasterio.env.set_gdal_config()'.  The discovered options are
        # reinstated when the outermost Rasterio environment exits.
        # Without this check any environment options that are present in
        # the GDAL environment and are also passed to 'rasterio.Env()'
        # will be unset when 'rasterio.Env()' tears down, regardless of
        # their value.  For example:
        #
        #   from osgeo import gdal import rasterio
        #
        #   gdal.SetConfigOption('key', 'value') with
        #   rasterio.Env(key='something'): pass
        #
        # The config option 'key' would be unset when 'Env()' exits.
        # A more comprehensive solution would also leverage
        # https://trac.osgeo.org/gdal/changeset/37273 but this gets
        # Rasterio + older versions of GDAL halfway there.  One major
        # assumption is that environment variables are not set directly
        # with 'osgeo.gdal.SetConfigOption()' OR
        # 'rasterio.env.set_gdal_config()' inside of a 'rasterio.Env()'.
        self._discovered_options = None


local = ThreadEnv()

log = logging.getLogger(__name__)

# Rasterio defaults
default_options = {
    'CHECK_WITH_INVERT_PROJ': True,
    'GTIFF_IMPLICIT_JPEG_OVR': False,
    "RASTERIO_ENV": True
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

    def __init__(self, session=None, aws_access_key_id=None,
                 aws_secret_access_key=None, aws_session_token=None,
                 region_name=None, profile_name=None, **options):
        """Create a new GDAL/AWS environment.

        Note: this class is a context manager. GDAL isn't configured
        until the context is entered via `with rasterio.Env():`

        Parameters
        ----------
        session: object, optional
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
        self.session = session

        self.options = options.copy()
        self.context_options = {}

        self._creds = None

    @property
    def is_credentialized(self):
        return bool(self._creds)

    def credentialize(self):
        """Get credentials and configure GDAL

        Note well: this method is a no-op if the GDAL environment
        already has credentials, unless session is not None.
        """
        if not hascreds():
            import boto3
            if not self.session and not self.aws_access_key_id and not self.profile_name:
                self.session = boto3.Session()
            elif not self.session:
                self.session = boto3.Session(
                    aws_access_key_id=self.aws_access_key_id,
                    aws_secret_access_key=self.aws_secret_access_key,
                    aws_session_token=self.aws_session_token,
                    region_name=self.region_name,
                    profile_name=self.profile_name)
            else:
                # use self.session
                pass
            self._creds = self.session._session.get_credentials()

            # Pass these credentials to the GDAL environment.
            cred_opts = {}
            if self._creds.access_key:  # pragma: no branch
                cred_opts['AWS_ACCESS_KEY_ID'] = self._creds.access_key
            if self._creds.secret_key:  # pragma: no branch
                cred_opts['AWS_SECRET_ACCESS_KEY'] = self._creds.secret_key
            if self._creds.token:
                cred_opts['AWS_SESSION_TOKEN'] = self._creds.token
            if self.session.region_name:
                cred_opts['AWS_REGION'] = self.session.region_name
            self.options.update(**cred_opts)
            setenv(**cred_opts)

    def can_credentialize_on_enter(self):
        return bool(self.session or self.aws_access_key_id or self.profile_name)

    def drivers(self):
        """Return a mapping of registered drivers."""
        return local._env.drivers()

    def __enter__(self):
        log.debug("Entering env context: %r", self)
        # No parent Rasterio environment exists.
        if local._env is None:
            log.debug("Starting outermost env")
            self._has_parent_env = False

            # See note directly above where _discovered_options is globally
            # defined.  This MUST happen before calling 'defenv()'.
            local._discovered_options = {}
            # Don't want to reinstate the "RASTERIO_ENV" option.
            probe_env = {k for k in default_options if k != "RASTERIO_ENV"}
            probe_env |= set(self.options.keys())
            for key in probe_env:
                val = get_gdal_config(key, normalize=False)
                if val is not None:
                    local._discovered_options[key] = val
                    log.debug("Discovered option: %s=%s", key, val)

            defenv(**self.options)
            self.context_options = {}
        else:
            self._has_parent_env = True
            self.context_options = getenv()
            setenv(**self.options)

        if self.can_credentialize_on_enter():
            self.credentialize()

        log.debug("Entered env context: %r", self)
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        log.debug("Exiting env context: %r", self)
        delenv()
        if self._has_parent_env:
            defenv()
            setenv(**self.context_options)
        else:
            log.debug("Exiting outermost env")
            # See note directly above where _discovered_options is globally
            # defined.
            while local._discovered_options:
                key, val = local._discovered_options.popitem()
                set_gdal_config(key, val, normalize=False)
                log.debug(
                    "Set discovered option back to: '%s=%s", key, val)
            local._discovered_options = None
        log.debug("Exited env context: %r", self)


def defenv(**options):
    """Create a default environment if necessary."""
    if local._env:
        log.debug("GDAL environment exists: %r", local._env)
    else:
        log.debug("No GDAL environment exists")
        local._env = GDALEnv()
        # first set default options, then add user options
        set_options = {}
        for d in (default_options, options):
            for (k, v) in d.items():
                set_options[k] = v
        local._env.update_config_options(**set_options)
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


def hasenv():
    return bool(local._env)


def setenv(**options):
    """Set options in the existing environment."""
    if not local._env:
        raise EnvError("No GDAL environment exists")
    else:
        local._env.update_config_options(**options)
        log.debug("Updated existing %r with options %r", local._env, options)


def hascreds():
    gdal_config = local._env.get_config_options()
    return bool('AWS_ACCESS_KEY_ID' in gdal_config and
                'AWS_SECRET_ACCESS_KEY' in gdal_config)


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
    if local._env:
        return f
    else:
        @wraps(f)
        def wrapper(*args, **kwds):
            with Env():
                return f(*args, **kwds)
        return wrapper

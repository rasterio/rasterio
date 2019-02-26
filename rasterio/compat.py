"""Python 2-3 compatibility."""

import itertools
import sys


if sys.version_info[0] >= 3:   # pragma: no cover
    string_types = str,
    text_type = str
    integer_types = int,
    zip_longest = itertools.zip_longest
    import configparser
    from urllib.parse import urlparse
    from collections import UserDict
    from inspect import getfullargspec as getargspec
    from unittest import mock
else:  # pragma: no cover
    string_types = basestring,
    text_type = unicode
    integer_types = int, long
    zip_longest = itertools.izip_longest
    import ConfigParser as configparser
    from urlparse import urlparse
    from UserDict import UserDict
    from inspect import getargspec
    import mock

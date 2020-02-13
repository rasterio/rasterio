"""Python 2-3 compatibility."""

import itertools
import sys
import warnings


if sys.version_info[0] >= 3:   # pragma: no cover
    string_types = str,
    text_type = str
    integer_types = int,
    zip_longest = itertools.zip_longest
    import configparser
    from urllib.parse import urlparse
    from collections import UserDict
    from collections.abc import Iterable, Mapping
    from inspect import getfullargspec as getargspec
    from pathlib import Path

else:  # pragma: no cover
    warnings.warn("Python 2 compatibility will be removed after version 1.1", DeprecationWarning)
    string_types = basestring,
    text_type = unicode
    integer_types = int, long
    zip_longest = itertools.izip_longest
    import ConfigParser as configparser
    from urlparse import urlparse
    from UserDict import UserDict
    from inspect import getargspec
    from collections import Iterable, Mapping

# Users can pass in objects that subclass a few different objects
# More specifically, rasterio has a CRS() class that subclasses UserDict()
# In Python 2 UserDict() is in its own module and does not subclass Mapping()
DICT_TYPES = (dict, Mapping, UserDict)

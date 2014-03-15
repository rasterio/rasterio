# Python 2-3 compatibility

import sys
if sys.version_info[0] >= 3:
    string_types = str,
    text_type = str
    integer_types = int,
else:
    string_types = basestring,
    text_type = unicode
    integer_types = int, long

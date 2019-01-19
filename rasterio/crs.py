"""Coordinate Reference Systems

Notes
-----

In Rasterio versions <= 1.0.13, coordinate reference system support was limited
to the CRS that can be described by PROJ parameters. This limitation is gone in
versions >= 1.0.14. Any CRS that can be defined using WKT (version 1) may be
used.

"""

import collections
import json

from rasterio._crs import _CRS, all_proj_keys
from rasterio.compat import string_types
from rasterio.errors import CRSError


class CRS(_CRS, collections.Mapping):
    """A geographic or projected coordinate reference system

    CRS objects may be created by passing PROJ parameters as keyword
    arguments to the standard constructor or by passing EPSG codes, PROJ
    mappings, PROJ strings, or WKT strings to the from_epsg, from_dict,
    from_string, or from_wkt class methods or static methods.

    Examples
    --------

    The from_dict method takes PROJ parameters as keyword arguments.

    >>> crs = CRS.from_dict(init='epsg:3005')

    EPSG codes may be used with the from_epsg method.

    >>> crs = CRS.from_epsg(3005)

    The from_string method takes a variety of input.

    >>> crs = CRS.from_string('EPSG:3005')

    """
    def __init__(self, initialdata=None, morph_from_esri_dialect=False, **kwargs):
        """Make a CRS from a PROJ dict or mapping

        Parameters
        ----------
        initialdata : projection string or mapping, optional
            A projection string (WKT, PROJ.4), a dictionary or other mapping
        morph_from_esri_dialect : bool, optional
            If True, items in the input using Esri's dialect of WKT
            will be replaced by OGC standard equivalents.
       kwargs : mapping, optional
            Another mapping. Will be overlaid on the initialdata.

        Returns
        -------
        CRS

        """
        self._wkt = None
        self._data = None

        proj = ""
        if isinstance(initialdata, string_types):
            proj = initialdata
        elif initialdata or kwargs:

            data = dict(initialdata or {})
            data.update(**kwargs)
            data = {k: v for k, v in data.items() if k in all_proj_keys}

            # always use lowercase 'epsg'.
            if 'init' in data:
                data['init'] = data['init'].replace('EPSG:', 'epsg:')

            proj = ' '.join(['+{}={}'.format(key, val) for key, val in data.items()])

        super(CRS, self).__init__(proj, morph_from_esri_dialect=morph_from_esri_dialect)

    def __getitem__(self, item):
        return self.data[item]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __bool__(self):
        return bool(self.wkt)

    __nonzero__ = __bool__

    def __eq__(self, other):
        other = CRS.from_user_input(other)
        return super(CRS, self).__eq__(other)

    def to_proj4(self):
        """Convert CRS to a PROJ4 string

        Returns
        -------
        str

        """
        return ' '.join(['+{}={}'.format(key, val) for key, val in self.data.items()])

    @property
    def wkt(self):
        """An OGC WKT representation of the CRS

        Returns
        -------
        str

        """
        if not self._wkt:
            self._wkt = self.to_wkt()
        return self._wkt

    @property
    def data(self):
        """A PROJ4 dict representation of the CRS"""
        if not self._data:
            self._data = self.to_dict()
        return self._data

    @property
    def is_valid(self):
        """Test that the CRS is a geographic or projected CRS

        Notes
        -----
        There are other types of CRS, such as compound or local or
        engineering CRS, but these are not supported in Rasterio 1.0.

        Returns
        -------
        bool

        """
        return self.is_geographic or self.is_projected

    @property
    def is_epsg_code(self):
        """Test if the CRS is defined by an EPSG code

        Returns
        -------
        bool

        """
        try:
            return bool(self.to_epsg())
        except CRSError:
            return False

    def to_string(self):
        """Convert CRS to a PROJ4 or WKT string

        Notes
        -----

        Mapping keys are tested against the ``all_proj_keys`` list.
        Values of ``True`` are omitted, leaving the key bare:
        {'no_defs': True} -> "+no_defs" and items where the value is
        otherwise not a str, int, or float are omitted.

        Returns
        -------
        str

        """
        epsg_code = self.to_epsg()
        if epsg_code:
            return 'EPSG:{}'.format(epsg_code)
        else:
            return self.to_wkt() or self.to_proj4()

    __str__ = to_string

    def __repr__(self):
        epsg_code = self.to_epsg()
        if epsg_code:
            return "CRS.from_dict(init='epsg:{}')".format(epsg_code)
        else:
            return "CRS.from_wkt('{}')".format(self.wkt)

    @classmethod
    def from_string(cls, string, morph_from_esri_dialect=False):
        """Make a CRS from an EPSG, PROJ, or WKT string

        Parameters
        ----------
        string : str
            An EPSG, PROJ, or WKT string.
        morph_from_esri_dialect : bool, optional
            If True, items in the input using Esri's dialect of WKT
            will be replaced by OGC standard equivalents.

        Returns
        -------
        CRS

        """
        if not string:
            raise CRSError("CRS is empty or invalid: {!r}".format(string))

        elif string.strip().upper().startswith('EPSG:'):
            auth, val = string.strip().split(':')
            if not val:
                raise CRSError("Invalid CRS: {!r}".format(string))
            return cls.from_epsg(val)

        elif string.startswith('{') or string.startswith('['):
            # may be json, try to decode it
            try:
                val = json.loads(string, strict=False)
            except ValueError:
                raise CRSError('CRS appears to be JSON but is not valid')

            if not val:
                raise CRSError("CRS is empty JSON")
            else:
                return cls.from_dict(**val)

        elif '+' in string and '=' in string:
            return cls.from_proj4(string)

        else:
            return cls.from_wkt(string, morph_from_esri_dialect=morph_from_esri_dialect)

    @classmethod
    def from_user_input(cls, value, morph_from_esri_dialect=False):
        """Make a CRS from various input

        Dispatches to from_epsg, from_proj, or from_string

        Parameters
        ----------
        value : obj
            A Python int, dict, or str.
        morph_from_esri_dialect : bool, optional
            If True, items in the input using Esri's dialect of WKT
            will be replaced by OGC standard equivalents.

        Returns
        -------
        CRS

        """
        if isinstance(value, cls):
            return value
        elif isinstance(value, int):
            return cls.from_epsg(value)
        elif isinstance(value, dict):
            return cls(**value)
        elif isinstance(value, string_types):
            return cls.from_string(value, morph_from_esri_dialect=morph_from_esri_dialect)
        else:
            raise CRSError("CRS is invalid: {!r}".format(value))

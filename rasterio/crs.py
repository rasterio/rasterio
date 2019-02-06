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


class CRS(collections.Mapping):
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
    def __init__(self, initialdata=None, **kwargs):
        """Make a CRS from a PROJ dict or mapping

        Parameters
        ----------
        initialdata : mapping, optional
            A dictionary or other mapping
        kwargs : mapping, optional
            Another mapping. Will be overlaid on the initialdata.

        Returns
        -------
        CRS

        """
        self._wkt = None
        self._data = None
        self._crs = None

        if initialdata or kwargs:

            data = dict(initialdata or {})
            data.update(**kwargs)
            data = {k: v for k, v in data.items() if k in all_proj_keys}

            # always use lowercase 'epsg'.
            if 'init' in data:
                data['init'] = data['init'].replace('EPSG:', 'epsg:')

            proj_parts = []

            for key, val in data.items():
                if val is False or None:
                    continue
                elif val is True:
                    proj_parts.append('+{}'.format(key))
                else:
                    proj_parts.append('+{}={}'.format(key, val))

            proj = ' '.join(proj_parts)
            self._crs = _CRS.from_proj4(proj)

        else:
            self._crs = _CRS()

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
        return (self._crs == other._crs)

    def to_proj4(self):
        """Convert CRS to a PROJ4 string

        Returns
        -------
        str

        """
        return ' '.join(['+{}={}'.format(key, val) for key, val in self.data.items()])

    def to_wkt(self, morph_to_esri_dialect=False):
        """Convert CRS to its OGC WKT representation

        Parameters
        ----------
        morph_to_esri_dialect : bool, optional
            Whether or not to morph to the Esri dialect of WKT

        Returns
        -------
        str

        """
        return self._crs.to_wkt(morph_to_esri_dialect=morph_to_esri_dialect)

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

    def to_epsg(self):
        """The epsg code of the CRS

        Returns None if there is no corresponding EPSG code.

        Returns
        -------
        int

        """
        return self._crs.to_epsg()

    def to_dict(self):
        """Convert CRS to a PROJ4 dict

        Notes
        -----
        If there is a corresponding EPSG code, it will be used.

        Returns
        -------
        dict

        """
        if self._crs is None:
            raise CRSError("Undefined CRS has no dict representation")

        else:
            epsg_code = self.to_epsg()
            if epsg_code:
                return {'init': 'epsg:{}'.format(epsg_code)}
            else:
                try:
                    return self._crs.to_dict()
                except CRSError:
                    return {}

    @property
    def data(self):
        """A PROJ4 dict representation of the CRS"""
        if not self._data:
            self._data = self.to_dict()
        return self._data

    @property
    def is_geographic(self):
        """Test that the CRS is a geographic CRS

        Returns
        -------
        bool

        """
        return self._crs.is_geographic

    @property
    def is_projected(self):
        """Test that the CRS is a projected CRS

        Returns
        -------
        bool

        """
        return self._crs.is_projected

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
    def from_epsg(cls, code):
        """Make a CRS from an EPSG code

        Parameters
        ----------
        code : int or str
            An EPSG code. Strings will be converted to integers.

        Notes
        -----
        The input code is not validated against an EPSG database.

        Returns
        -------
        CRS

        """
        obj = cls()
        obj._crs = _CRS.from_epsg(code)
        return obj

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
    def from_proj4(cls, proj):
        """Make a CRS from a PROJ4 string

        Parameters
        ----------
        proj : str
            A PROJ4 string like "+proj=longlat ..."

        Returns
        -------
        CRS

        """
        obj = cls()
        obj._crs = _CRS.from_proj4(proj)
        return obj

    @classmethod
    def from_dict(cls, initialdata=None, **kwargs):
        """Make a CRS from a PROJ dict

        Parameters
        ----------
        initialdata : mapping, optional
            A dictionary or other mapping
        kwargs : mapping, optional
            Another mapping. Will be overlaid on the initialdata.

        Returns
        -------
        CRS

        """
        obj = cls()
        obj._crs = _CRS.from_dict(initialdata, **kwargs)
        return obj

    @classmethod
    def from_wkt(cls, wkt, morph_from_esri_dialect=False):
        """Make a CRS from a WKT string

        Parameters
        ----------
        wkt : str
            A WKT string.
        morph_from_esri_dialect : bool, optional
            If True, items in the input using Esri's dialect of WKT
            will be replaced by OGC standard equivalents.

        Returns
        -------
        CRS

        """
        obj = cls()
        obj._crs = _CRS.from_wkt(wkt, morph_from_esri_dialect=morph_from_esri_dialect)
        return obj

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
            obj = cls()
            obj._crs = _CRS.from_user_input(value, morph_from_esri_dialect=morph_from_esri_dialect)
            return obj
        else:
            raise CRSError("CRS is invalid: {!r}".format(value))

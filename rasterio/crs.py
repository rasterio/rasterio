"""Coordinate Reference Systems

Notes
-----

In Rasterio versions <= 1.0.13, coordinate reference system support was limited
to the CRS that can be described by PROJ parameters. This limitation is gone in
versions >= 1.0.14. Any CRS that can be defined using WKT (version 1) may be
used.

"""

from collections.abc import Mapping
import json
import pickle

import rasterio._loading
with rasterio._loading.add_gdal_dll_directories():
    from rasterio._crs import _CRS, all_proj_keys, _epsg_treats_as_latlong, _epsg_treats_as_northingeasting
    from rasterio.errors import CRSError


class CRS(Mapping):
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
            self._crs = _CRS.from_dict(data)

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
        try:
            other = CRS.from_user_input(other)
        except CRSError:
            return False
        return (self._crs == other._crs)

    def __getstate__(self):
        return self.to_wkt()

    def __setstate__(self, state):
        self._wkt = None
        self._data = None
        self._crs = _CRS.from_wkt(state)

    def __copy__(self):
        return pickle.loads(pickle.dumps(self))

    def __hash__(self):
        return hash(self.to_wkt())

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

    def to_authority(self):
        """The authority name and code of the CRS

        .. versionadded:: 1.1.7

        Returns
        -------
        (str, str) or None

        """
        return self._crs.to_authority()

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

    @property
    def linear_units_factor(self):
        """The linear units of the CRS and the conversion factor to meters.

        The first element of the tuple is a string, its possible values
        include "metre" and "US survey foot".
        The second element of the tuple is a float that represent the conversion
        factor of the raster units to meters.

        Returns
        -------
        tuple

        """
        return self._crs.linear_units_factor

    @property
    def linear_units(self):
        """The linear units of the CRS

        Possible values include "metre" and "US survey foot".

        Returns
        -------
        str

        """
        return self._crs.linear_units

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
        auth = self.to_authority()
        if auth:
            return ":".join(auth)
        else:
            return self.to_wkt() or self.to_proj4()

    __str__ = to_string

    def __repr__(self):
        epsg_code = self.to_epsg()
        if epsg_code:
            return "CRS.from_epsg({})".format(epsg_code)
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
    def from_authority(cls, auth_name, code):
        """Make a CRS from an authority name and authority code

        .. versionadded:: 1.1.7

        Parameters
        ----------
        auth_name: str
            The name of the authority.
        code : int or str
            The code used by the authority.

        Returns
        -------
        CRS
        """
        return cls.from_string("{auth_name}:{code}".format(auth_name=auth_name, code=code))

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
        try:
            string = string.strip()
        except AttributeError:
            pass

        if not string:
            raise CRSError("CRS is empty or invalid: {!r}".format(string))

        elif string.upper().startswith('EPSG:'):
            auth, val = string.split(':')
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
        elif string.endswith("]"):
            return cls.from_wkt(string, morph_from_esri_dialect=morph_from_esri_dialect)
        elif "=" in string:
            return cls.from_proj4(string)

        obj = cls()
        obj._crs = _CRS.from_user_input(string, morph_from_esri_dialect=morph_from_esri_dialect)
        return obj

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
        elif hasattr(value, "to_wkt") and callable(value.to_wkt):
            return cls.from_wkt(
                value.to_wkt(),
                morph_from_esri_dialect=morph_from_esri_dialect,
            )
        elif isinstance(value, int):
            return cls.from_epsg(value)
        elif isinstance(value, dict):
            return cls(**value)
        elif isinstance(value, str):
            return cls.from_string(value, morph_from_esri_dialect=morph_from_esri_dialect)
        else:
            raise CRSError("CRS is invalid: {!r}".format(value))


def epsg_treats_as_latlong(input):
    """Test if the CRS is in latlon order

    From GDAL docs:

    > This method returns TRUE if EPSG feels this geographic coordinate
    system should be treated as having lat/long coordinate ordering.

    > Currently this returns TRUE for all geographic coordinate systems with
    an EPSG code set, and axes set defining it as lat, long.

    > FALSE will be returned for all coordinate systems that are not
    geographic, or that do not have an EPSG code set.

    > **Note**

    > Important change of behavior since GDAL 3.0.
    In previous versions, geographic CRS imported with importFromEPSG()
    would cause this method to return FALSE on them, whereas now it returns
    TRUE, since importFromEPSG() is now equivalent to importFromEPSGA().

    Parameters
    ----------
    input : CRS
        Coordinate reference system, as a rasterio CRS object
        Example: CRS({'init': 'EPSG:4326'})

    Returns
    -------
    bool

    """
    if not isinstance(input, CRS):
        input = CRS.from_user_input(input)

    return _epsg_treats_as_latlong(input._crs)


def epsg_treats_as_northingeasting(input):
    """Test if the CRS should be treated as having northing/easting coordinate ordering

    From GDAL docs:

    > This method returns TRUE if EPSG feels this projected coordinate
    system should be treated as having northing/easting coordinate ordering.

    > Currently this returns TRUE for all projected coordinate systems with
    an EPSG code set, and axes set defining it as northing, easting.

    > FALSE will be returned for all coordinate systems that are not
    projected, or that do not have an EPSG code set.

    > **Note**

    > Important change of behavior since GDAL 3.0.
    In previous versions, projected CRS with northing, easting axis order
    imported with importFromEPSG() would cause this method to return FALSE
    on them, whereas now it returns TRUE, since importFromEPSG() is now 
    equivalent to importFromEPSGA().

    Parameters
    ----------
    input : CRS
        Coordinate reference system, as a rasterio CRS object
        Example: CRS({'init': 'EPSG:4326'})

    Returns
    -------
    bool

    """
    if not isinstance(input, CRS):
        input = CRS.from_user_input(input)

    return _epsg_treats_as_northingeasting(input._crs)

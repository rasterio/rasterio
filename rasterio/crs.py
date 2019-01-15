"""Coordinate Reference Systems

Notes
-----

In Rasterio 1.0, coordinate reference system support is limited to the
CRS that can be described by PROJ parameters.

"""

from rasterio._crs import _CRS, all_proj_keys
from rasterio.compat import string_types


class CRS(_CRS):
    """A container class for coordinate reference system info

    CRS objects may be created by passing PROJ parameters as keyword
    arguments to the standard constructor or by passing EPSG codes,
    PROJ strings, or WKT strings to the from_epsg and from_string
    class methods.

    Examples
    --------

    The constructor takes PROJ parameters as keyword arguments.

    >>> crs = CRS(init='epsg:3005')

    EPSG codes may be used with the from_epsg class method.

    >>> crs = CRS.from_epsg(3005)

    """

    @property
    def is_valid(self):
        """Test if the CRS is a valid geographic or projected
        coordinate reference system

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
        """Turn CRS into a PROJ string

        Notes
        -----

        Mapping keys are tested against the ``all_proj_keys`` list. Values of
        ``True`` are omitted, leaving the key bare: {'no_defs': True} -> "+no_defs"
        and items where the value is otherwise not a str, int, or float are
        omitted.

        Returns
        -------
        str
        """
        return self._wkt_or_proj()

    __str__ = to_string

    def __repr__(self):
        if self._wkt:
            return "CRS.from_wkt('{}')".format(self._wkt)
        elif self._data:
            return "CRS({})".format(repr(self._data))
        else:
            return "CRS()"

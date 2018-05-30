"""Coordinate Reference Systems"""

from rasterio._crs import _CRS, all_proj_keys
from rasterio.compat import string_types


class CRS(_CRS):
    """A container class for coordinate reference system info

    PROJ.4 is the law of this land: http://proj.osgeo.org/. But whereas PROJ.4
    coordinate reference systems are described by strings of parameters such as

        +proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs

    here we use mappings:

        {'proj': 'longlat', 'ellps': 'WGS84', 'datum': 'WGS84', 'no_defs': True}

    One can set/get any PROJ.4 parameter using a dict-like key/value pair on the
    object. You can instantiate the object by simply passing a dict to the
    constructor. E.g.

        crs = CRS({'init': 'epsg:3005'})

    """

    @property
    def is_valid(self):
        """Check if valid geographic or projected coordinate reference system."""
        return self.is_geographic or self.is_projected

    @property
    def is_epsg_code(self):
        for val in self.values():
            if isinstance(val, string_types) and val.lower().startswith('epsg'):
                return True
        return False

    def to_string(self):
        """Turn a parameter mapping into a more conventional PROJ.4 string.

        Mapping keys are tested against the ``all_proj_keys`` list. Values of
        ``True`` are omitted, leaving the key bare: {'no_defs': True} -> "+no_defs"
        and items where the value is otherwise not a str, int, or float are
        omitted.
        """
        items = []
        for k, v in sorted(filter(
                lambda x: x[0] in all_proj_keys and x[1] is not False and (
                    isinstance(x[1], (bool, int, float)) or
                    isinstance(x[1], string_types)),
                self.items())):
            items.append("+" + "=".join(map(str, filter(
                lambda y: (y or y == 0) and y is not True, (k, v)))))
        return " ".join(items)

    @classmethod
    def from_epsg(cls, code):
        """Given an integer code, returns an EPSG-like mapping.

        Note: the input code is not validated against an EPSG database.
        """
        if int(code) <= 0:
            raise ValueError("EPSG codes are positive integers")
        return cls(init="epsg:%s" % code, no_defs=True)

    def __repr__(self):
        # Should use super() here, but what's the best way to be compatible
        # between Python 2 and 3?
        return "CRS({})".format(dict.__repr__(self.data))

    def to_dict(self):
        return self.data

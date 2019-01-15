"""Coordinate reference systems, class and functions.
"""

include "gdal.pxi"

import collections
import json
import logging

from rasterio._err import CPLE_BaseError, CPLE_NotSupportedError
from rasterio.compat import UserDict, string_types
from rasterio.errors import CRSError
from rasterio.env import env_ctx_if_needed

from rasterio._base cimport _osr_from_crs as osr_from_crs
from rasterio._base cimport _safe_osr_release
from rasterio._err cimport exc_wrap_int


log = logging.getLogger(__name__)


class _CRS(collections.Mapping):
    """CRS base class."""

    def __init__(self, initialdata=None, **kwargs):
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
        cdef OGRSpatialReferenceH osr = OSRNewSpatialReference(NULL)

        data = dict(initialdata or {})
        data.update(**kwargs)
        data = {k: v for k, v in data.items() if k in all_proj_keys}

        # always use lowercase 'epsg'.
        if 'init' in data:
            data['init'] = data['init'].replace('EPSG:', 'epsg:')

        proj = ' '.join(['+{}={}'.format(key, val) for key, val in data.items()])
        b_proj = proj.encode('utf-8')

        try:
            exc_wrap_int(OSRImportFromProj4(osr, <const char *>b_proj))
        except CPLE_BaseError as exc:
            raise CRSError("The PROJ4 dict could not be understood. {}".format(str(exc)))
        else:
            self._wkt = None
            self._data = data
        finally:
            _safe_osr_release(osr)

    @property
    def data(self):
        if not self._data and self._wkt:
            self._data = self.to_dict()
        return self._data

    def __getitem__(self, item):
        return self.data[item]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def _wkt_or_proj(self):
        return self._wkt or ' '.join(['+{}={}'.format(key, val) for key, val in self.data.items() if key in all_proj_keys])

    def __bool__(self):
        return bool(self._wkt or self.data)

    __nonzero__ = __bool__

    @property
    def is_geographic(self):
        """Test if the CRS is a geographic coordinate reference system

        Returns
        -------
        bool

        """
        cdef OGRSpatialReferenceH osr = OSRNewSpatialReference(NULL)

        try:
            osr_input = self._wkt_or_proj().encode('utf-8')
            exc_wrap_int(OSRSetFromUserInput(osr, <const char *>osr_input))
            exc_wrap_int(OSRMorphFromESRI(osr))
            return bool(OSRIsGeographic(osr) == 1)
        except CPLE_BaseError as exc:
            raise CRSError("{}".format(str(exc)))
        finally:
            _safe_osr_release(osr)

    @property
    def is_projected(self):
        """Test if the CRS is a projected coordinate reference system

        Returns
        -------
        bool

        """
        cdef OGRSpatialReferenceH osr = OSRNewSpatialReference(NULL)

        try:
            osr_input = self._wkt_or_proj().encode('utf-8')
            exc_wrap_int(OSRSetFromUserInput(osr, <const char *>osr_input))
            exc_wrap_int(OSRMorphFromESRI(osr))
            return bool(OSRIsProjected(osr) == 1)
        except CPLE_BaseError as exc:
            raise CRSError("{}".format(str(exc)))
        finally:
            _safe_osr_release(osr)

    def __eq__(self, other):
        cdef OGRSpatialReferenceH osr1 = NULL
        cdef OGRSpatialReferenceH osr2 = NULL

        if not self or not other:
            return not self and not other

        else:
            osr1 = OSRNewSpatialReference(NULL)
            osr2 = OSRNewSpatialReference(NULL)

            try:
                osr_input1 = self._wkt_or_proj().encode('utf-8')
                exc_wrap_int(OSRSetFromUserInput(osr1, <const char *>osr_input1))
                exc_wrap_int(OSRMorphFromESRI(osr1))

                if isinstance(other, string_types):
                    other = _CRS.from_string(other)
                elif not isinstance(other, _CRS):
                    other = _CRS(other)

                osr_input2 = other._wkt_or_proj().encode('utf-8')
                exc_wrap_int(OSRSetFromUserInput(osr2, <const char *>osr_input2))
                exc_wrap_int(OSRMorphFromESRI(osr2))

                return bool(OSRIsSame(osr1, osr2) == 1)

            finally:
                _safe_osr_release(osr1)
                _safe_osr_release(osr2)

    def to_wkt(self, morph_to_esri_dialect=False):
        """An OGC WKT representation of the CRS

        Parameters
        ----------
        morph_to_esri_dialect : bool, optional
            Whether or not to morph to the Esri dialect of WKT

        Returns
        -------
        str

        """
        cdef char *conv_wkt = NULL
        cdef OGRSpatialReferenceH osr = NULL

        if self._wkt:
            return self._wkt

        else:
            try:
                osr_input = self._wkt_or_proj().encode('utf-8')
                osr = OSRNewSpatialReference(NULL)
                exc_wrap_int(OSRSetFromUserInput(osr, <const char *>osr_input))

                if morph_to_esri_dialect:
                    exc_wrap_int(OSRMorphToESRI(osr))

                exc_wrap_int(OSRExportToWkt(osr, &conv_wkt))

                wkt = conv_wkt.decode('utf-8')

                if not wkt:
                    raise CRSError("Could not convert to WKT.")

                return wkt

            finally:
                CPLFree(conv_wkt)
                _safe_osr_release(osr)

    @property
    def wkt(self):
        """An OGC WKT representation of the CRS

        Returns
        -------
        str

        """
        return self.to_wkt()

    def to_epsg(self):
        """The epsg code of the CRS

        Returns
        -------
        int

        """
        cdef OGRSpatialReferenceH osr = OSRNewSpatialReference(NULL)

        try:
            osr_input = self._wkt_or_proj().encode('utf-8')
            exc_wrap_int(OSRSetFromUserInput(osr, <const char *>osr_input))
            exc_wrap_int(OSRFixup(osr))
            if OSRAutoIdentifyEPSG(osr) == 0:
                epsg_code = OSRGetAuthorityCode(osr, NULL)
                return int(epsg_code.decode('utf-8'))
            else:
                return None
        finally:
            _safe_osr_release(osr)

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
        if int(code) <= 0:
            raise CRSError("EPSG codes are positive integers")
        return cls.from_dict(init="epsg:{}".format(code))

    @classmethod
    def from_string(cls, s, morph_from_esri_dialect=False):
        """Make a CRS from an EPSG, PROJ, or WKT string

        Parameters
        ----------
        s : str
            An EPSG, PROJ, or WKT string.
        morph_from_esri_dialect : bool, optional
            If True, items in the input using Esri's dialect of WKT
            will be replaced by OGC standard equivalents.

        Returns
        -------
        CRS

        """
        if not s:
            raise CRSError("CRS is empty or invalid: {!r}".format(s))

        elif s.strip().upper().startswith('EPSG:'):
            auth, val = s.strip().split(':')
            if not val:
                raise CRSError("Invalid CRS: {!r}".format(s))
            return cls.from_epsg(val)

        elif s.startswith('{') or s.startswith('['):
            # may be json, try to decode it
            try:
                val = json.loads(s, strict=False)
            except ValueError:
                raise CRSError('CRS appears to be JSON but is not valid')

            if not val:
                raise CRSError("CRS is empty JSON")
            else:
                return cls.from_dict(**val)

        elif '+' in s and '=' in s:
            return cls.from_proj4(s)

        else:
            return cls.from_wkt(s, morph_from_esri_dialect=morph_from_esri_dialect)

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
        cdef OGRSpatialReferenceH osr = OSRNewSpatialReference(NULL)

        def parse(v):
            if v in ('True', 'true'):
                return True
            elif v in ('False', 'false'):
                return False
            else:
                try:
                    return int(v)
                except ValueError:
                    pass
                try:
                    return float(v)
                except ValueError:
                    return v

        b_proj = proj.encode('utf-8')

        try:
            exc_wrap_int(OSRImportFromProj4(osr, <const char *>b_proj))
        except CPLE_BaseError as exc:
            raise CRSError("The PROJ4 dict could not be understood. {}".format(str(exc)))
        else:
            parts = [o.lstrip('+') for o in proj.strip().split()]
            items = map(lambda kv: len(kv) == 2 and (kv[0], parse(kv[1])) or (kv[0], True), (p.split('=') for p in parts))
            obj = cls()
            obj._data = {k: v for k, v in items if k in all_proj_keys}
            return obj
        finally:
            _safe_osr_release(osr)

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
        cdef OGRSpatialReferenceH osr = OSRNewSpatialReference(NULL)

        data = dict(initialdata or {})
        data.update(**kwargs)
        data = {k: v for k, v in data.items() if k in all_proj_keys}

        # always use lowercase 'epsg'.
        if 'init' in data:
            data['init'] = data['init'].replace('EPSG:', 'epsg:')

        proj = ' '.join(['+{}={}'.format(key, val) for key, val in data.items()])
        b_proj = proj.encode('utf-8')

        try:
            exc_wrap_int(OSRImportFromProj4(osr, <const char *>b_proj))
        except CPLE_BaseError as exc:
            raise CRSError("The PROJ4 dict could not be understood. {}".format(str(exc)))
        else:
            obj = cls()
            obj._data = data
            return obj
        finally:
            _safe_osr_release(osr)

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
        cdef char *conv_wkt = NULL
        cdef OGRSpatialReferenceH osr = NULL

        if isinstance(wkt, string_types):
            b_wkt = wkt.encode('utf-8')
        else:
            raise ValueError("A string is expected")

        try:
            osr = OSRNewSpatialReference(b_wkt)

            if osr == NULL:
                raise CRSError("The WKT could not be parsed.")

            if morph_from_esri_dialect:
                exc_wrap_int(OSRMorphFromESRI(osr))

            exc_wrap_int(OSRExportToWkt(osr, &conv_wkt))
        except CPLE_BaseError as exc:
            raise CRSError("The WKT could not be parsed. {}".format(str(exc)))
        else:
            obj = cls()
            obj._wkt = conv_wkt.decode('utf-8')
            return obj
        finally:
            CPLFree(conv_wkt)
            _safe_osr_release(osr)

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
        if isinstance(value, _CRS):
            return value
        elif isinstance(value, int):
            return cls.from_epsg(value)
        elif isinstance(value, dict):
            return cls(**value)
        elif isinstance(value, string_types):
            return cls.from_string(value, morph_from_esri_dialect=morph_from_esri_dialect)
        else:
            raise CRSError("CRS is invalid: {!r}".format(value))

    def to_dict(self):
        """Convert CRS to a PROJ4 dict

        Returns
        -------
        dict

        """
        cdef OGRSpatialReferenceH osr = OSRNewSpatialReference(NULL)
        cdef char *prj = NULL

        if self._data:
            return dict(self._data)
        else:
            b_wkt = self._wkt.encode('utf-8')
            try:
                exc_wrap_int(OSRSetFromUserInput(osr, <const char *>b_wkt))
                exc_wrap_int(OSRMorphFromESRI(osr))
                exc_wrap_int(OSRExportToProj4(osr, &prj))
                proj_str = prj.decode('utf-8')
                parts = [o.lstrip('+') for o in proj_str.strip().split()]

                def parse(v):
                    if v in ('True', 'true'):
                        return True
                    elif v in ('False', 'false'):
                        return False
                    else:
                        try:
                            return int(v)
                        except ValueError:
                            pass
                        try:
                            return float(v)
                        except ValueError:
                            return v

                items = map(
                    lambda kv: len(kv) == 2 and (kv[0], parse(kv[1])) or (kv[0], True),
                    (p.split('=') for p in parts))

                return {k: v for k, v in items if k in all_proj_keys}
            except CPLE_BaseError as exc:
                raise CRSError("The WKT could not be parsed. {}".format(str(exc)))
            finally:
                CPLFree(prj)
                _safe_osr_release(osr)

# Below is the big list of PROJ4 parameters from
# http://trac.osgeo.org/proj/wiki/GenParms.
# It is parsed into a list of parameter keys ``all_proj_keys``.

_param_data = """
+a         Semimajor radius of the ellipsoid axis
+alpha     ? Used with Oblique Mercator and possibly a few others
+axis      Axis orientation (new in 4.8.0)
+b         Semiminor radius of the ellipsoid axis
+datum     Datum name (see `proj -ld`)
+ellps     Ellipsoid name (see `proj -le`)
+init      Initialize from a named CRS
+k         Scaling factor (old name)
+k_0       Scaling factor (new name)
+lat_0     Latitude of origin
+lat_1     Latitude of first standard parallel
+lat_2     Latitude of second standard parallel
+lat_ts    Latitude of true scale
+lon_0     Central meridian
+lonc      ? Longitude used with Oblique Mercator and possibly a few others
+lon_wrap  Center longitude to use for wrapping (see below)
+nadgrids  Filename of NTv2 grid file to use for datum transforms (see below)
+no_defs   Don't use the /usr/share/proj/proj_def.dat defaults file
+over      Allow longitude output outside -180 to 180 range, disables wrapping (see below)
+pm        Alternate prime meridian (typically a city name, see below)
+proj      Projection name (see `proj -l`)
+south     Denotes southern hemisphere UTM zone
+to_meter  Multiplier to convert map units to 1.0m
+towgs84   3 or 7 term datum transform parameters (see below)
+units     meters, US survey feet, etc.
+vto_meter vertical conversion to meters.
+vunits    vertical units.
+x_0       False easting
+y_0       False northing
+zone      UTM zone
+a         Semimajor radius of the ellipsoid axis
+alpha     ? Used with Oblique Mercator and possibly a few others
+azi
+b         Semiminor radius of the ellipsoid axis
+belgium
+beta
+czech
+e         Eccentricity of the ellipsoid = sqrt(1 - b^2/a^2) = sqrt( f*(2-f) )
+ellps     Ellipsoid name (see `proj -le`)
+es        Eccentricity of the ellipsoid squared
+f         Flattening of the ellipsoid (often presented as an inverse, e.g. 1/298)
+gamma
+geoc
+guam
+h
+k         Scaling factor (old name)
+K
+k_0       Scaling factor (new name)
+lat_0     Latitude of origin
+lat_1     Latitude of first standard parallel
+lat_2     Latitude of second standard parallel
+lat_b
+lat_t
+lat_ts    Latitude of true scale
+lon_0     Central meridian
+lon_1
+lon_2
+lonc      ? Longitude used with Oblique Mercator and possibly a few others
+lsat
+m
+M
+n
+no_cut
+no_off
+no_rot
+ns
+o_alpha
+o_lat_1
+o_lat_2
+o_lat_c
+o_lat_p
+o_lon_1
+o_lon_2
+o_lon_c
+o_lon_p
+o_proj
+over
+p
+path
+proj      Projection name (see `proj -l`)
+q
+R
+R_a
+R_A       Compute radius such that the area of the sphere is the same as the area of the ellipsoid
+rf        Reciprocal of the ellipsoid flattening term (e.g. 298)
+R_g
+R_h
+R_lat_a
+R_lat_g
+rot
+R_V
+s
+south     Denotes southern hemisphere UTM zone
+sym
+t
+theta
+tilt
+to_meter  Multiplier to convert map units to 1.0m
+units     meters, US survey feet, etc.
+vopt
+W
+westo
+x_0       False easting
+y_0       False northing
+zone      UTM zone
"""

with env_ctx_if_needed():
    _lines = filter(lambda x: len(x) > 1, _param_data.split("\n"))
    all_proj_keys = list(set(line.split()[0].lstrip("+").strip()
                             for line in _lines)) + ['no_mayo']

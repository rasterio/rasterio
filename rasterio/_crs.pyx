# cython: language_level=3, boundscheck=False

"""Coordinate reference systems, class and functions.
"""

import logging
import warnings

import rasterio._env
from rasterio._err import CPLE_BaseError, CPLE_NotSupportedError
from rasterio.errors import CRSError
from rasterio.enums import WktVersion

from rasterio._base cimport _osr_from_crs as osr_from_crs
from rasterio._base cimport _safe_osr_release, osr_get_name, osr_set_traditional_axis_mapping_strategy
from rasterio._err cimport exc_wrap_ogrerr, exc_wrap_int, exc_wrap_pointer


log = logging.getLogger(__name__)


def gdal_version():
    """Return the version as a major.minor.patchlevel string."""
    cdef char *info_c = NULL
    info_c = GDALVersionInfo("RELEASE_NAME")
    info_b = info_c
    return info_b.decode("utf-8")


def _epsg_treats_as_latlong(input_crs):
    """Test if the CRS is in latlon order

    Parameters
    ----------
    input_crs : _CRS
        rasterio _CRS object

    Returns
    -------
    bool

    """
    cdef _CRS crs = input_crs

    try:
        return bool(OSREPSGTreatsAsLatLong(crs._osr) == 1)
    except CPLE_BaseError as exc:
        raise CRSError("{}".format(exc))


def _epsg_treats_as_northingeasting(input_crs):
    """Test if the CRS should be treated as having northing/easting coordinate ordering

    Parameters
    ----------
    input_crs : _CRS
        rasterio _CRS object

    Returns
    -------
    bool

    """
    cdef _CRS crs = input_crs

    try:
        return bool(OSREPSGTreatsAsNorthingEasting(crs._osr) == 1)
    except CPLE_BaseError as exc:
        raise CRSError("{}".format(exc))


cdef class _CRS:
    """Cython extension class"""

    def __cinit__(self):
        self._osr = OSRNewSpatialReference(NULL)

    def __dealloc__(self):
        _safe_osr_release(self._osr)

    @property
    def is_geographic(self):
        """Test if the CRS is a geographic coordinate reference system

        Returns
        -------
        bool

        """
        try:
            return bool(OSRIsGeographic(self._osr) == 1)
        except CPLE_BaseError as exc:
            raise CRSError("{}".format(exc))

    @property
    def is_projected(self):
        """Test if the CRS is a projected coordinate reference system

        Returns
        -------
        bool

        """
        try:
            return bool(OSRIsProjected(self._osr) == 1)
        except CPLE_BaseError as exc:
            raise CRSError("{}".format(exc))

    @property
    def linear_units(self):
        """Get linear units of the CRS
        Returns
        -------
        str
        """
        cdef char *units_c = NULL
        cdef double fmeter

        try:
            fmeter = OSRGetLinearUnits(self._osr, &units_c)
        except CPLE_BaseError as exc:
            raise CRSError("{}".format(exc))
        else:
            units_b = units_c
            return units_b.decode('utf-8')

    @property
    def linear_units_factor(self):
        """Get linear units and the conversion factor to meters of the CRS

        Returns
        -------
        tuple

        """
        cdef char *units_c = NULL
        cdef double to_meters

        try:
            if self.is_projected:
                to_meters = OSRGetLinearUnits(self._osr, &units_c)
            else:
                raise CRSError("{}".format("Linear units factor is not defined for non projected CRS"))
        except CPLE_BaseError as exc:
            raise CRSError("{}".format(exc))
        else:
            units_b = units_c
            return (units_b.decode('utf-8'), to_meters)

    def __eq__(self, other):
        cdef OGRSpatialReferenceH osr_s = NULL
        cdef OGRSpatialReferenceH osr_o = NULL
        cdef _CRS crs_o = other

        epsg_s = self.to_epsg()
        epsg_o = other.to_epsg()

        if epsg_s is not None and epsg_o is not None and epsg_s == epsg_o:
            return True

        else:
            try:
                osr_s = exc_wrap_pointer(OSRClone(self._osr))
                exc_wrap_ogrerr(OSRMorphFromESRI(osr_s))
                osr_o = exc_wrap_pointer(OSRClone(crs_o._osr))
                exc_wrap_ogrerr(OSRMorphFromESRI(osr_o))
                return bool(OSRIsSame(osr_s, osr_o) == 1)

            finally:
                _safe_osr_release(osr_s)
                _safe_osr_release(osr_o)

    def to_wkt(self, morph_to_esri_dialect=False, version=None):
        """An OGC WKT representation of the CRS

         .. versionadded:: 1.3.0 version

        Parameters
        ----------
        morph_to_esri_dialect : bool, optional
            Whether or not to morph to the Esri dialect of WKT
            Only applies to GDAL versions < 3. This parameter will be removed in a future version of rasterio.
        version : WktVersion or str, optional
            The version of the WKT output.
            Only works with GDAL 3+. Default is WKT1_GDAL.

        Returns
        -------
        str

        """
        cdef char *conv_wkt = NULL
        IF CTE_GDAL_MAJOR_VERSION >= 3:
            cdef const char* options_wkt[2]
            options_wkt[0] = NULL
            options_wkt[1] = NULL

        try:
            if osr_get_name(self._osr) != NULL:
                IF CTE_GDAL_MAJOR_VERSION >= 3:
                    if morph_to_esri_dialect:
                        warnings.warn(
                            "'morph_to_esri_dialect' ignored with GDAL 3+. "
                            "Use 'version=WktVersion.WKT1_ESRI' instead."
                        )
                    if version:
                        version = WktVersion(version).value
                        wkt_format = "FORMAT={}".format(version).encode("utf-8")
                        options_wkt[0] = wkt_format
                    exc_wrap_ogrerr(OSRExportToWktEx(self._osr, &conv_wkt, options_wkt))
                ELSE:
                    if version is not None:
                        warnings.warn("'version' requires GDAL 3+")
                    if morph_to_esri_dialect:
                        exc_wrap_ogrerr(OSRMorphToESRI(self._osr))
                    exc_wrap_ogrerr(OSRExportToWkt(self._osr, &conv_wkt))

        except CPLE_BaseError as exc:
            raise CRSError("Cannot convert to WKT. {}".format(exc))

        else:
            if conv_wkt != NULL:
                return conv_wkt.decode('utf-8')
            else:
                return ''
        finally:
            CPLFree(conv_wkt)


    def to_epsg(self):
        """The epsg code of the CRS

        Returns
        -------
        int

        """
        if self._epsg is not None:
            return self._epsg

        auth = self.to_authority()
        if auth is None:
            return None
        name, code = auth
        if name.upper() == "EPSG":
            self._epsg = int(code)
        return self._epsg

    def to_authority(self):
        """The authority name and code of the CRS

        Returns
        -------
        (str, str) or None

        """
        cdef OGRSpatialReferenceH osr = NULL

        code = None
        name = None

        try:
            osr = exc_wrap_pointer(OSRClone(self._osr))
            exc_wrap_ogrerr(OSRMorphFromESRI(osr))

            if OSRAutoIdentifyEPSG(osr) == 0:
                c_code = OSRGetAuthorityCode(osr, NULL)
                c_name = OSRGetAuthorityName(osr, NULL)
                if c_code != NULL and c_name != NULL:
                    code = c_code.decode('utf-8')
                    name = c_name.decode('utf-8')

        finally:
            _safe_osr_release(osr)

        if None not in (name, code):
            return (name, code)

        return None

    def to_json(self, pretty=False, indentation=2):
        """PROJ JSON representation of the CRS

        .. versionadded:: 1.3.0

        .. note:: Requites GDAL 3.1+ and PROJ 6.2+

        Parameters
        ----------
        pretty: bool
            If True, it will set the output to be a multiline string. Defaults to False.
        indentation: int
            If pretty is True, it will set the width of the indentation. Default is 2.

        Returns
        -------
        str

        """
        cdef char *conv_json = NULL
        cdef const char* options[3]

        try:
            IF (CTE_GDAL_MAJOR_VERSION, CTE_GDAL_MINOR_VERSION) >= (3, 1):
                if osr_get_name(self._osr) != NULL:
                    multiline = b"MULTILINE=NO"
                    if pretty:
                        multiline = b"MULTILINE=YES"
                    indentation_width = f"INDENTATION_WIDTH={indentation:.0f}".encode("utf-8")
                    options[0] = multiline
                    options[1] = indentation_width
                    options[2] = NULL
                    exc_wrap_ogrerr(OSRExportToPROJJSON(self._osr, &conv_json, options))
            ELSE:
                raise CRSError("GDAL 3.1+ required to export to PROJ JSON.")

        except CPLE_BaseError as exc:
            raise CRSError("Cannot convert to PROJ JSON. {}".format(exc))

        else:
            if conv_json != NULL:
                return conv_json.decode('utf-8')
            else:
                return ''
        finally:
            CPLFree(conv_json)


    @staticmethod
    def from_epsg(code):
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
        cdef _CRS obj = _CRS.__new__(_CRS)

        code = int(code)

        if code <= 0:
            raise CRSError("EPSG codes are positive integers")

        try:
            exc_wrap_ogrerr(exc_wrap_int(OSRImportFromEPSG(obj._osr, <int>code)))
        except CPLE_BaseError as exc:
            raise CRSError("The EPSG code is unknown. {}".format(exc))
        else:
            osr_set_traditional_axis_mapping_strategy(obj._osr)
            obj._epsg = code
            return obj

    @staticmethod
    def from_proj4(proj):
        """Make a CRS from a PROJ4 string

        Parameters
        ----------
        proj : str
            A PROJ4 string like "+proj=longlat ..."

        Returns
        -------
        CRS

        """
        cdef _CRS obj = _CRS.__new__(_CRS)

        # Filter out nonsensical items that might have crept in.
        items_filtered = []
        items = proj.split()
        for item in items:
            parts = item.split('=')
            if len(parts) == 2 and parts[1] in ('false', 'False'):
                continue
            items_filtered.append(item)

        proj = ' '.join(items_filtered)
        proj_b = proj.encode('utf-8')

        try:
            exc_wrap_ogrerr(exc_wrap_int(OSRImportFromProj4(obj._osr, <const char *>proj_b)))
        except CPLE_BaseError as exc:
            raise CRSError("The PROJ4 dict could not be understood. {}".format(exc))
        else:
            osr_set_traditional_axis_mapping_strategy(obj._osr)
            return obj

    @staticmethod
    def from_dict(initialdata=None, **kwargs):
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
        data = dict(initialdata or {})
        data.update(**kwargs)
        data = {k: v for k, v in data.items() if k in all_proj_keys}

        # "+init=epsg:xxxx" is deprecated in GDAL. If we find this, we will
        # extract the epsg code and dispatch to from_epsg.
        if 'init' in data and data['init'].lower().startswith('epsg:'):
            epsg_code = int(data['init'].split(':')[1])
            return _CRS.from_epsg(epsg_code)

        # Continue with the general case.
        proj = ' '.join(['+{}={}'.format(key, val) for key, val in data.items()])
        b_proj = proj.encode('utf-8')

        cdef _CRS obj = _CRS.__new__(_CRS)

        try:
            exc_wrap_ogrerr(OSRImportFromProj4(obj._osr, <const char *>b_proj))
        except CPLE_BaseError as exc:
            raise CRSError("The PROJ4 dict could not be understood. {}".format(exc))
        else:
            osr_set_traditional_axis_mapping_strategy(obj._osr)
            return obj

    @staticmethod
    def from_wkt(wkt, morph_from_esri_dialect=False):
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
        cdef char *wkt_c = NULL

        if not isinstance(wkt, str):
            raise ValueError("A string is expected")

        wkt_b= wkt.encode('utf-8')
        wkt_c = wkt_b

        cdef _CRS obj = _CRS.__new__(_CRS)

        try:
            errcode = exc_wrap_ogrerr(OSRImportFromWkt(obj._osr, &wkt_c))
            if morph_from_esri_dialect and not gdal_version().startswith("3"):
                exc_wrap_ogrerr(OSRMorphFromESRI(obj._osr))
        except CPLE_BaseError as exc:
            raise CRSError("The WKT could not be parsed. {}".format(exc))
        else:
            osr_set_traditional_axis_mapping_strategy(obj._osr)
            return obj

    @staticmethod
    def from_user_input(text, morph_from_esri_dialect=False):
        """Make a CRS from a WKT string

        Parameters
        ----------
        text : str
            User input text of many different kinds.
        morph_from_esri_dialect : bool, optional
            If True, items in the input using Esri's dialect of WKT
            will be replaced by OGC standard equivalents.

        Returns
        -------
        CRS

        """
        cdef const char *text_c = NULL

        if not isinstance(text, str):
            raise ValueError("A string is expected")

        text_b = text.encode('utf-8')
        text_c = text_b

        cdef _CRS obj = _CRS.__new__(_CRS)

        try:
            errcode = exc_wrap_ogrerr(OSRSetFromUserInput(obj._osr, text_c))
            if morph_from_esri_dialect and not gdal_version().startswith("3"):
                exc_wrap_ogrerr(OSRMorphFromESRI(obj._osr))
        except CPLE_BaseError as exc:
            raise CRSError("The WKT could not be parsed. {}".format(exc))
        else:
            osr_set_traditional_axis_mapping_strategy(obj._osr)
            return obj

    def to_dict(self):
        """Convert CRS to a PROJ4 dict

        Returns
        -------
        dict

        """
        cdef OGRSpatialReferenceH osr = NULL
        cdef char *proj_c = NULL

        try:
            osr = exc_wrap_pointer(OSRClone(self._osr))
            exc_wrap_ogrerr(OSRMorphFromESRI(osr))
            exc_wrap_ogrerr(OSRExportToProj4(osr, &proj_c))

        except CPLE_BaseError as exc:
            raise CRSError("The WKT could not be parsed. {}".format(exc))

        else:
            proj_b = proj_c
            proj = proj_b.decode('utf-8')

        finally:
            CPLFree(proj_c)
            _safe_osr_release(osr)

        parts = [o.lstrip('+') for o in proj.strip().split()]

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

        return {k: v for k, v in items if k in all_proj_keys and v is not False}

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
+wktext
+x_0       False easting
+y_0       False northing
+zone      UTM zone
"""

_lines = filter(lambda x: len(x) > 1, _param_data.split("\n"))
all_proj_keys = list(set(line.split()[0].lstrip("+").strip() for line in _lines)) + ['no_mayo']

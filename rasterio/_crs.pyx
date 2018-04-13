"""Coordinate reference systems, class and functions.
"""

include "gdal.pxi"

import logging
import warnings

from rasterio.compat import UserDict
from rasterio.compat import string_types
from rasterio.errors import CRSError

from rasterio._base cimport _osr_from_crs as osr_from_crs
from rasterio._base cimport _safe_osr_release


log = logging.getLogger(__name__)


class _CRS(UserDict):
    """CRS base class."""

    @property
    def is_geographic(self):
        cdef OGRSpatialReferenceH osr_crs = NULL
        cdef int retval

        try:
            osr_crs = osr_from_crs(self)
            retval = OSRIsGeographic(osr_crs)
            return bool(retval == 1)
        finally:
            _safe_osr_release(osr_crs)

    @property
    def is_projected(self):
        cdef OGRSpatialReferenceH osr_crs = NULL
        cdef int retval

        try:
            osr_crs = osr_from_crs(self)
            retval = OSRIsProjected(osr_crs)
            return bool(retval == 1)
        finally:
            _safe_osr_release(osr_crs)

    def __eq__(self, other):
        cdef OGRSpatialReferenceH osr_crs1 = NULL
        cdef OGRSpatialReferenceH osr_crs2 = NULL
        cdef int retval

        try:
            if not self and not other:
                return True

            # use dictionary equality rules first
            elif UserDict(self.data) == UserDict(other):
                return True

            elif not self or not other:
                return False

            else:
                osr_crs1 = osr_from_crs(self)
                osr_crs2 = osr_from_crs(other)
                retval = OSRIsSame(osr_crs1, osr_crs2)
                return bool(retval == 1)

        finally:
            _safe_osr_release(osr_crs1)
            _safe_osr_release(osr_crs2)

    @property
    def wkt(self):
        """An OGC WKT string representation of the coordinate reference
        system.
        """
        cdef char *srcwkt = NULL
        cdef OGRSpatialReferenceH osr = NULL

        try:
            osr = osr_from_crs(self)
            OSRExportToWkt(osr, &srcwkt)
            return srcwkt.decode('utf-8')
        finally:
            CPLFree(srcwkt)
            _safe_osr_release(osr)

    @classmethod
    def from_wkt(cls, wkt):

        """Turn an OGC WKT string representation of a coordinate reference
        system into a mapping of PROJ.4 parameters.

        Parameters
        ----------
        wkt : str
            OGC WKT text representation of a coordinate reference system.

        Returns
        -------
        CRS
        """

        if isinstance(wkt, string_types):
            b_wkt = wkt.encode('utf-8')

        cdef char *proj4 = NULL
        cdef OGRSpatialReferenceH osr = OSRNewSpatialReference(b_wkt)

        if osr == NULL:
            raise CRSError("Invalid WKT: {}".format(wkt))

        try:
            OSRExportToProj4(osr, &proj4)
            return cls.from_string(proj4.decode('utf-8'))
        finally:
            CPLFree(proj4)
            _safe_osr_release(osr)

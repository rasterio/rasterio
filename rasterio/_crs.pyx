"""Coordinate reference systems, class and functions.
"""

include "gdal.pxi"

import logging

from rasterio.compat import UserDict
from rasterio.compat import string_types

from rasterio._base cimport _osr_from_crs as osr_from_crs


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
            OSRRelease(osr_crs)

    @property
    def is_projected(self):
        cdef OGRSpatialReferenceH osr_crs = NULL
        cdef int retval

        try:
            osr_crs = osr_from_crs(self)
            retval = OSRIsProjected(osr_crs)
            return bool(retval == 1)
        finally:
            OSRRelease(osr_crs)

    def __eq__(self, other):
        cdef OGRSpatialReferenceH osr_crs1 = NULL
        cdef OGRSpatialReferenceH osr_crs2 = NULL
        cdef int retval

        try:
            # return False immediately if either value is undefined
            if not (self and other):
                return False
            osr_crs1 = osr_from_crs(self)
            osr_crs2 = osr_from_crs(other)
            retval = OSRIsSame(osr_crs1, osr_crs2)
            return bool(retval == 1)
        finally:
            OSRRelease(osr_crs1)
            OSRRelease(osr_crs2)

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
            OSRRelease(osr)

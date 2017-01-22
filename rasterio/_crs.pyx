"""Coordinate reference systems, class and functions.
"""

import logging

from rasterio.compat import UserDict
from rasterio.compat import string_types

from rasterio._base cimport _osr_from_crs as osr_from_crs
from rasterio._gdal cimport (
    CPLFree, OSRDestroySpatialReference, OSRExportToWkt, OSRIsGeographic,
    OSRIsProjected, OSRIsSame)

include "gdal.pxi"


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
            OSRDestroySpatialReference(osr_crs)

    @property
    def is_projected(self):
        cdef OGRSpatialReferenceH osr_crs = NULL
        cdef int retval

        try:
            osr_crs = osr_from_crs(self)
            retval = OSRIsProjected(osr_crs)
            return bool(retval == 1)
        finally:
            OSRDestroySpatialReference(osr_crs)

    def __eq__(self, other):
        cdef OGRSpatialReferenceH osr_crs1 = NULL
        cdef OGRSpatialReferenceH osr_crs2 = NULL
        cdef int retval

        try:
            osr_crs1 = osr_from_crs(self)
            osr_crs2 = osr_from_crs(other)
            osrs_valid = ((OSRIsGeographic(osr_crs1) == 1 or
                           OSRIsProjected(osr_crs1) == 1) and
                          (OSRIsGeographic(osr_crs2) == 1 or
                           OSRIsProjected(osr_crs2) == 1))
            osr_same = (OSRIsSame(osr_crs1, osr_crs2) == 1)
            return (osr_same and osrs_valid)
        finally:
            OSRDestroySpatialReference(osr_crs1)
            OSRDestroySpatialReference(osr_crs2)

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
            OSRDestroySpatialReference(osr)

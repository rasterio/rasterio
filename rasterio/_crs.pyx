"""Coordinate reference systems, class and functions.
"""

import logging

from rasterio cimport _gdal, _base
from rasterio.compat import UserDict
from rasterio.compat import string_types

log = logging.getLogger(__name__)

class _CRS(UserDict):
    """
    """
    @property
    def is_geographic(self):
        cdef void *osr_crs = NULL
        cdef int retval
        try:
            osr_crs = _base._osr_from_crs(self)
            retval = _gdal.OSRIsGeographic(osr_crs)
            return bool(retval == 1)
        finally:
            _gdal.OSRDestroySpatialReference(osr_crs)

    @property
    def is_projected(self):
        cdef void *osr_crs = NULL
        cdef int retval
        try:
            osr_crs = _base._osr_from_crs(self)
            retval = _gdal.OSRIsProjected(osr_crs)
            return bool(retval == 1)
        finally:
            _gdal.OSRDestroySpatialReference(osr_crs)

    def __eq__(self, other):
        cdef void *osr_crs1 = NULL
        cdef void *osr_crs2 = NULL
        cdef int retval
        try:
            osr_crs1 = _base._osr_from_crs(self)
            osr_crs2 = _base._osr_from_crs(other)
            retval = _gdal.OSRIsSame(osr_crs1, osr_crs2)
            return bool(retval == 1)
        finally:
            _gdal.OSRDestroySpatialReference(osr_crs1)
            _gdal.OSRDestroySpatialReference(osr_crs2)

    @property
    def wkt(self):
        """An OGC WKT string representation of the coordinate reference
        system.
        """
        cdef char *srcwkt = NULL
        cdef void *osr = NULL
        try:
            osr = _base._osr_from_crs(self)
            _gdal.OSRExportToWkt(osr, &srcwkt)
            wkt = srcwkt.decode('utf-8')
        finally:
            _gdal.CPLFree(srcwkt)
            _gdal.OSRDestroySpatialReference(osr)
        return wkt

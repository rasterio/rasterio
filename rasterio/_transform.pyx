# cython: boundscheck=False, c_string_type=unicode, c_string_encoding=utf8
"""Transforms."""

include "gdal.pxi"

import warnings

from rasterio._err import GDALError
from rasterio.errors import NotGeoreferencedWarning

def _transform_from_gcps(gcps):
    cdef double gt[6]

    cdef GDAL_GCP *gcplist = <GDAL_GCP *>CPLMalloc(len(gcps) * sizeof(GDAL_GCP))
    
    try:
        for i, obj in enumerate(gcps):
            ident = str(i).encode('utf-8')
            info = "".encode('utf-8')
            gcplist[i].pszId = ident
            gcplist[i].pszInfo = info
            gcplist[i].dfGCPPixel = obj.col
            gcplist[i].dfGCPLine = obj.row
            gcplist[i].dfGCPX = obj.x
            gcplist[i].dfGCPY = obj.y
            gcplist[i].dfGCPZ = obj.z or 0.0

        err = GDALGCPsToGeoTransform(len(gcps), gcplist, gt, 0)
        if err == GDALError.failure:
                warnings.warn(
                "Could not get geotransform set from gcps. The identity matrix may be returned.",
                NotGeoreferencedWarning)

    finally:
            CPLFree(gcplist)

    return [gt[i] for i in range(6)]


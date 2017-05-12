include "directives.pxi"

# The baseline GDAL API.
include "gdal.pxi"

# Shim API for GDAL >= 2.0
include "shim_rasterioex.pxi"


# Declarations and implementations specific for GDAL >= 2.1
cdef extern from "gdal.h" nogil:

    cdef CPLErr GDALDeleteRasterNoDataValue(GDALRasterBandH hBand)


cdef int delete_nodata_value(GDALRasterBandH hBand) except 3:
    return GDALDeleteRasterNoDataValue(hBand)

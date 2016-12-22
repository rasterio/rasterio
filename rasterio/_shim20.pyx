# cython: boundscheck=False

# The baseline GDAL API.
include "gdal.pxi"

# Shim API for GDAL >= 2.0
include "shim_rasterioex.pxi"


# Declarations and implementations specific for GDAL==2.0
cdef int delete_nodata_value(GDALRasterBandH hBand) except 3:
    raise NotImplementedError(
        "GDAL versions < 2.1 do not support nodata deletion")

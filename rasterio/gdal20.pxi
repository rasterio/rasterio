# Inline versions of functions provided by GDAL 2.1+.

cdef inline int GDALDeleteRasterNoDataValue(GDALRasterBandH hBand) except 3:
    raise NotImplementedError(
        "GDAL versions < 2.1 do not support nodata deletion")

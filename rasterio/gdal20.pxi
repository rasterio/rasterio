# Inline versions of functions provided by GDAL 2.1+.

cdef inline CPLErr GDALDeleteRasterNoDataValue(GDALRasterBandH hBand):
    raise NotImplementedError(
        "GDAL versions < 2.1 do not support nodata deletion")

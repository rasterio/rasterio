cdef extern from "gdal.h" nogil:

    CPLErr GDALDeleteRasterNoDataValue(GDALRasterBandH hBand)

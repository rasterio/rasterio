DEF CAN_DELETE_NODATA = True

cdef extern from "gdal.h" nogil:

    CPLErr GDALDeleteRasterNoDataValue(GDALRasterBandH hBand)

include "gdal.pxi"

cdef extern from "gdal.h":
    ctypedef void* GDALRasterAttributeTableH
    GDALRasterAttributeTableH GDALCreateRasterAttributeTable()
    void GDALDestroyRasterAttributeTable(GDALRasterAttributeTableH hRAT)
    int GDALRATGetColumnCount(GDALRasterAttributeTableH hRAT)

cdef class GDALRasterAttributeTableWrapper:
    cdef GDALRasterAttributeTableH _hRAT
    cdef _get_column_index(self, const char * name)
    cdef add_column(self, const char * column_name, const GDALRATFieldType column_type, const GDALRATFieldUsage column_usage, int * values, int row_start, int row_end)
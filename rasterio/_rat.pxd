include "gdal.pxi"

#cdef extern from "gdal.h":
#    GDALRasterAttributeTableH GDALCreateRasterAttributeTable()
#    void GDALDestroyRasterAttributeTable(GDALRasterAttributeTableH hRAT)
#    int GDALRATGetColumnCount(GDALRasterAttributeTableH hRAT)

cdef class GDALRasterAttributeTableWrapper:
    cdef GDALRasterAttributeTableH _hRAT
    cdef read(self, GDALRasterAttributeTableH rat)
    cdef _get_column_count(self)
    cdef get_row_count(self)
    cdef _get_column_index(self, const char * name)
    cdef add_column(self, const char * column_name, const GDALRATFieldType column_type, const GDALRATFieldUsage column_usage, int * values, int row_start, int row_end)


cdef class RATReader():
    cdef GDALRasterAttributeTableH hRAT
    cdef GDALRasterAttributeTableH handle(self) except NULL
    cdef void read(self, GDALRasterAttributeTableH rat, bint clone)
    cdef int _get_column_count(self)

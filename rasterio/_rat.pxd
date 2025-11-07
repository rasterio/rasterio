include "gdal.pxi"

cdef class RATBase:
    cdef GDALRasterAttributeTableH _hRAT
    @staticmethod
    cdef RATBase clone(GDALRasterAttributeTableH rat_ptr)
    cdef int _get_column_count(self)
    cdef int _get_row_count(self)
    cdef int _get_column_index(self, str name)
    cdef char * _get_column_name(self, const int index)
    cdef GDALRATFieldUsage _get_column_usage(self, int index)
    cdef GDALRATFieldType _get_column_type(self, int index)
    cdef _get_string_column( self, int column_index, int start_row, int end_row)
    cdef int _create_column(self, const char * column_name, const GDALRATFieldType column_type, const GDALRATFieldUsage column_usage)
    cdef void create(self)
include "gdal.pxi"

cdef class RATBase:
    cdef GDALRasterAttributeTableH _hRAT
    cdef void _clone(self, GDALRasterAttributeTableH rat)
    cdef void _create(self)
    cdef int _get_column_count(self)
    cdef int _get_row_count(self)
    cdef int _get_column_index(self, str name)
    cdef char * _get_column_name(self, const int index)
    cdef GDALRATFieldType _get_column_type(self, int index)
    cdef _get_string_column( self, int column_index, int start_row, int end_row)
    cdef int _create_column(self, const char * column_name, const GDALRATFieldType column_type, const GDALRATFieldUsage column_usage)
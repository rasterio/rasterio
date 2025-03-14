import numpy as np
cimport numpy as np

cdef class GDALRasterAttributeTableWrapper:

    def __cinit__(self):
        self._hRAT = GDALCreateRasterAttributeTable()
        if self._hRAT == NULL:
            raise MemoryError("Failed to create GDALRasterAttributeTable")

    def __dealloc__(self):
        if self._hRAT != NULL:
            GDALDestroyRasterAttributeTable(self._hRAT)

    def get_column_count(self):
        if self._hRAT == NULL:
            raise ValueError("Raster attribute table is NULL")
        
        cdef int count = GDALRATGetColumnCount(self._hRAT)
        return count
    
    def get_row_count(self):
        if self._hRAT == NULL:
            raise ValueError("Raster attribute table is NULL")
        
        cdef int count = GDALRATGetRowCount(self._hRAT)
        return count

    cdef _get_column_index(self, const char * name):
        
        for i in range(self.get_column_count()):
            if GDALRATGetNameOfCol(self._hRAT, i) == name:
                return i
        return -1

    def _add_column_wrapper(
        self,
        column_name: bytes | str,
        column_type,
        column_usage,
        values: np.ndarray,
        row_start: int,
        row_end: int):
        
        if isinstance(column_name, str):
            column_name = column_name.encode('utf-8')
        elif isinstance(column_name, bytes):
            pass
        else:
            raise TypeError("Column name must be a string or bytes")

        cdef char * c_column_name = column_name
        cdef int *buf = <int *>np.PyArray_DATA(values)

        self.add_column(
            c_column_name,
            column_type,
            column_usage,
            buf,
            row_start,
            row_end
        )


    cdef add_column(
        self,
        const char * column_name,
        const GDALRATFieldType column_type,
        const GDALRATFieldUsage column_usage,
        int * values,
        int row_start,
        int row_end):

        GDALRATCreateColumn(
            self._hRAT,
            column_name,
            column_type,
            column_usage
        )

        index = self._get_column_index(column_name)

        GDALRATValuesIOAsInteger(
            self._hRAT,
            GDALRWFlag.GF_Write,
            index,
            row_start,
            row_end,
            values
        )	
    
#    def get_column(self, index):

#        if isinstance(index, str):
#            index = self._get_column_index(index)
#        if isinstance(index, int):
#            if index < 0 or index >= self.get_column_count():
#                raise IndexError("Column index out of range")
#        else:
#            raise TypeError("Index must be an integer or string")

#        values = np.ndarray(
#            shape=(self.get_row_count(),),
#            dtype=np.int32,
#        )
#        GDALRATValuesIOAsInteger(
#            self._hRAT,
#            GF_Read,
#            index,
#            0,
#            self.get_row_count(),
#            values
#        )
#        return values



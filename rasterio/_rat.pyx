import numpy as np
cimport numpy as np

from rasterio._err cimport exc_wrap_pointer, exc_wrap_int, exc_wrap

cdef class GDALRasterAttributeTableWrapper:

    def __cinit__(self):
        self._hRAT = NULL
        if self._hRAT == NULL:
            print("Initialized to NULL")

    def __dealloc__(self):
        if self._hRAT != NULL:
            GDALDestroyRasterAttributeTable(self._hRAT)

    cdef read(self, GDALRasterAttributeTableH rat):
        self._hRAT = rat
        if self._hRAT == NULL:
            print("Read failed, RAT is NULL")
        else:
            print("Read successful, RAT is not NULL")

    cdef _get_column_count(self):
        print('Getting column count')
        if self._hRAT == NULL:
            raise ValueError("Raster attribute table is NULL")
        count =  exc_wrap_int(GDALRATGetColumnCount(self._hRAT))
        print(f"Column count: {count}")
        return count
    
    def get_column_count(self):
        print("get_column_count() called")
        count = self._get_column_count()
        print(f"get_column_count() returning {count}")
        return count

    cdef get_row_count(self):
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

cdef class RATReader:

    def __cinit__(self):
        self.hRAT = NULL

    cdef GDALRasterAttributeTableH handle(self) except NULL:
        if self.hRAT == NULL:
            raise ValueError("Raster attribute table is NULL")
        else:
            return self.hRAT

    cdef void read(self, GDALRasterAttributeTableH rat, bint clone):

        if clone:
            self.hRAT = GDALRATClone(rat)
        else:
            self.hRAT = rat

        if self.hRAT == NULL:
            raise ValueError("RAT handle failed to load")

    cdef int _get_column_count(self):
        print('Getting column count')
        cdef int count = GDALRATGetColumnCount(self.handle())
        print(f"Column count: {count}")
        return count

    def get_column_count(self):
        print("RATReader get_column_count() called")
        cdef int count = self._get_column_count()
        return(count)
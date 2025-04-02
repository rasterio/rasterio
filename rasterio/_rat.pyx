import numpy as np
cimport numpy as np

from rasterio.rat import (
    numpy_types,
)

cdef class RATBase:

    def __cinit__(self):
        self._hRAT = NULL

    def __dealloc__(self):
        if self._hRAT != NULL:
            GDALDestroyRasterAttributeTable(self._hRAT)

    def __len__(self):
        return self._get_row_count()


    def __getitem__(self, ix):

        if isinstance(ix, (str, bytes, int)):
            # Single column by name
            ix = [ix]

        elif isinstance(ix, slice):
            # Slice of columns
            ix = list(
                range( *ix.indices( self._get_column_count()))
            )
        elif not isinstance(ix, (list, tuple, set)):
            # Collection of columns
            raise AttributeError(f"Index {ix} not recognized")

        column_indexes = []
        for index in ix:
            if isinstance(index, str):
                column_indexes.append(self._get_column_index(index))
            elif isinstance(index, bytes):
                column_indexes.append(self._get_column_index(index.decode()))
            elif isinstance(index, int):
                column_indexes.append(index)
            else:
                raise AttributeError(f'Column indexes must be integers or string, got {type(index)}')
        
        column_names = [self._get_column_name(i).decode('utf-8') for i in column_indexes]

        # TODO: Return column usages and table type?
        data = [self._get_column(i) for i in column_indexes]

        retvalue = np.core.records.fromarrays(
            data,
            names=','.join(column_names)
        )

        return retvalue

    def __setitem__(self, ix, col):

        if 0 > ix < self._get_column_count():
            print('DEBUG: CREATING COLUMN')
            ix = self._create_column(
                col.name.encode('utf-8'),
                col.field_type,
                col.usage
            )
        
        cdef int *val = <int*>np.PyArray_DATA(col.values)
        array_len = len(col.values)

        assert array_len == self._get_row_count()

        GDALRATValuesIOAsInteger(
            self._hRAT,
            GF_Write,
            ix,
            0,
            array_len,
            val
        )

    cdef void _clone(self, GDALRasterAttributeTableH rat):

        if self._hRAT != NULL:
            raise ValueError("RAT Handle already exists, cannot clone")

        self._hRAT = GDALRATClone(rat)

        if self._hRAT == NULL:
            raise ValueError("RAT handle failed to clone")
    
    cdef void _create(self):

        if self._hRAT == NULL:
            self._hRAT = GDALCreateRasterAttributeTable()
        else:
            raise ValueError("RAT Handle already exists, cannot create a new one")

    cdef int _get_row_count(self):
        if self._hRAT == NULL:
            raise ValueError("Raster attribute table is NULL")
        cdef int count = GDALRATGetRowCount(self._hRAT)
        return count

    cdef int _get_column_count(self):
        if self._hRAT == NULL:
            raise ValueError("Raster attribute table is NULL")
        return GDALRATGetColumnCount(self._hRAT)

    cdef int _get_column_index(self, str name):

        cdef int i

        for i in range(self._get_column_count()):
            if GDALRATGetNameOfCol(self._hRAT, i) == name:
                return i
        return -1
    
    cdef char * _get_column_name(self, const int index):
        return GDALRATGetNameOfCol(self._hRAT, index)

    cdef GDALRATFieldType _get_column_type(self, int index):
        if index < 0:
            raise AttributeError("Invalid column index")
        
        return GDALRATGetTypeOfCol(self._hRAT, index)
        
    cdef int _create_column(self,
        const char * column_name,
        const GDALRATFieldType column_type,
        const GDALRATFieldUsage column_usage):

        GDALRATCreateColumn(
            self._hRAT,
            column_name,
            column_type,
            column_usage
        )

        return self._get_column_count()-1

    cdef _get_string_column(
        self,
        int column_index,
        int start_row,
        int end_row):
        """String columns require special handling"""
        # https://github.com/OSGeo/gdal/blob/a599c264fc26c9f183c526b3a8dbba6a61e57c61/swig/include/gdal_array.i#L2217

        cdef int array_length = self._get_row_count()
        cdef char **papszStringList = <char **>CPLCalloc(sizeof(char*), array_length)

        GDALRATValuesIOAsString(
            self._hRAT,
            GF_Read,
            column_index,
            0,
            array_length,
            papszStringList
        )

        tmp = [r for r in papszStringList[:array_length]]
        arr = np.array(tmp, dtype=str)
        CPLFree(papszStringList)
        return arr

    def _new_hRAT(self):
        self._create()

    def _get_column(
        self,
        column_index: int | str,
        start_row: int = None,
        end_row: int = None):

        if isinstance(column_index, str):
            # Convert from column name to integer index
            column_index = column_index.encode('utf-8')
        
        if isinstance(column_index, bytes):
            column_index = self._get_column_index(column_index)
        elif isinstance(column_index, int):
            pass
        else:
            raise AttributeError(f'column_index must for str or int, got {type(column_index)}')

        if 0 > column_index > self._get_column_count():
            raise AttributeError(f'Column with index {column_index} does not exist')
        # Return a subset of the column if specified
        start_row = start_row or 0
        end_row = end_row or self._get_row_count()

        column_type = self._get_column_type(column_index)

        # Initialize an empty np array to be returned

        retval = np.empty(
            end_row-start_row,
            dtype=numpy_types[column_type]
        )

        if column_type == GFT_Integer:
            GDALRATValuesIOAsInteger(
                self._hRAT,
                GF_Read,
                column_index,
                start_row,
                end_row,
                <int *>np.PyArray_DATA(retval)
            )
        elif column_type == GFT_Real:
            GDALRATValuesIOAsDouble(
                self._hRAT,
                GF_Read,
                column_index,
                start_row,
                end_row,
                <double *>np.PyArray_DATA(retval)
            )
        elif column_type == GFT_String:
            retval = self._get_string_column(
                column_index,
                start_row=start_row,
                end_row=end_row
            )
        else:
            raise ValueError(f"Column {column_index} is not a valid type")
        
        return retval

    def shape(self):
        return self._get_row_count(), self._get_column_count()
    
    def columns(self):
        
        retval = []
        for ix in range(self._get_column_count()):
            retval.append(self._get_column_name(ix).decode())
        
        return retval
    
    def TEST(self, arr):

        # cdef int *val = [1,1,1,1,1,1,1,1,1,1,1,1]

        # cdef int *val = <int*>np.PyArray_DATA(np.array([2,2,2,2,2,2,2,2,2,2,2,2]))
        cdef int *val = <int*>np.PyArray_DATA(arr)
        

        GDALRATValuesIOAsInteger(
            self._hRAT,
            GF_Write,
            0,
            0,
            12,
            val
        )


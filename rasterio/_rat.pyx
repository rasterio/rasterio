import numpy as np
cimport numpy as np

from rasterio.rat import (
    numpy_types,
    Column
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
        """Return one or more columns from the RAT as a list of
        rasterio.rat.Column objects.
        """

        column_indexes = self._parse_column_index(ix)
        retval = []
        for i in column_indexes:
            # Collect the columns and package into a list of Column objects
            retval.append(
                Column(
                    name=self._get_column_name(i).decode('utf-8'),
                    field_type=self._get_column_type(i),
                    field_usage=self._get_column_usage(i),
                    values=self._get_column_values(i)
                )
            )

        return retval

    def __setitem__(self, ix, col):
        """Set one or more columns in the RAT from rasterio.rat.Column object(s).
        """

        cdef int *val
        cdef int array_len

        column_indexes = self._parse_column_index(ix)


        for i in column_indexes:
            if i == -1:
                # Create a new column if it doesn't exist
                ix = self._create_column(
                    col.name.encode('utf-8'),
                    col.field_type,
                    col.usage
                )

                self._set_column_values(
                    ix,
                    col
                )

    @staticmethod
    cdef RATBase clone(GDALRasterAttributeTableH rat_ptr):
        """Set the raster attribute table as a clone of an existing hRAT.
        Use this function when creating a RAT object from an existing raster file.
        """

        cdef RATBase rat_wrapper = RATBase.__new__(RATBase)

        if rat_wrapper._hRAT != NULL:
            raise ValueError("RAT Handle already exists, cannot clone")

        rat_wrapper._hRAT = GDALRATClone(rat_ptr)

        if rat_wrapper._hRAT == NULL:
            raise ValueError("RAT handle failed to clone")
        
        return rat_wrapper
    
    cdef void create(self):
        """Create a new hRAT empty object.
        Use this function when creating a RAT object from scratch.
        """
        if self._hRAT == NULL:
            self._hRAT = GDALCreateRasterAttributeTable()
        else:
            raise ValueError("RAT Handle already exists, cannot create a new one")

    def _create(self):
        self.create()

    def _parse_column_index(self, ix):
        """Return the integer index of the column(s) specified by ix.
        ix can be a string, bytes, int, or a collection of those types.
        """

        if isinstance(ix, (str, bytes, int)):
            # Single column by or integer
            ix = [ix]

        elif isinstance(ix, slice):
            # Slice of columns
            ix = list(
                range( *ix.indices( self._get_column_count()))
            )
        elif isinstance(ix, (list, tuple, set)):
            # Collection of columns
            ix = list(ix)
        else:
            raise AttributeError(f"Index {ix} of type {type(ix)} not recognized. Pass a string, bytes, int, or collection of those types.")

        # Convert column identifies to a list of integer indexes
        column_indexes = []
        for index in ix:
            if isinstance(index, str):
                column_indexes.append(self._get_column_index(index))
            elif isinstance(index, bytes):
                column_indexes.append(self._get_column_index(index.decode()))
            elif isinstance(index, int):

                if index < 0:
                    raise ValueError(f"Index cannot be negative: {index}")
                elif index > self._get_column_count():
                    raise ValueError(f"Index cannot be greater than the number of columns: {index}")

                column_indexes.append(index)
            else:
                raise AttributeError(f'Column indexes must be integers or string, got {type(index)}')

        return column_indexes

    cdef int _get_row_count(self):
        """Return the number of rows in the attribute table
        """
        if self._hRAT == NULL:
            raise ValueError("Raster attribute table is NULL")
        cdef int count = GDALRATGetRowCount(self._hRAT)
        return count

    cdef int _get_column_count(self):
        """Return the number of columns in the attribute table
        """
        if self._hRAT == NULL:
            raise ValueError("Raster attribute table is NULL")
        return GDALRATGetColumnCount(self._hRAT)

    cdef int _get_column_index(self, str name):
        """Return the integer index of a column from its name.
        If the column name does not exist, returns -1.

        Parameters
        ----------

        name : str
            Column name as a unicode string

        Returns 
        -------
        int
        """

        cdef int i

        for i in range(self._get_column_count()):
            if GDALRATGetNameOfCol(self._hRAT, i) == name:
                return i
        return -1
    
    cdef char * _get_column_name(self, const int index):
        """Returns the column name based on the index.

        Parameters
        ----------
        index: int
            Column index
        
        Returns
        -------
        char
        """
        return GDALRATGetNameOfCol(self._hRAT, index)

    cdef GDALRATFieldUsage _get_column_usage(self, int index):
        """Return the usage designation of a column by index.

        Parameters
        ----------
        index: int

        Returns
        -------
        GDALRATFieldType
        """

        if index < 0:
            raise AttributeError("Invalid column index")
        
        return GDALRATGetUsageOfCol(self._hRAT, index)


    cdef GDALRATFieldType _get_column_type(self, int index):
        """Return the type of a column by index.

        Parameters
        ----------
        index: int

        Returns
        -------
        GDALRATFieldType
        """

        if index < 0:
            raise AttributeError("Invalid column index")
        
        return GDALRATGetTypeOfCol(self._hRAT, index)
        
    cdef int _create_column(self,
        const char * column_name,
        const GDALRATFieldType column_type,
        const GDALRATFieldUsage column_usage):
        """Create a new column in the raster attribute table
        Returns the index of the newly created column

        Parameters
        ----------

        column_name: char
            Name of the column
        column_type: GDALRATFieldType
            Data type of the column
        column_usage: GDALRATFieldUsage
            Usage designation for the column
        
        Returns
        -------

        int
        
        """

        GDALRATCreateColumn(
            self._hRAT,
            column_name,
            column_type,
            column_usage
        )

        return self._get_column_count()-1


    cdef _get_string_column( self, int column_index, int start_row, int end_row):
        """Returns a string column as a numpy array. String datatypes require
        special handling to determine the dtype based on the maximum length
        of string values in the column.

        Parameters
        ----------

        column_index: int
            Index of the column to return

        Returns
        -------
        np.array
        """

        cdef int array_length = self._get_row_count()
        cdef char **papszStringList = <char **>CPLCalloc(sizeof(char*), array_length)

        GDALRATValuesIOAsString(
            self._hRAT,
            GF_Read,
            column_index,
            start_row,
            end_row,
            papszStringList
        )

        tmp = [r for r in papszStringList[:array_length]]
        arr = np.array(tmp, dtype=str)
        CPLFree(papszStringList)
        return arr

    def _get_column_values(self, column_index: int):
        """Return column values as a numpy array.

        Parameters
        ----------
        column_index: int
            Index of the column to return
        
        Returns
        -------
        np.array
        """
        
        if not isinstance(column_index, int):
            raise AttributeError(f'column_index must be an int, got {type(column_index)}: {column_index}')

        if 0 > column_index > self._get_column_count():
            raise AttributeError(f'Column with index {column_index} does not exist')

        # Return a subset of the column if specified
        start_row = 0
        end_row = self._get_row_count()

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
    
    def _set_column_values( self, column_index: int, col: Column):
        """Set the values of an existing column.

        Parameters
        ----------
        column_index: int
            Index of the column to return
        
        Returns
        -------

        rasterio.Column
        
        """
        
        if not isinstance(column_index, int):
            raise AttributeError(f'column_index must be an int, got {type(column_index)}: {column_index}')

        if 0 > column_index > self._get_column_count():
            raise AttributeError(f'Column with index {column_index} does not exist')
        
        assert col.column_type == self._get_column_type(column_index)
        assert col.column_usage == self._get_column_usage(column_index)

        start_row = 0
        end_row = self._get_row_count()

        if col.column_type == GFT_Integer:
            GDALRATValuesIOAsInteger(
                self._hRAT,
                GF_Read,
                column_index,
                start_row,
                end_row,
                <int *>np.PyArray_DATA(col.values)
            )
        elif col.column_type == GFT_Real:
            GDALRATValuesIOAsDouble(
                self._hRAT,
                GF_Read,
                column_index,
                start_row,
                end_row,
                <double *>np.PyArray_DATA(col.values)
            )
        elif col.column_type == GFT_String:
            GDALRATValuesIOAsString(
                self._hRAT,
                GF_Read,
                column_index,
                start_row,
                end_row,
                <char **>np.PyArray_DATA(col.values)
            )
        else:
            raise ValueError(f"Column {column_index} is not a valid type")

    def shape(self):
        """Returns the dimensions of the Raster Attribute Table
        """
        return self._get_row_count(), self._get_column_count()
    
    def columns(self):
        """Returns a of names of the Raster Attribute Table columns"""
        
        retval = []
        for ix in range(self._get_column_count()):
            retval.append(self._get_column_name(ix).decode())
        
        return retval
    
    def to_numpy(self):
        """Returns the Raster Attribute Table as a numpy array"""
        col_count = range(self._get_column_count())

        retval = np.rec.fromarrays(
            [self._get_column_values(ix) for ix in col_count],
            names=[self._get_column_name(ix).decode() for ix in col_count]
        )

        return retval
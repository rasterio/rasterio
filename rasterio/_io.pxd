include "gdal.pxi"

cimport numpy as np

from rasterio._base cimport DatasetBase


cdef class DatasetReaderBase(DatasetBase):
    pass


cdef class DatasetWriterBase(DatasetReaderBase):
    cdef readonly object _init_dtype
    cdef readonly object _init_nodata
    cdef readonly object _init_gcps
    cdef readonly object _options


cdef class BufferedDatasetWriterBase(DatasetWriterBase):
    pass


cdef class InMemoryRaster:
    cdef GDALDatasetH _hds
    cdef double gdal_transform[6]
    cdef int* band_ids
    cdef np.ndarray _image
    cdef object crs
    cdef object transform  # this is an Affine object.

    cdef GDALDatasetH handle(self) except NULL
    cdef GDALRasterBandH band(self, int) except NULL


cdef class MemoryFileBase:
    cdef VSILFILE * _vsif

cdef class VSIFileBase:
    cdef VSILFILE * _vsif

ctypedef np.uint8_t DTYPE_UBYTE_t
ctypedef np.uint16_t DTYPE_UINT16_t
ctypedef np.int16_t DTYPE_INT16_t
ctypedef np.uint32_t DTYPE_UINT32_t
ctypedef np.int32_t DTYPE_INT32_t
ctypedef np.float32_t DTYPE_FLOAT32_t
ctypedef np.float64_t DTYPE_FLOAT64_t


cdef bint in_dtype_range(value, dtype)

cdef int io_auto(image, GDALRasterBandH band, bint write, int resampling=*) except -1

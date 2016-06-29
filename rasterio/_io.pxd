cimport numpy as np

from rasterio cimport _base

include "gdal.pxi"


cdef class DatasetReaderBase(_base.DatasetBase):
    # Read-only access to raster data and metadata.
    pass


cdef class DatasetWriterBase(DatasetReaderBase):
    # Read-write access to raster data and metadata.
    cdef readonly object _init_dtype
    cdef readonly object _init_nodata
    cdef readonly object _options


cdef class BufferedDatasetWriterBase(DatasetWriterBase):
    pass


cdef class InMemoryRaster:
    cdef GDALDatasetH dataset
    cdef GDALRasterBandH band
    cdef double transform[6]
    cdef int band_ids[1]
    cdef np.ndarray _image
    cdef object crs


ctypedef np.uint8_t DTYPE_UBYTE_t
ctypedef np.uint16_t DTYPE_UINT16_t
ctypedef np.int16_t DTYPE_INT16_t
ctypedef np.uint32_t DTYPE_UINT32_t
ctypedef np.int32_t DTYPE_INT32_t
ctypedef np.float32_t DTYPE_FLOAT32_t
ctypedef np.float64_t DTYPE_FLOAT64_t


cdef bint in_dtype_range(value, dtype)


cdef int io_ubyte(
        void *hband, 
        int mode, 
        int xoff, 
        int yoff, 
        int width, 
        int height, 
        np.uint8_t[:, :] buffer)


cdef int io_uint16(
        void *hband, 
        int mode, 
        int xoff, 
        int yoff, 
        int width, 
        int height,
        np.uint16_t[:, :] buffer)


cdef int io_int16(
        void *hband, 
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height, 
        np.int16_t[:, :] buffer)

cdef int io_uint32(
        void *hband, 
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height, 
        np.uint32_t[:, :] buffer)

cdef int io_int32(
        void *hband, 
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height, 
        np.int32_t[:, :] buffer)

cdef int io_float32(
        void *hband, 
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height, 
        np.float32_t[:, :] buffer)

cdef int io_float64(
        void *hband,
        int mode,
        int xoff,
        int yoff,
        int width, 
        int height, 
        np.float64_t[:, :] buffer)

cdef int io_multi_ubyte(
        void *hds, 
        int mode, 
        int xoff, 
        int yoff, 
        int width, 
        int height, 
        np.uint8_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil

cdef int io_multi_uint16(
        void *hds, 
        int mode, 
        int xoff, 
        int yoff, 
        int width, 
        int height, 
        np.uint16_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil

cdef int io_multi_int16(
        void *hds, 
        int mode, 
        int xoff, 
        int yoff, 
        int width, 
        int height, 
        np.int16_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil

cdef int io_multi_uint32(
        void *hds, 
        int mode, 
        int xoff, 
        int yoff, 
        int width, 
        int height, 
        np.uint32_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil

cdef int io_multi_int32(
        void *hds, 
        int mode, 
        int xoff, 
        int yoff, 
        int width, 
        int height, 
        np.int32_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil

cdef int io_multi_float32(
        void *hds, 
        int mode, 
        int xoff, 
        int yoff, 
        int width, 
        int height, 
        np.float32_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil

cdef int io_multi_float64(
        void *hds, 
        int mode, 
        int xoff, 
        int yoff, 
        int width, 
        int height, 
        np.float64_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil

cdef int io_multi_cint16(
        void *hds, 
        int mode, 
        int xoff, 
        int yoff, 
        int width, 
        int height, 
        np.complex_t[:, :, :] out,
        long[:] indexes,
        int count)

cdef int io_multi_cint32(
        void *hds, 
        int mode, 
        int xoff, 
        int yoff, 
        int width, 
        int height, 
        np.complex_t[:, :, :] out,
        long[:] indexes,
        int count)

cdef int io_multi_cfloat32(
        void *hds, 
        int mode, 
        int xoff, 
        int yoff, 
        int width, 
        int height, 
        np.complex64_t[:, :, :] out,
        long[:] indexes,
        int count)

cdef int io_multi_cfloat64(
        void *hds, 
        int mode, 
        int xoff, 
        int yoff, 
        int width, 
        int height, 
        np.complex128_t[:, :, :] out,
        long[:] indexes,
        int count)

cdef int io_auto(image, void *hband, bint write)

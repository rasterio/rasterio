cimport numpy as np

from rasterio._base cimport DatasetBase

include "gdal.pxi"


cdef class DatasetReaderBase(DatasetBase):
    pass


cdef class DatasetWriterBase(DatasetReaderBase):
    cdef readonly object _init_dtype
    cdef readonly object _init_nodata
    cdef readonly object _init_units
    cdef readonly object _init_description
    cdef readonly object _options


cdef class BufferedDatasetWriterBase(DatasetWriterBase):
    pass


cdef class InMemoryRaster:
    cdef GDALDatasetH _hds
    cdef double transform[6]
    cdef int band_ids[1]
    cdef np.ndarray _image
    cdef object crs

    cdef GDALDatasetH handle(self) except NULL
    cdef GDALRasterBandH band(self, int) except NULL


ctypedef np.uint8_t DTYPE_UBYTE_t
ctypedef np.uint16_t DTYPE_UINT16_t
ctypedef np.int16_t DTYPE_INT16_t
ctypedef np.uint32_t DTYPE_UINT32_t
ctypedef np.int32_t DTYPE_INT32_t
ctypedef np.float32_t DTYPE_FLOAT32_t
ctypedef np.float64_t DTYPE_FLOAT64_t


cdef bint in_dtype_range(value, dtype)


cdef int io_ubyte(
        GDALRasterBandH band,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.uint8_t[:, :] buffer)


cdef int io_uint16(
        GDALRasterBandH band,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.uint16_t[:, :] buffer)


cdef int io_int16(
        GDALRasterBandH band,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.int16_t[:, :] buffer)


cdef int io_uint32(
        GDALRasterBandH band,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.uint32_t[:, :] buffer)


cdef int io_int32(
        GDALRasterBandH band,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.int32_t[:, :] buffer)


cdef int io_float32(
        GDALRasterBandH band,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.float32_t[:, :] buffer)


cdef int io_float64(
        GDALRasterBandH band,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.float64_t[:, :] buffer)


cdef int io_multi_ubyte(
        GDALDatasetH hds,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.uint8_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil


cdef int io_multi_uint16(
        GDALDatasetH hds,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.uint16_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil


cdef int io_multi_int16(
        GDALDatasetH hds,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.int16_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil


cdef int io_multi_uint32(
        GDALDatasetH hds,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.uint32_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil


cdef int io_multi_int32(
        GDALDatasetH hds,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.int32_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil


cdef int io_multi_float32(
        GDALDatasetH hds,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.float32_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil


cdef int io_multi_float64(
        GDALDatasetH hds,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.float64_t[:, :, :] buffer,
        long[:] indexes,
        int count) nogil


cdef int io_multi_cint16(
        GDALDatasetH hds,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.complex_t[:, :, :] out,
        long[:] indexes,
        int count)


cdef int io_multi_cint32(
        GDALDatasetH hds,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.complex_t[:, :, :] out,
        long[:] indexes,
        int count)


cdef int io_multi_cfloat32(
        GDALDatasetH hds,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.complex64_t[:, :, :] out,
        long[:] indexes,
        int count)


cdef int io_multi_cfloat64(
        GDALDatasetH hds,
        int mode,
        int xoff,
        int yoff,
        int width,
        int height,
        np.complex128_t[:, :, :] out,
        long[:] indexes,
        int count)


cdef int io_auto(image, GDALRasterBandH band, bint write)

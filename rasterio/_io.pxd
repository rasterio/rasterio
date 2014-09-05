cimport numpy as np

from rasterio cimport _base


cdef extern from "gdal.h":

    ctypedef enum GDALDataType:
        GDT_Unknown
        GDT_Byte
        GDT_UInt16
        GDT_Int16
        GDT_UInt32
        GDT_Int32
        GDT_Float32
        GDT_Float64
        GDT_CInt16
        GDT_CInt32
        GDT_CFloat32
        GDT_CFloat64
        GDT_TypeCount

    ctypedef enum GDALAccess:
        GA_ReadOnly
        GA_Update

    ctypedef enum GDALRWFlag:
        GF_Read
        GF_Write


cdef class RasterReader(_base.DatasetReader):
    # Read-only access to raster data and metadata.
    pass

cdef class RasterUpdater(RasterReader):
    # Read-write access to raster data and metadata.
    cdef readonly object _init_dtype
    cdef readonly object _init_nodata
    cdef readonly object _options


ctypedef np.uint8_t DTYPE_UBYTE_t
ctypedef np.uint16_t DTYPE_UINT16_t
ctypedef np.int16_t DTYPE_INT16_t
ctypedef np.uint32_t DTYPE_UINT32_t
ctypedef np.int32_t DTYPE_INT32_t
ctypedef np.float32_t DTYPE_FLOAT32_t
ctypedef np.float64_t DTYPE_FLOAT64_t

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


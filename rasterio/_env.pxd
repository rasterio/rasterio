include "gdal.pxi"


cdef class ConfigEnv:
    cdef public object options


cdef class GDALEnv(ConfigEnv):
    cdef public object _have_registered_drivers

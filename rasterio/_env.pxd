# cython: language_level=3

cdef class ConfigEnv(object):
    cdef public object options


cdef class GDALEnv(ConfigEnv):
    cdef public object _have_registered_drivers

cdef class ConfigEnv(object):
    cdef public object options


cdef class GDALEnv(ConfigEnv):
    cdef object _have_registered_drivers

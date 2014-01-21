# The GDAL and OGR driver registry.
# GDAL driver management.

cdef extern from "gdal.h":
    void GDALAllRegister()
    void GDALDestroyDriverManager()
    int GDALGetDriverCount()

cdef extern from "ogr_api.h":
    void OGRRegisterAll()
    void OGRCleanupAll()
    int OGRGetDriverCount()

import logging


log = logging.getLogger('rasterio')
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())


def driver_count():
    return GDALGetDriverCount() + OGRGetDriverCount()


class DummyManager(object):
    
    def __enter__(self):
        pass

    def __exit__(self, *args):
        pass


cdef class DriverManager(object):
    
    def __enter__(self):
        GDALAllRegister()
        OGRRegisterAll()
        if driver_count() == 0:
            raise ValueError("Drivers not registered")
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        GDALDestroyDriverManager()
        OGRCleanupAll()
        if driver_count() != 0:
            raise ValueError("Drivers not de-registered")


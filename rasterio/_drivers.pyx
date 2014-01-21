# The GDAL and OGR driver registry.

from rasterio cimport _gdal, _ogr

cdef void _registerall():
    _gdal.GDALAllRegister()
    _ogr.OGRRegisterAll()

cdef void _unregisterall():
    _gdal.GDALDestroyDriverManager()
    _ogr.OGRCleanupAll()


class DriverManager(object):
    
    def __enter__(self):
        _registerall()
        return self

    def __exit__(self, exc_type=None, exc_val=None, exc_tb=None):
        _unregisterall()


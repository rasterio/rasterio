"""Tests of GDAL and PROJ data finding"""
from rasterio._env import GDALDataFinder, PROJDataFinder


def test_gdal_data_find_file():
    """Find_file shouldn't raise any exceptions"""
    GDALDataFinder().find_file("header.dxf")


def test_proj_data_has_data():
    """has_data shouldn't raise any exceptions"""
    PROJDataFinder().has_data()

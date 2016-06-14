from rasterio._base import driver_can_create, driver_can_create_copy


def test_driver_cap_tiff():
    """GTiff can CREATE and CREATE COPY"""
    assert driver_can_create('GTiff')
    assert driver_can_create_copy('GTiff')


def test_driver_cap_jpeg():
    """JPEG can CREATE COPY, not CREATE"""
    assert not driver_can_create('JPEG')
    assert driver_can_create_copy('JPEG')

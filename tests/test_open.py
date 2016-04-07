import pytest
import rasterio


def test_open_bad_path():
    with pytest.raises(TypeError):
        rasterio.open(3.14)


def test_open_bad_mode():
    with pytest.raises(TypeError):
        rasterio.open("tests/data/RGB.byte.tif", mode=3.14)

    with pytest.raises(ValueError):
        rasterio.open("tests/data/RGB.byte.tif", mode="foo")


def test_open_bad_driver():
    with pytest.raises(TypeError):
        rasterio.open("tests/data/RGB.byte.tif", mode="r", driver=3.14)

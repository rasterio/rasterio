import pytest
import rasterio


def test_open_bad_path():
    with pytest.raises(TypeError):
        rasterio.open(3.14)


def test_open_bad_mode_1():
    with pytest.raises(TypeError):
        rasterio.open("tests/data/RGB.byte.tif", mode=3.14)


def test_open_bad_mode_2():
    with pytest.raises(ValueError):
        rasterio.open("tests/data/RGB.byte.tif", mode="foo")


def test_open_bad_driver():
    with pytest.raises(TypeError):
        rasterio.open("tests/data/RGB.byte.tif", mode="r", driver=3.14)


def test_open_pathlib_path():
    try:
        from pathlib import Path
    except ImportError:
        return
    tif = Path.cwd() / 'tests' / 'data' / 'RGB.byte.tif'
    with rasterio.open(tif) as src:
        assert src.count == 3

from rasterio._show_versions import (
    _get_deps_info,
    _get_gdal_info,
    _get_sys_info,
    show_versions,
)


def test_get_gdal_info():
    yagdal_info = _get_gdal_info()
    assert "rasterio" in yagdal_info
    assert "GDAL" in yagdal_info
    assert "PROJ" in yagdal_info
    assert "GEOS" in yagdal_info
    assert "PROJ DATA" in yagdal_info
    assert "GDAL DATA" in yagdal_info


def test_get_sys_info():
    sys_info = _get_sys_info()

    assert "python" in sys_info
    assert "executable" in sys_info
    assert "machine" in sys_info


def test_get_deps_info():
    deps_info = _get_deps_info()

    assert "affine" in deps_info
    assert "attrs" in deps_info
    assert "certifi" in deps_info
    assert "click" in deps_info
    assert "click-plugins" in deps_info
    assert "cligj" in deps_info
    assert "cython" in deps_info
    assert "numpy" in deps_info
    assert "setuptools" in deps_info
    assert "snuggs" in deps_info


def test_show_versions_with_gdal(capsys):
    show_versions()
    out, err = capsys.readouterr()
    assert "System" in out
    assert "python" in out
    assert "GDAL" in out
    assert "Python deps" in out

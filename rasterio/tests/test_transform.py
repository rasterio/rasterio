
import rasterio
from rasterio.coords import AffineMatrix

def test_gdal():
    t = AffineMatrix.from_gdal(-237481.5, 425.0, 0.0, 237536.4, 0.0, -425.0)
    assert t.c == t.xoff == -237481.5
    assert t.a == 425.0
    assert t.b == 0.0
    assert t.f == t.yoff ==  237536.4
    assert t.d == 0.0
    assert t.e == -425.0
    assert tuple(t) == (425.0, 0.0, -237481.5, 0.0, -425.0, 237536.4)
    assert t.to_gdal() == (-237481.5, 425.0, 0.0, 237536.4, 0.0, -425.0)

def test_window():
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        left, bottom, right, top = src.bounds
        assert src.window(left, bottom, right, top) == ((0, src.height),
                                                        (0, src.width))
        assert src.window(left, top-src.res[1], left+src.res[0], top) == (
            (0, 1), (0, 1))
        # TODO what about fractional windows?

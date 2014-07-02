
import rasterio
from rasterio.enums import ColorInterp


def test_colorinterp(tmpdir):
    
    with rasterio.drivers():

        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
            r, g, b = map(src.read_band, (1, 2, 3))
            meta = src.meta
            
            assert src.colorinterp(1) == ColorInterp.red
            assert src.colorinterp(2) == ColorInterp.green
            assert src.colorinterp(3) == ColorInterp.blue



import rasterio
from rasterio.enums import ColorInterp


def test_colorinterp(tmpdir):
    
    with rasterio.drivers():

        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
            assert src.colorinterp(1) == ColorInterp.red
            assert src.colorinterp(2) == ColorInterp.green
            assert src.colorinterp(3) == ColorInterp.blue
            
        tiffname = str(tmpdir.join('foo.tif'))
        
        meta = src.meta
        meta['photometric'] = 'CMYK'
        meta['count'] = 4
        with rasterio.open(tiffname, 'w', **meta) as dst:
            assert dst.colorinterp(1) == ColorInterp.cyan
            assert dst.colorinterp(2) == ColorInterp.magenta
            assert dst.colorinterp(3) == ColorInterp.yellow
            assert dst.colorinterp(4) == ColorInterp.black


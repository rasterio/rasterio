
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
            
        tiffname = str(tmpdir.join('foo.tif'))
        
        with rasterio.open(tiffname, 'w', **meta) as dst:
            dst.write_band(1, r)
            dst.write_band(2, g)
            dst.write_band(3, b)
            
            dst.write_colorinterp(1, ColorInterp.gray)
            dst.write_colorinterp(2, ColorInterp.grey)
            dst.write_colorinterp(3, ColorInterp.gray)
            
            assert dst.colorinterp(1) == ColorInterp.gray
            assert dst.colorinterp(2) == ColorInterp.grey
            assert dst.colorinterp(3) == ColorInterp.gray
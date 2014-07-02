import rasterio

def test_colorinterp(tmpdir):
    
    with rasterio.drivers():

        with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
            r, g, b = map(src.read_band, (1, 2, 3))
            meta = src.meta
            
            assert src.colorinterp(1) == 3
            assert src.colorinterp(2) == 4
            assert src.colorinterp(3) == 5
            
        tiffname = str(tmpdir.join('foo.tif'))
        
        with rasterio.open(tiffname, 'w', **meta) as dst:
            dst.write_band(1, r)
            dst.write_band(2, g)
            dst.write_band(3, b)
            
            dst.write_colorinterp(1, 1)
            dst.write_colorinterp(2, 1)
            dst.write_colorinterp(3, 1)
            
            assert dst.colorinterp(1) == 1
            assert dst.colorinterp(2) == 1
            assert dst.colorinterp(3) == 1
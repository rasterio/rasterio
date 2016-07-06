# You should be able to write rasters with no georeferencing, e.g., plain old
# PNGs and JPEGs.

import rasterio


def test_write(tmpdir):
    name = str(tmpdir.join("test.png"))
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        kwargs = src.meta.copy()
        del kwargs['transform']
        del kwargs['crs']
        kwargs['driver'] = 'PNG'
        with rasterio.open(name, 'w', **kwargs) as dst:
            dst.write(src.read())


def test_read_write(tmpdir):
    tif1 = str(tmpdir.join("test.tif"))
    tif2 = str(tmpdir.join("test2.tif"))
    with rasterio.open('tests/data/RGB.byte.tif') as src:
        kwargs = src.meta.copy()
        del kwargs['transform']
        del kwargs['crs']
        with rasterio.open(tif1, 'w', **kwargs) as dst:
            dst.write(src.read())
    with rasterio.open(tif1) as src, rasterio.open(tif2, 'w', **src.meta) as dst:
        dst.write(src.read())

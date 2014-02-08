
import pytest
import rasterio

def test_tags_read():
    with rasterio.open('rasterio/tests/data/RGB.byte.tif') as src:
        assert src.tags() == {'AREA_OR_POINT': 'Area'}
        assert src.tags(domain='IMAGE_STRUCTURE') == {'INTERLEAVE': 'PIXEL'}
        assert 'STATISTICS_MAXIMUM' in src.tags(1)

def test_tags_update(tmpdir):
    tiffname = str(tmpdir.join('foo.tif'))
    with rasterio.open(
            tiffname, 
            'w', 
            driver='GTiff', 
            count=1, 
            dtype=rasterio.uint8, 
            width=10, 
            height=10) as dst:
        dst.update_tags(a='1', b='2')
        dst.update_tags(1, c=3)
        assert dst.tags() == {'a': '1', 'b': '2'}
        assert dst.tags(1) == {'c': '3'}

    with rasterio.open(tiffname) as src:
        assert src.tags() == {'a': '1', 'b': '2'}
        assert src.tags(1) == {'c': '3'}


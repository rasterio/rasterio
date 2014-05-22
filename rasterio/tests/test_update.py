
import shutil
import subprocess
import re
import numpy
import pytest

import rasterio

def test_update_tags(tmpdir):
    tiffname = str(tmpdir.join('foo.tif'))
    shutil.copy('rasterio/tests/data/RGB.byte.tif', tiffname)
    with rasterio.open(tiffname, 'r+') as f:
        f.update_tags(a='1', b='2')
        f.update_tags(1, c=3)
        with pytest.raises(ValueError):
            f.update_tags(4, d=4)
        assert f.tags() == {'AREA_OR_POINT': 'Area', 'a': '1', 'b': '2'}
        assert ('c', '3') in f.tags(1).items()
    info = subprocess.check_output(["gdalinfo", tiffname]).decode('utf-8')
    assert re.search("Metadata:\W+a=1\W+AREA_OR_POINT=Area\W+b=2", info)

def test_update_band(tmpdir):
    tiffname = str(tmpdir.join('foo.tif'))
    shutil.copy('rasterio/tests/data/RGB.byte.tif', tiffname)
    with rasterio.open(tiffname, 'r+') as f:
        f.write_band(1, numpy.zeros(f.shape, dtype=f.dtypes[0]))
    with rasterio.open(tiffname) as f:
        assert not f.read_band(1).any()

def test_update_spatial(tmpdir):
    tiffname = str(tmpdir.join('foo.tif'))
    shutil.copy('rasterio/tests/data/RGB.byte.tif', tiffname)
    with rasterio.open(tiffname, 'r+') as f:
        f.transform = rasterio.AffineMatrix.from_gdal(1.0, 1.0, 0.0, 0.0, 0.0, -1.0)
        f.crs = {'+init': 'epsg:4326'}
    with rasterio.open(tiffname) as f:
        assert list(f.transform.to_gdal()) == [1.0, 1.0, 0.0, 0.0, 0.0, -1.0]
        assert f.crs == {
            u'datum': u'WGS84', u'no_defs': True, u'proj': u'longlat'}

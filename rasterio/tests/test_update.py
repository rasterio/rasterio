
import shutil
import subprocess

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
    info = subprocess.check_output(["gdalinfo", tiffname])
    assert "Metadata:\n  a=1\n" in info.decode('utf-8')


import logging
import subprocess
import sys
import re
import numpy
import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_write_ubyte(tmpdir):
    name = str(tmpdir.mkdir("sub").join("test_write_ubyte.png"))
    a = numpy.ones((100, 100), dtype=rasterio.ubyte) * 127
    with rasterio.open(
            name, 'w', 
            driver='PNG', width=100, height=100, count=1, 
            dtype=a.dtype) as s:
        s.write(a, indexes=1)
    info = subprocess.check_output(["gdalinfo", "-stats", name]).decode('utf-8')
    assert "Minimum=127.000, Maximum=127.000, Mean=127.000, StdDev=0.000" in info

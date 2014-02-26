import logging
import sys

import rasterio
from rasterio._drivers import driver_count, GDALEnv

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_drivers():
    with rasterio.drivers() as m:
        assert driver_count() > 0
        assert type(m) == GDALEnv
        
        n = rasterio.drivers()
        assert driver_count() > 0
        assert type(n) == GDALEnv

def test_options(tmpdir):
    """Test that setting CPL_DEBUG=True results in GDAL debug messages.
    """
    logger = logging.getLogger('rasterio')
    logger.setLevel(logging.DEBUG)
    logfile = str(tmpdir.join('test_options.log'))
    fh = logging.FileHandler(logfile)
    logger.addHandler(fh)
    with rasterio.drivers(CPL_DEBUG=True):
        with rasterio.open("rasterio/tests/data/RGB.byte.tif") as src:
            pass
        log = open(logfile).read()
        assert "GDAL: GDALOpen(rasterio/tests/data/RGB.byte.tif" in log


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
    logger = logging.getLogger('GDAL')
    logger.setLevel(logging.DEBUG)
    logfile1 = str(tmpdir.join('test_options1.log'))
    fh = logging.FileHandler(logfile1)
    logger.addHandler(fh)
    
    # With CPL_DEBUG=True, expect debug messages from GDAL in
    # logfile1
    with rasterio.drivers(CPL_DEBUG=True):
        with rasterio.open("rasterio/tests/data/RGB.byte.tif") as src:
            pass

    log = open(logfile1).read()
    assert "GDAL: GDALOpen(rasterio/tests/data/RGB.byte.tif" in log
    
    # The GDAL env above having exited, CPL_DEBUG should be OFF.
    logfile2 = str(tmpdir.join('test_options2.log'))
    fh = logging.FileHandler(logfile2)
    logger.addHandler(fh)

    with rasterio.open("rasterio/tests/data/RGB.byte.tif") as src:
        pass
    
    # Expect no debug messages from GDAL.
    log = open(logfile2).read()
    assert "GDAL: GDALOpen(rasterio/tests/data/RGB.byte.tif" not in log


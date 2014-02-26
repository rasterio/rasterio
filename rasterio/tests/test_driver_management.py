import logging
import sys

import rasterio
from rasterio._drivers import driver_count, DriverManager, NonExitingDriverManager

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

def test_drivers():
    with rasterio.drivers() as m:
        assert driver_count() > 0
        assert type(m) == DriverManager
        
        n = rasterio.drivers()
        assert driver_count() > 0
        assert type(n) == NonExitingDriverManager


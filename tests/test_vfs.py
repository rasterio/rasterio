import logging
import sys

import rasterio


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_read_zip():
    with rasterio.open(
            '/RGB.byte.tif',
            vfs='zip://tests/data/files.zip') as src:
        assert src.name == '/vsizip/tests/data/files.zip/RGB.byte.tif'
        assert src.count == 3

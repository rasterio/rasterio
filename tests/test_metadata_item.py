#-*- coding: utf-8 -*-
import logging
import sys

import pytest
import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_get_metadata_item():
    with rasterio.open('tests/data/cogeo.tif') as src:
        assert src.get_metadata_item(1, 'IFD_OFFSET', 'TIFF') == '8'
        assert src.get_metadata_item(1, 'IFD_OFFSET', 'TIFF', ovr=1) == '1504'
        assert not src.get_metadata_item(1, 'IF', 'TIFF')

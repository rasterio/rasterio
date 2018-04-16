#-*- coding: utf-8 -*-
import logging
import sys

import pytest
import rasterio

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_get_tag_item():
    with rasterio.open('tests/data/cogeo.tif') as src:
        assert src.get_tag_item('INTERLEAVE', 'IMAGE_STRUCTURE') == 'PIXEL'
        assert src.get_tag_item('IFD_OFFSET', 'TIFF', bidx=1) == '8'
        assert src.get_tag_item('IFD_OFFSET', 'TIFF', bidx=1, ovr=1) == '1504'
        assert not src.get_tag_item('IF', 'TIFF', bidx=1)
        with pytest.raises(Exception):
            src.get_tag_item('IFD_OFFSET', 'TIFF', ovr=1)


def test_get_tag_item_noOverview():
    with rasterio.open('tests/data/rgb3.tif') as src:
        assert not src.get_tag_item('IFD_OFFSET', 'TIFF', bidx=1, ovr=1)

#-*- coding: utf-8 -*-
import logging
import sys

import pytest

import rasterio
from rasterio.errors import BandOverviewError

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)


def test_get_tag_item():
    with rasterio.open('tests/data/cogeo.tif') as src:
        assert src.get_tag_item('INTERLEAVE', 'IMAGE_STRUCTURE') == 'PIXEL'


def test_get_tag_item_Tiff():
    with rasterio.open('tests/data/cogeo.tif') as src:
        assert src.get_tag_item('IFD_OFFSET', 'TIFF', bidx=1) == '8'
        assert src.get_tag_item('IFD_OFFSET', 'TIFF', bidx=1, ovr=0) == '1104'
        assert src.get_tag_item('IFD_OFFSET', 'TIFF', bidx=1, ovr=1) == '1504'
        assert not src.get_tag_item('IF', 'TIFF', bidx=1)
        with pytest.raises(Exception):
            src.get_tag_item('IFD_OFFSET', 'TIFF', ovr=1)


def test_get_tag_item_noOverview():
    with rasterio.open('tests/data/rgb3.tif') as src:
        with pytest.raises(BandOverviewError):
            src.get_tag_item('IFD_OFFSET', 'TIFF', bidx=1, ovr=1)

#!/usr/bin/env python

from rasterio.rio.calc import calc
from rasterio.rio.cli import cli
from rasterio.rio.bands import stack
from rasterio.rio.features import shapes, rasterize
from rasterio.rio.info import env, info
from rasterio.rio.merge import merge
from rasterio.rio.rio import bounds, insp, transform
from rasterio.rio.sample import sample

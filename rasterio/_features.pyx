# cython: profile=True

import logging
import os
import os.path
import numpy as np
cimport numpy as np

from rasterio cimport _gdal
from rasterio import dtypes

log = logging.getLogger('rasterio')
class NullHandler(logging.Handler):
    def emit(self, record):
        pass
log.addHandler(NullHandler())


"""
Reproduces an issue where a deadlock occurred due to the GDAL thread pool which is not properly
cleaned up at fork. Rasterio includes an at fork hook to clear this thread pool in the parent before
forking.
"""

from multiprocessing import Process
from threading import Thread

import numpy as np
from affine import Affine

import rasterio
from rasterio import MemoryFile


def _create_in_memory_file():
    w, h, c = 100, 100, 3

    with MemoryFile() as memfile:
        with memfile.open(driver='GTiff',
                          dtype=rasterio.uint8,
                          count=c,
                          height=h,
                          width=w,
                          crs='epsg:3226',
                          compress='deflate',
                          transform=Affine.identity() * Affine.scale(0.5, -0.5),
                          num_threads='ALL_CPUS') as dst:
            dst.write(np.zeros((3, h, w), dtype=np.uint8))


def test_fork_after_write():
    # checks that even when GDAL was just used from another thread, the check should realize it and print an error
    t = Thread(target=_create_in_memory_file)
    t.start()
    t.join()

    p = Process(target=_create_in_memory_file)
    p.start()

    for try_idx in range(5):
        p.join(timeout=1)
        if p.exitcode is not None:
            assert p.exitcode == 0
    if p.exitcode is None:
        p.terminate()
        raise AssertionError("Child process did not terminate within 5 seconds. "
                             "It is very likely that a deadlock has occured!")

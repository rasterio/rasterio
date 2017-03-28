from threading import Thread
import time
import unittest

import rasterio as rio
from rasterio.env import get_gdal_config


class TestThreading(unittest.TestCase):
    def test_multiopen(self):
        """
        Open a file from different threads.

        Regression test for issue #986
        """

        def func(delay):
            try:
                with rio.open('tests/data/RGB.byte.tif'):
                    time.sleep(delay)
            except Exception as err:
                global exceptions
                exceptions.append(err)

        global exceptions
        exceptions = []

        t1 = Thread(target=func, args=(0.1,))
        t2 = Thread(target=func, args=(0,))

        with rio.Env():
            t1.start()
            t2.start()  # potential error if Env manages globals unsafely

            t1.join()
            t2.join()

        assert not exceptions

    def test_reliability(self):
        """Allow for nondeterminism of race condition"""
        for i in range(3):
            self.test_multiopen()


def test_child_thread_inherits_env():
    """A new thread inherit's the main thread's env"""
    def func():
        with rio.Env(lol='wut'):
            assert get_gdal_config('lol') == 'wut'
            # The next config option will have been set in the main thread.
            assert get_gdal_config('FROM_MAIN') is True

    t1 = Thread(target=func)

    with rio.Env(FROM_MAIN=True):
        t1.start()
        assert get_gdal_config('FROM_MAIN') is True
        assert get_gdal_config('lol') is None
        t1.join()


def test_child_thread_isolation():
    """Child threads have isolated environments"""
    def func(key, value, other_key):
        env = {key: value}
        with rio.Env(**env):
            assert get_gdal_config(key) == value
            # The other key is one set in another child thread.
            assert get_gdal_config(other_key) is None

    t1 = Thread(target=func, args=('is_t1', True, 'is_t2'))
    t2 = Thread(target=func, args=('is_t2', True, 'is_t1'))

    t1.start()
    t2.start()
    t1.join()
    t2.join()


if __name__ == '__main__':
    unittest.main()

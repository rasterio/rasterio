from threading import Thread
import time
import rasterio as rio
import unittest

class TestThreading(unittest.TestCase):
    def test_multiopen(self):
        """
        Open a file from different threads.

        Regression test for issue #986
        """

        def func(delay):
            try:
                with rio.open('tests/data/RGB.byte.tif') as src:
                    time.sleep(delay)
            except Exception as err:
                global exceptions
                exceptions.append(err)

        global exceptions
        exceptions = []

        t1 = Thread(target=func, args=(0.1,))
        t2 = Thread(target=func, args=(0,))

        t1.start()
        t2.start() # potential error if Env manages globals unsafely

        t1.join()
        t2.join()

        assert not exceptions

    def test_reliability(self):
        """Allow for nondeterminism of race condition"""
        for i in range(3):
            self.test_multiopen()

if __name__ == '__main__':
    unittest.main()

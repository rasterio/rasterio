from affine import Affine
import pytest

from rasterio.io import WindowMethodsMixin


class MockDatasetBase(object):
    def __init__(self):
        # from tests/data/RGB.byte.tif
        self.affine = Affine(300.0379266750948, 0.0, 101985.0,
                             0.0, -300.041782729805, 2826915.0)
        self.bounds = (101985.0, 2611485.0, 339315.0, 2826915.0)
        self.transform = self.affine
        self.height = 718
        self.width = 791


def test_windows_mixin():

    class MockDataset(MockDatasetBase, WindowMethodsMixin):
        pass

    src = MockDataset()
    assert src.window(*src.bounds) == ((0, src.height),
                                       (0, src.width))
    assert src.window_bounds(
        ((0, src.height),
         (0, src.width))) == src.bounds
    assert src.window_transform(
        ((0, src.height),
         (0, src.width))) == src.transform


def test_windows_mixin_fail():

    class MockDataset(WindowMethodsMixin):
        # doesn't inherit transform, height and width
        pass

    src = MockDataset()
    with pytest.raises(AttributeError):
        assert src.window(0, 0, 1, 1, boundless=True)
    with pytest.raises(AttributeError):
        assert src.window_bounds(((0, 1), (0, 1)))
    with pytest.raises(AttributeError):
        assert src.window_transform(((0, 1), (0, 1)))

from hypothesis import given
from hypothesis.strategies import composite, floats, integers

from rasterio import windows
from rasterio.coords import BoundingBox


class FakeDataset(windows.WindowMethodsMixin):
    """A test double to support testing of the mixin class"""

    def __init__(self, **kwargs):
        self.transform = kwargs.get('transform')
        self.height = kwargs.get('height')
        self.width = kwargs.get('width')

    @property
    def bounds(self):
        a, b, c, d, e, f, _, _, _ = self.transform
        return BoundingBox(c, f + e * self.height, c + a * self.width, f)

    def __repr__(self):
        return "<FakeDataset: transform={}, height={}, width={}>".format(self.transform, self.height, self.width)


@composite
def dataset_utm(draw):
    """Generate a fake UTM dataset with an origin, a resolution, and a finite size"""
    x = draw(floats(min_value=-1e6, max_value=1e+6, allow_nan=False, allow_infinity=False))
    y = draw(floats(min_value=-1e6, max_value=1e+6, allow_nan=False, allow_infinity=False))
    res = draw(floats(min_value=0.1, max_value=30, allow_nan=False, allow_infinity=False))
    h = draw(integers(min_value=1, max_value=1000))
    w = draw(integers(min_value=1, max_value=1000))
    return FakeDataset(
        transform=windows.Affine.identity() * windows.Affine.translation(x, y) * windows.Affine.scale(res, -res),
        height=h, width=w)


@composite
def dataset_utm_north_down(draw):
    """Generate a fake UTM dataset with an origin, a resolution, and a finite size"""
    x = draw(floats(min_value=-1e6, max_value=1e+6, allow_nan=False, allow_infinity=False))
    y = draw(floats(min_value=-1e6, max_value=1e+6, allow_nan=False, allow_infinity=False))
    res = draw(floats(min_value=0.1, max_value=30, allow_nan=False, allow_infinity=False))
    h = draw(integers(min_value=1, max_value=1000))
    w = draw(integers(min_value=1, max_value=1000))
    return FakeDataset(
        transform=windows.Affine.identity() * windows.Affine.translation(x, y) * windows.Affine.scale(res),
        height=h, width=w)


def assert_windows_almost_equal(a, b):
    assert round(a.col_off, 7) == round(b.col_off, 7)
    assert round(a.row_off, 7) == round(b.row_off, 7)
    assert round(a.width, 7) == round(b.width, 7)
    assert round(a.height, 7) == round(b.height, 7)


@given(dataset=dataset_utm())
def test_window_rt(dataset):
    """Get correct window for full dataset extent"""
    left, top = dataset.transform * (0, 0)
    right, bottom = dataset.transform * (dataset.width, dataset.height)
    assert_windows_almost_equal(
        dataset.window(left, bottom, right, top),
        windows.Window(0, 0, dataset.width, dataset.height))


@given(dataset=dataset_utm_north_down())
def test_window_rt_north_down(dataset):
    """Get correct window for full dataset extent"""
    left, top = dataset.transform * (0, 0)
    right, bottom = dataset.transform * (dataset.width, dataset.height)
    assert_windows_almost_equal(
        dataset.window(left, bottom, right, top),
        windows.Window(0, 0, dataset.width, dataset.height))


@given(dataset=dataset_utm())
def test_window_transform_rt(dataset):
    assert dataset.window_transform(windows.Window(0, 0, dataset.width, dataset.height)) == dataset.transform


@given(dataset=dataset_utm_north_down())
def test_window_transform_rt_north_down(dataset):
    assert dataset.window_transform(windows.Window(0, 0, dataset.width, dataset.height)) == dataset.transform


@given(dataset=dataset_utm())
def test_window_bounds_rt(dataset):
    assert dataset.window_bounds(windows.Window(0, 0, dataset.width, dataset.height)) == dataset.bounds


@given(dataset=dataset_utm_north_down())
def test_window_bounds_rt_north_down(dataset):
    assert dataset.window_bounds(windows.Window(0, 0, dataset.width, dataset.height)) == dataset.bounds

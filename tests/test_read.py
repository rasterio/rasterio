from hashlib import md5
import os
import unittest

import numpy as np
import pytest
import sys

import rasterio
from rasterio._err import CPLE_AppDefinedError
from rasterio.errors import DatasetIOShapeError, RasterioIOError
import affine

# Find out if we've got HDF support (needed below).
try:
    with rasterio.open('tests/data/no_band.h5') as s:
        pass
    has_hdf = True
except Exception:
    has_hdf = False


# Fixture to create test datasets within temporary directory
@pytest.fixture
def make_gtiff(tmpdir):
    files = []
    def _write_tiff(fname, **kwargs):
        path = str(tmpdir.join(f"{fname}.tif"))
        with rasterio.open(path, 'w', **kwargs) as dst:
            count, width, height = kwargs['count'], kwargs['width'], kwargs['height']
            data = np.ones((count, height, width), dtype=rasterio.uint8)
            data[:, 0:width//2, 0:height//2] = 255
            dst.write(data)
        files.append(path)
        return path

    yield _write_tiff

    for f in files:
        os.remove(f)


class ReaderContextTest(unittest.TestCase):

    def test_context(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            self.assertEqual(s.name, 'tests/data/RGB.byte.tif')
            self.assertEqual(s.driver, 'GTiff')
            self.assertEqual(s.closed, False)
            self.assertEqual(s.count, 3)
            self.assertEqual(s.width, 791)
            self.assertEqual(s.height, 718)
            self.assertEqual(s.shape, (718, 791))
            self.assertEqual(s.dtypes, tuple([rasterio.ubyte] * 3))
            self.assertEqual(s.nodatavals, (0, 0, 0))
            self.assertEqual(s.indexes, (1, 2, 3))
            self.assertEqual(s.crs.to_epsg(), 32618)
            self.assertTrue(s.crs.wkt.startswith('PROJCS'), s.crs.wkt)
            for i, v in enumerate((101985.0, 2611485.0, 339315.0, 2826915.0)):
                self.assertAlmostEqual(s.bounds[i], v)
            self.assertEqual(
                s.transform,
                (300.0379266750948, 0.0, 101985.0,
                 0.0, -300.041782729805, 2826915.0,
                 0, 0, 1.0))
            self.assertEqual(s.meta['crs'], s.crs)
            self.assertEqual(
                repr(s),
                "<open DatasetReader name='tests/data/RGB.byte.tif' "
                "mode='r'>")
        self.assertEqual(s.closed, True)
        self.assertEqual(s.count, 3)
        self.assertEqual(s.width, 791)
        self.assertEqual(s.height, 718)
        self.assertEqual(s.shape, (718, 791))
        self.assertEqual(s.dtypes, tuple([rasterio.ubyte] * 3))
        self.assertEqual(s.nodatavals, (0, 0, 0))
        self.assertEqual(s.crs.to_epsg(), 32618)
        self.assertEqual(
            s.transform,
            (300.0379266750948, 0.0, 101985.0,
             0.0, -300.041782729805, 2826915.0,
             0, 0, 1.0))
        self.assertEqual(
            repr(s),
            "<closed DatasetReader name='tests/data/RGB.byte.tif' "
            "mode='r'>")

    def test_derived_spatial(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            self.assertTrue(s.crs.wkt.startswith('PROJCS'), s.crs.wkt)
            for i, v in enumerate((101985.0, 2611485.0, 339315.0, 2826915.0)):
                self.assertAlmostEqual(s.bounds[i], v)
            for a, b in zip(s.xy(0, 0, offset='ul'), (101985.0, 2826915.0)):
                self.assertAlmostEqual(a, b)

    def test_read_ubyte(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = s.read(1)
            self.assertEqual(a.dtype, rasterio.ubyte)

    def test_read_ubyte_bad_index(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            self.assertRaises(IndexError, s.read, 0)

    def test_read_ubyte_out(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = np.zeros((718, 791), dtype=rasterio.ubyte)
            a = s.read(1, a)
            self.assertEqual(a.dtype, rasterio.ubyte)

    def test_read_out_dtype_fail(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = np.zeros((718, 791), dtype=rasterio.float32)
            s.read(1, a)

    def test_read_basic(self):
        with rasterio.open('tests/data/shade.tif') as s:
            a = s.read(masked=True)  # Gray
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (1, 1024, 1024))
            self.assertTrue(hasattr(a, 'mask'))
            self.assertEqual(a.fill_value, 255)
            self.assertEqual(list(set(s.nodatavals)), [255])
            self.assertEqual(a.dtype, rasterio.ubyte)
            self.assertEqual(a.sum((1, 2)).tolist(), [0])
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = s.read(masked=True)  # RGB
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (3, 718, 791))
            self.assertTrue(hasattr(a, 'mask'))
            self.assertEqual(a.fill_value, 0)
            self.assertEqual(list(set(s.nodatavals)), [0])
            self.assertEqual(a.dtype, rasterio.ubyte)
            a = s.read(masked=False)  # no mask
            self.assertFalse(hasattr(a, 'mask'))
            self.assertEqual(list(set(s.nodatavals)), [0])
            self.assertEqual(a.dtype, rasterio.ubyte)
        with rasterio.open('tests/data/float.tif') as s:
            a = s.read(masked=True)  # floating point values
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (1, 2, 3))
            self.assertTrue(hasattr(a, 'mask'))
            self.assertEqual(list(set(s.nodatavals)), [None])
            self.assertEqual(a.dtype, rasterio.float64)

    def test_read_indexes(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = s.read()  # RGB
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (3, 718, 791))
            self.assertEqual(a.sum((1, 2)).tolist(),
                             [17008452, 25282412, 27325233])
            # read last index as 2D array
            a = s.read(s.indexes[-1])  # B
            self.assertEqual(a.ndim, 2)
            self.assertEqual(a.shape, (718, 791))
            self.assertEqual(a.sum(), 27325233)
            # read last index as 2D array
            a = s.read(s.indexes[-1:])  # [B]
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (1, 718, 791))
            self.assertEqual(a.sum((1, 2)).tolist(), [27325233])
            # out of range indexes
            self.assertRaises(IndexError, s.read, 0)
            self.assertRaises(IndexError, s.read, [3, 4])
            # read slice
            a = s.read(s.indexes[0:2])  # [RG]
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (2, 718, 791))
            self.assertEqual(a.sum((1, 2)).tolist(), [17008452, 25282412])
            # read stride
            a = s.read(s.indexes[::2])  # [RB]
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (2, 718, 791))
            self.assertEqual(a.sum((1, 2)).tolist(), [17008452, 27325233])
            # read zero-length slice
            try:
                a = s.read(s.indexes[1:1])
            except ValueError:
                pass

    def test_read_window(self):
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            # window with 1 nodata on band 3
            a = s.read(window=((300, 320), (320, 330)), masked=True)
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (3, 20, 10))
            self.assertTrue(hasattr(a, 'mask'))
            self.assertEqual(a.mask.sum((1, 2)).tolist(), [0, 0, 1])
            self.assertEqual([md5(x.tobytes()).hexdigest() for x in a],
                             ['1df719040daa9dfdb3de96d6748345e8',
                              'ec8fb3659f40c4a209027231bef12bdb',
                              '5a9c12aebc126ec6f27604babd67a4e2'])
            # window without any missing data, but still is masked result
            a = s.read(window=((310, 330), (320, 330)), masked=True)
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (3, 20, 10))
            self.assertTrue(hasattr(a, 'mask'))
            self.assertEqual([md5(x.tobytes()).hexdigest() for x in a[:]],
                             ['9e3000d60b4b6fb956f10dc57c4dc9b9',
                              '6a675416a32fcb70fbcf601d01aeb6ee',
                              '94fd2733b534376c273a894f36ad4e0b'])

    def test_read_window_overflow(self):
        """Test graceful Numpy-like handling of windows that overflow
        the dataset's bounds."""
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = s.read(window=((None, 20000), (None, 20000)))
            self.assertEqual(a.shape, (3,) + s.shape)

    def test_read_window_beyond(self):
        """Test graceful Numpy-like handling of windows beyond
        the dataset's bounds."""
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = s.read(window=((10000, 20000), (10000, 20000)))
            self.assertEqual(a.shape, (3, 0, 0))

    def test_read_window_overlap(self):
        """Test graceful Numpy-like handling of windows beyond
        the dataset's bounds."""
        with rasterio.open('tests/data/RGB.byte.tif') as s:
            a = s.read(window=((-100, 20000), (-100, 20000)))
            self.assertEqual(a.shape, (3, 100, 100))

    def test_read_nan_nodata(self):
        with rasterio.open('tests/data/float_nan.tif') as s:
            a = s.read(masked=True)
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (1, 2, 3))
            self.assertTrue(hasattr(a, 'mask'))
            self.assertNotEqual(a.fill_value, np.nan)
            self.assertEqual(str(list(set(s.nodatavals))), str([np.nan]))
            self.assertEqual(a.dtype, rasterio.float32)
            self.assertFalse(np.isnan(a).any())
            a = s.read(masked=False)
            self.assertFalse(hasattr(a, 'mask'))
            self.assertTrue(np.isnan(a).any())
            # Window does not contain a nodatavalue, result is still masked
            a = s.read(window=((0, 2), (0, 2)), masked=True)
            self.assertEqual(a.ndim, 3)
            self.assertEqual(a.shape, (1, 2, 2))
            self.assertTrue(hasattr(a, 'mask'))

    @pytest.mark.skipif(not has_hdf, reason="HDF driver not available")
    def test_read_no_band(self):
        with rasterio.open('tests/data/no_band.h5') as s:
            self.assertEqual(s.count, 0)
            self.assertEqual(s.meta['dtype'], 'float_')
            self.assertIsNone(s.meta['nodata'])
            self.assertRaises(ValueError, s.read)

    def test_read_gtiff_band_interleave_multithread(self):
        """Test workaround for https://github.com/rasterio/rasterio/issues/2847."""

        with rasterio.Env(GDAL_NUM_THREADS='2'), rasterio.open('tests/data/rgb_deflate.tif') as s:
            s.read(1)
            a = s.read(2)
            self.assertEqual(a.sum(), 25282412)

        with rasterio.Env(GDAL_NUM_THREADS='2'), rasterio.open('tests/data/rgb_deflate.tif') as s:
            a = s.read(indexes=[3,2,1])
            self.assertEqual(a[0].sum(), 27325233)
            self.assertEqual(a[1].sum(), 25282412)
            self.assertEqual(a[2].sum(), 17008452)


@pytest.mark.parametrize("shape,indexes", [
    ((72, 80), 1),          # Single band
    ((2, 72, 80), (1, 3)),  # Multiband
    ((3, 72, 80), None)     # All bands
])
def test_out_shape(path_rgb_byte_tif, shape, indexes):

    """Test read(out_shape) and read_masks(out_shape).  The tests are identical
    aside from the method call.

    The pytest parameters are:

        * shape - tuple passed to out_shape
        * indexes - The bands to read

    The resulting images have been decimated by a factor of 10.
    """

    with rasterio.open(path_rgb_byte_tif) as src:

        for attr in 'read', 'read_masks':

            reader = getattr(src, attr)

            out_shape = reader(indexes, out_shape=shape)
            out = reader(indexes, out=np.empty(shape, dtype=src.dtypes[0]))

            assert out_shape.shape == out.shape
            assert (out_shape == out).all()

            # Sanity check of the test itself
            assert shape[-2:] == (72, 80)


def test_out_shape_exceptions(path_rgb_byte_tif):

    with rasterio.open(path_rgb_byte_tif) as src:

        for attr in 'read', 'read_masks':

            reader = getattr(src, attr)

            with pytest.raises(ValueError):
                out = np.empty((src.count, src.height, src.width))
                out_shape = (src.count, src.height, src.width)
                reader(out=out, out_shape=out_shape)

            with pytest.raises(Exception):
                out_shape = (5, src.height, src.width)
                reader(1, out_shape=out_shape)


def test_out_shape_implicit(path_rgb_byte_tif):
    """out_shape is filled to match read indexes"""
    with rasterio.open(path_rgb_byte_tif) as src:
        out = src.read(indexes=(1, 2), out_shape=src.shape)
        assert out.shape == (2,) + src.shape


def test_out_shape_no_segfault(path_rgb_byte_tif):
    """Prevent segfault as reported in 2189"""
    with rasterio.open(path_rgb_byte_tif) as src:
        with pytest.raises(DatasetIOShapeError):
            src.read(out_shape=(2, src.height, src.width))


def test_read_out_no_mask(path_rgb_byte_tif):
    """Find no mask when out keyword arg is not masked."""
    with rasterio.open(path_rgb_byte_tif) as src:
        a = np.empty((3, 718, 791), np.ubyte)
        b = src.read(out=a)
        assert not hasattr(a, "mask")
        assert not hasattr(b, "mask")


def test_read_out_mask(path_rgb_byte_tif):
    """Find a mask when out keyword arg is a masked array."""
    with rasterio.open(path_rgb_byte_tif) as src:
        a = np.ma.empty((3, 718, 791), np.ubyte)
        b = src.read(out=a)
        assert hasattr(a, "mask")
        assert hasattr(b, "mask")


@pytest.mark.parametrize(
    "out", [np.empty((20, 10), np.ubyte), np.empty((2, 20, 10), np.ubyte)]
)
def test_read_out_mask(path_rgb_byte_tif, out):
    """Raise when out keyword arg has wrong shape."""
    with rasterio.open(path_rgb_byte_tif) as src:
        with pytest.raises(ValueError):
            src.read(indexes=[2], out=out)


def test_chained_io_errors(path_rgb_byte_tif):
    """Get chained exceptions."""
    with rasterio.open("tests/data/corrupt.tif") as src:
        # RasterioIOError is at the top of the stack (~0).
        with pytest.raises(RasterioIOError) as excinfo:
            src.read()

        assert "Read failed. See previous exception for details." == str(excinfo.value)

        # Exception ~1 is a GDAL AppDefinedError mentioning IReadBlock.
        exc = excinfo.value.__cause__
        assert isinstance(exc, CPLE_AppDefinedError)
        msg = str(exc)
        assert "corrupt.tif" in msg
        assert "IReadBlock failed" in msg

        # Exception ~2 is another AppDefinedError mentioning TIFFReadEncodedTile.
        exc = excinfo.value.__cause__.__cause__
        assert isinstance(exc, CPLE_AppDefinedError)
        msg = str(exc)
        assert "TIFFReadEncodedTile()" in msg

        # Exception ~3 is another AppDefinedError mentioning TIFFFillTile.
        exc = excinfo.value.__cause__.__cause__.__cause__
        assert isinstance(exc, CPLE_AppDefinedError)
        msg = str(exc)
        assert "TIFFFillTile:Read error" in msg


def test_read_bounds_eps(make_gtiff):
    eps = sys.float_info.epsilon
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.5, eps, 13,
                                   eps, 1.2, -32),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 1
    }
    with rasterio.open(make_gtiff("a.tif", **kwargs)) as ds:
        assert ds.bounds == (13.0, -20.0, 18.0, -32.0)


def test_read_bounds_0(make_gtiff):
    eps = sys.float_info.epsilon
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.5, eps, 13,
                                   eps, 1.2, -32),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 1
    }
    kwargs['transform'] = affine.identity.rotation(0) * affine.identity.scale(2, 3)
    with rasterio.open(make_gtiff("0_rot.tif", **kwargs)) as ds:
        assert ds.bounds == (0.0, 30.0, 20.0, 0.0)


def test_read_bounds_90(make_gtiff):
    eps = sys.float_info.epsilon
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.5, eps, 13,
                                   eps, 1.2, -32),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 1
    }
    kwargs['transform'] = affine.identity.rotation(90) * affine.identity.scale(2, 3)
    with rasterio.open(make_gtiff("90_rot.tif",**kwargs)) as ds:
        assert ds.bounds == (0.0, 20.0, -30.0, 0.0)


def test_read_bounds_180(make_gtiff):
    eps = sys.float_info.epsilon
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.5, eps, 13,
                                   eps, 1.2, -32),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 1
    }
    kwargs['transform'] = affine.identity.rotation(180) * affine.identity.scale(2, 3)
    with rasterio.open(make_gtiff("180_rot.tif", **kwargs)) as ds:
        assert ds.bounds == (0.0, -30.0, -20.0, 0.0)


def test_read_bounds_270(make_gtiff):
    eps = sys.float_info.epsilon
    kwargs = {
        "crs": {'init': 'epsg:4326'},
        "transform": affine.Affine(0.5, eps, 13,
                                   eps, 1.2, -32),
        "count": 1,
        "dtype": rasterio.uint8,
        "driver": "GTiff",
        "width": 10,
        "height": 10,
        "nodata": 1
    }
    kwargs['transform'] = affine.identity.rotation(270) * affine.identity.scale(2, 3)
    with rasterio.open(make_gtiff("270_rot.tif", **kwargs)) as ds:
        assert ds.bounds == (0.0, -20.0, 30.0, 0.0)

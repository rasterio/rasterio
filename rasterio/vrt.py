"""rasterio.vrt: a module concerned with GDAL VRTs"""

from rasterio._warp import WarpedVRTReaderBase
from rasterio.enums import Resampling
from rasterio.env import ensure_env
from rasterio.io import WindowMethodsMixin, TransformMethodsMixin


class WarpedVRTReader(WarpedVRTReaderBase, WindowMethodsMixin,
                      TransformMethodsMixin):
    """A virtual warped dataset reader"""

    def __repr__(self):
        return "<{} WarpedVRTReader name='{}' mode='{}'>".format(
            self.closed and 'closed' or 'open', self.name, self.mode)


class WarpedVRT(object):

    """Creates a virtual warped dataset.

    Abstracts many details of raster warping and allows access to data
    that is reprojected as needed.

    This class is backed by an in-memory GDAL VRTWarpedDataset VRT file.

    Attributes
    ----------

    path : str
        The file path or network resource identifier for the dataset to
        be virtually warped.
    dst_crs : CRS or str
        The warp operation's destination coordinate reference system.
    resampling : int
        One of the values from rasterio.enums.Resampling. The default is
        `Resampling.nearest`.
    tolerance : float
        The maximum error tolerance in input pixels when approximating
        the warp transformation. The default is 0.125.

    Example
    -------

    >>> with VirtualWarpedFile('tests/data/RGB.byte.tif', dst_crs='EPSG:3857'
    ...         ).open() as src:
    ...     data = src.read()

    """

    def __init__(self, path, dst_crs=None, resampling=Resampling.nearest,
                 tolerance=0.125):
        self.path = path
        self.dst_crs = dst_crs
        self.resampling = resampling
        self.tolerance = tolerance

    @ensure_env
    def open(self):
        """Open the virtual warped dataset

        Returns a dataset object opened in 'r' mode.
        """
        s = WarpedVRTReader(self.path, dst_crs=self.dst_crs,
                            resampling=self.resampling,
                            tolerance=self.tolerance)
        s.start()
        return s

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass

"""Tools for accessing all properties of datasets that do not
correspond to bands."""

from rasterio._base import DatasetReaderBase


class RasterMetadataReader(DatasetReaderBase):
    """Read-only access to dataset metadata and other properties

    Attributes
    ----------
    name : str
        The dataset's filename or identifier.
    mode : str
        The access mode in which the dataset object was opened. One
        of 'r', 'r+', 'w' (which have the same semantics as with
        standard Python streams), and 'r-' a mode in which dataset
        metadata properties may be read but not any image or raster
        data.
    """

    @property
    def kwds(self):
        """A dataset's format-specific creation keywords."""
        return self.tags(ns='rio_creation_kwds')

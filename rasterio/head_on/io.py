from rasterio.head_on._io import HeadonDatasetReaderBase
from rasterio.transform import TransformMethodsMixin
from rasterio.windows import WindowMethodsMixin


class HeadonDatasetReader(HeadonDatasetReaderBase, WindowMethodsMixin, TransformMethodsMixin):
    """An unbuffered data and metadata reader"""

    def __repr__(self):
        return "<{} HeadonDatasetReader name='{}' mode='{}'>".format(
            self.closed and 'closed' or 'open', self.name, self.mode)

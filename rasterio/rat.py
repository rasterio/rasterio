"""Raster attribute tables"""
import numpy as np

from rasterio._rat import (
    RATBase
)

from rasterio.enums import (
    RATFieldType,
    RATTableType,
    RATFieldUsage
)


numpy_types = {
    RATFieldType.Integer: np.int32,
    RATFieldType.Real: np.float64,
    RATFieldType.String: np.str_,
}

class Column:

    def __init__(
            self,
            name,
            field_type: RATFieldType,
            field_usage: RATFieldUsage=RATFieldUsage.Generic,
            values: np.array=None):

        self.name = name
        self.field_type = field_type
        self.dtype = numpy_types[field_type]
        self.usage = field_usage

        if values is None:
            self.values = np.empty(0, dtype=self.dtype)
        else:
            self.values = np.asarray(values, dtype=self.dtype)

        if self.values.ndim != 1:
            raise ValueError("values must be a 1D array")

    def __setitem__(self, index, value):
        self.values[index] = value

class Table(RATBase):
    """Raster attribute table.
    """

    def __init__(self, columns=None):
        self._create()

        if columns is None:
            columns = []

        for i, column in enumerate(columns):
            self[i] = column
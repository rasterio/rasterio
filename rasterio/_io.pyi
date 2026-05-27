"""Type stubs for rasterio._io Cython module."""

from __future__ import annotations

from contextlib import ExitStack
from typing import Any, Iterator

import numpy as np
from numpy.typing import NDArray

from rasterio._base import DatasetBase
from rasterio.crs import CRS
from rasterio.enums import Resampling

class Statistics:
    min: float
    max: float
    mean: float
    std: float
    def __init__(self, min: float, max: float, mean: float, std: float) -> None: ...

class DatasetReaderBase(DatasetBase):
    def read(
        self,
        indexes: int | list[int] | None = ...,
        out: NDArray[Any] | None = ...,
        window: Any | None = ...,
        masked: bool = ...,
        out_shape: tuple[int, ...] | None = ...,
        boundless: bool = ...,
        resampling: Resampling = ...,
        fill_value: float | None = ...,
        out_dtype: str | np.dtype[Any] | None = ...,
    ) -> NDArray[Any]: ...
    def read_masks(
        self,
        indexes: int | list[int] | None = ...,
        out: NDArray[Any] | None = ...,
        out_shape: tuple[int, ...] | None = ...,
        window: Any | None = ...,
        boundless: bool = ...,
        resampling: Resampling = ...,
    ) -> NDArray[Any]: ...
    def dataset_mask(
        self,
        out: NDArray[Any] | None = ...,
        out_shape: tuple[int, ...] | None = ...,
        window: Any | None = ...,
        boundless: bool = ...,
        resampling: Resampling = ...,
    ) -> NDArray[Any]: ...
    def sample(
        self,
        xy: Any,
        indexes: int | list[int] | None = ...,
        masked: bool = ...,
    ) -> Iterator[NDArray[Any]]: ...
    def stats(
        self,
        *,
        indexes: int | list[int] | None = ...,
        approx: bool = ...,
    ) -> list[Statistics]: ...
    def statistics(
        self,
        bidx: int,
        approx: bool = ...,
        clear_cache: bool = ...,
    ) -> Statistics: ...

class DatasetWriterBase(DatasetReaderBase):
    def __init__(
        self,
        path: Any,
        mode: str,
        driver: str | None = ...,
        width: int | None = ...,
        height: int | None = ...,
        count: int | None = ...,
        crs: Any = ...,
        transform: Any = ...,
        dtype: str | np.dtype[Any] | None = ...,
        nodata: float | None = ...,
        gcps: Any = ...,
        rpcs: Any = ...,
        sharing: bool = ...,
        **kwargs: Any,
    ) -> None: ...
    def write(
        self,
        arr: NDArray[Any],
        indexes: int | list[int] | None = ...,
        window: Any | None = ...,
        masked: bool = ...,
    ) -> None: ...
    def write_band(
        self, bidx: int, src: NDArray[Any], window: Any | None = ...
    ) -> None: ...
    def clear_stats(self) -> None: ...
    def update_stats(
        self,
        *,
        stats: list[Statistics] | Statistics | None = ...,
        indexes: int | list[int] | None = ...,
        approx: bool = ...,
    ) -> None: ...
    def update_tags(
        self, bidx: int = ..., ns: str | None = ..., **kwargs: str
    ) -> None: ...
    def set_band_description(self, bidx: int, value: str) -> None: ...
    def set_band_unit(self, bidx: int, value: str) -> None: ...
    def write_colormap(
        self,
        bidx: int,
        colormap: dict[int, tuple[int, int, int, int] | tuple[int, int, int]],
    ) -> None: ...
    def write_mask(
        self, mask_array: NDArray[Any] | bool, window: Any | None = ...
    ) -> None: ...
    def build_overviews(
        self,
        factors: list[int],
        resampling: Resampling = ...,
    ) -> None: ...

class BufferedDatasetWriterBase(DatasetWriterBase):
    def __init__(
        self,
        path: Any,
        mode: str = ...,
        driver: str | None = ...,
        width: int | None = ...,
        height: int | None = ...,
        count: int | None = ...,
        crs: Any = ...,
        transform: Any = ...,
        dtype: str | np.dtype[Any] | None = ...,
        nodata: float | None = ...,
        gcps: Any = ...,
        rpcs: Any = ...,
        sharing: bool = ...,
        **kwargs: Any,
    ) -> None: ...
    def stop(self) -> None: ...

class MemoryFileBase:
    name: str
    mode: str

    def __init__(
        self,
        file_or_bytes: Any = ...,
        dirname: str | None = ...,
        filename: str | None = ...,
        ext: str = ...,
    ) -> None: ...
    @property
    def closed(self) -> bool: ...
    def exists(self) -> bool: ...
    def __len__(self) -> int: ...
    def getbuffer(self) -> Any: ...
    def close(self) -> None: ...
    def seek(self, offset: int, whence: int = ...) -> int: ...
    def tell(self) -> int: ...
    def read(self, size: int = ...) -> bytes: ...
    def write(self, data: bytes) -> int: ...

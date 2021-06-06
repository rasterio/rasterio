""" some basic types """
import os
from typing import TypeVar, Union, Sequence, Any

T = TypeVar("T")
MaybeSequence = Union[T, Sequence[T]]
PathLikeOrStr = Union[str, os.PathLike]
FileType = Any


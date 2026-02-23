"""Serialization and deserialization."""

from functools import singledispatch


@singledispatch
def to_json(obj):
    """Convert obj to a JSON serializable form."""
    return obj

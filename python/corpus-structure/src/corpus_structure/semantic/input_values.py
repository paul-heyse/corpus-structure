"""Detach untrusted field values before domain validation and interpretation."""

import copy
from collections.abc import Callable, Mapping
from typing import Any

from pydantic import BaseModel


def _untrusted_value(value: Any, *, model_field: Callable[[BaseModel, str], Any] = getattr) -> Any:
    """Model instances can have bypassed validation; reconstruct their public fields."""
    if isinstance(value, BaseModel):
        return {
            name: _untrusted_value(model_field(value, name), model_field=model_field)
            for name in type(value).model_fields
            if name in value.model_fields_set
        }
    if isinstance(value, Mapping):
        return {key: _untrusted_value(item, model_field=model_field) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_untrusted_value(item, model_field=model_field) for item in value)
    if isinstance(value, list):
        return [_untrusted_value(item, model_field=model_field) for item in value]
    return copy.deepcopy(value)

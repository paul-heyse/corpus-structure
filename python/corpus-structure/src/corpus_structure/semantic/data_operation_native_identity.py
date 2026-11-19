"""Identity facts supplied by the installed native descriptor."""

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB


def native_identity_value(name: str):
    return func.sem.data_operation_native_descriptor(type_=JSONB())[name]


def native_identity_field(name: str):
    return native_identity_value(name).astext

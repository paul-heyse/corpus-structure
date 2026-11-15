"""Bounded reuse of pure compiled facts for identical ordinary captured inputs.

Acquired permissions, source custody and native trust are checked by their owners.
This cache retains immutable model values, never analyzer managers or live ports.
"""

from __future__ import annotations

import dataclasses
import typing
from functools import lru_cache
from importlib.metadata import version as _package_version
from typing import Any

from .data_operation_compilation import compile_data_operations as _STATIC_COMPILER
from .python_operation_sources import PythonSource, PythonSourceCollection
from .types import (
    ClassDefinition,
    PropertyDefinition,
    SourceArtifact,
    SourceBundle,
    VocabularyMember,
    VocabularySnapshot,
)

# A process-local compilation cache cannot survive analyzer/compiler replacement.
# Exact source and interpretation settings remain part of each cache key below.
_STATIC_COMPILER_CONTEXT = (
    _STATIC_COMPILER,
    _STATIC_COMPILER.__code__,
    tuple((name, _package_version(name)) for name in ("griffe", "libcst", "astroid")),
)


_STATIC_INPUT_TYPES = (
    SourceBundle,
    SourceArtifact,
    PythonSourceCollection,
    PythonSource,
    ClassDefinition,
    PropertyDefinition,
    VocabularySnapshot,
    VocabularyMember,
)


def _ordinary_static_input(value: object) -> bool:
    """Cache eligibility only; nonordinary inputs retain the compiler's validation.

    A subclass can replace equality/hash while exposing different source bytes.
    Never let caller-controlled equality select previously compiled source facts.
    """
    kind = type(value)
    if any(kind is ordinary for ordinary in (str, bytes, int, float, bool, type(None))):
        return True
    if kind is tuple:
        return all(_ordinary_static_input(item) for item in typing.cast(tuple[object, ...], value))
    if any(kind is ordinary for ordinary in _STATIC_INPUT_TYPES):
        return all(
            _ordinary_static_input(getattr(value, field.name))
            for field in dataclasses.fields(typing.cast(Any, value))
        )
    return False


@lru_cache(maxsize=16)
def _prepared_python_sources(schema, declarations, sources, definitions, vocabularies, context, captured_contracts=()):
    """Reuse immutable static facts, never analyzer managers or acquired authority.

    Every input is an exact frozen preparation value. The context names the active
    compiler implementation and process analyzer selection; it is not a durable
    semantic fingerprint or authorization cache.
    """
    return _STATIC_COMPILER(
        schema,
        declarations=declarations,
        python_sources=sources,
        definitions=definitions,
        vocabularies=vocabularies,
        captured_contracts=captured_contracts,
    )


def prepare_data_operation_model(
    schema=None, declarations=(), sources=None, *, definitions=None, vocabularies=(), captured_contracts=()
):
    """Recompile substituted interpreters and nonordinary inputs without cache lookup."""
    from .data_operation_compilation import compile_data_operations

    values = (schema, declarations, sources, definitions, vocabularies, captured_contracts)
    if compile_data_operations is _STATIC_COMPILER and _ordinary_static_input(values):
        return _prepared_python_sources(schema, declarations, sources, definitions, vocabularies, _STATIC_COMPILER_CONTEXT, captured_contracts)
    return compile_data_operations(
        schema,
        declarations=declarations,
        python_sources=sources,
        definitions=definitions,
        vocabularies=vocabularies,
        captured_contracts=captured_contracts,
    )

"""Archive-3 directional products, independent of storage and semantic admission."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from typing import Any, get_args, get_origin

from cattrs import Converter, transform_error
from cattrs.cols import homogenous_tuple_structure_factory
from cattrs.errors import BaseValidationError
from cattrs.gen import make_dict_structure_fn, make_dict_unstructure_fn, override

from .types import (
    ClassDefinition,
    Diagnostic,
    PreparedRelease,
    QueryDescriptor,
    RegistryRow,
    VocabularySnapshot,
)


@dataclass(frozen=True)
class ArtifactReference:
    kind: str
    digest: str


@dataclass(frozen=True)
class RegistryWireRow:
    kind: str
    name: str
    body_hex: bytes

    def semantic_row(self) -> RegistryRow:
        return RegistryRow(self.kind, self.name, self.body_hex)


@dataclass(frozen=True)
class ArchiveProducts:
    release_id: str
    definitions: tuple[ClassDefinition, ...]
    vocabularies: tuple[VocabularySnapshot, ...]
    registry_rows: tuple[RegistryWireRow, ...]
    queries: tuple[QueryDescriptor, ...]
    artifacts: tuple[ArtifactReference, ...]
    required_capabilities: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]
    execution_model_id: str | None = None


def _exact(value: Any, expected: type) -> Any:
    if type(value) is not expected:
        raise TypeError(f"expected {expected.__name__}")
    return value


def _hex(value: Any, _: Any) -> bytes:
    return bytes.fromhex(_exact(value, str))


def _converter() -> Converter:
    converter = Converter(forbid_extra_keys=True, detailed_validation=True)
    for primitive in (str, int, bool, float, bytes):
        converter.register_structure_hook(primitive, _exact)

    def tuple_hook(target):
        args = get_args(target)
        nested = (
            homogenous_tuple_structure_factory(target, converter)
            if args and args[-1] is Ellipsis
            else converter.gen_structure_hetero_tuple(target)
        )

        def structure(value, expected=target):
            if not isinstance(value, (list, tuple)):
                raise TypeError("expected array")
            return nested(value, expected)

        return structure

    converter.register_structure_hook_factory(lambda t: get_origin(t) is tuple, tuple_hook)

    def object_hook(target):
        options: dict[str, Any] = (
            {"body_hex": override(struct_hook=_hex)} if target is RegistryWireRow else {}
        )
        nested = make_dict_structure_fn(target, converter, **options)

        def structure(value, _=target):
            if not isinstance(value, Mapping):
                raise TypeError("expected object")
            return nested(value, target)

        return structure

    converter.register_structure_hook_factory(is_dataclass, object_hook)
    converter.register_unstructure_hook(
        RegistryWireRow,
        make_dict_unstructure_fn(
            RegistryWireRow, converter, body_hex=override(unstruct_hook=bytes.hex)
        ),
    )
    nullable: dict[str, Any] = {
        f.name: override(omit_if_default=True) for f in fields(Diagnostic) if f.default is None
    }
    converter.register_unstructure_hook(
        Diagnostic, make_dict_unstructure_fn(Diagnostic, converter, **nullable)
    )
    converter.register_unstructure_hook(
        ArchiveProducts,
        make_dict_unstructure_fn(
            ArchiveProducts, converter, execution_model_id=override(omit_if_default=True)
        ),
    )
    return converter


_CONVERTER = _converter()


def _decode(value: Any, target: Any, path: str) -> Any:
    from .releases import ArchiveDecodeError

    try:
        return _CONVERTER.structure(value, target)
    except (BaseValidationError, TypeError, ValueError, KeyError) as exc:
        diagnostics = tuple(
            Diagnostic("archive_wire", text.partition(" @ ")[-1], text.partition(" @ ")[0])
            for text in transform_error(exc, path=path)
        )
        raise ArchiveDecodeError(diagnostics) from exc


def decode_products(value: Any) -> ArchiveProducts:
    return _decode(value, ArchiveProducts, "products")


def decode_vocabularies(value: Any) -> tuple[VocabularySnapshot, ...]:
    return _decode(value, tuple[VocabularySnapshot, ...], "inputs.vocabulary")


def encode_products(prepared: PreparedRelease) -> dict[str, Any]:
    product = ArchiveProducts(
        prepared.release_id,
        prepared.definitions,
        prepared.vocabularies,
        tuple(RegistryWireRow(r.kind, r.name, r.body) for r in prepared.registry_rows),
        prepared.queries,
        tuple(ArtifactReference(a.kind, a.digest) for a in prepared.artifacts),
        prepared.required_capabilities,
        prepared.diagnostics,
        prepared.execution_model_id,
    )
    return _CONVERTER.unstructure(product)

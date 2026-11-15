"""Prepared source-linked interfaces, separate from executable semantic identity.

Only the closed frontend creates this projection. Ordinary archive reads decode
these facts without importing or reanalysing the currently installed target code.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from enum import Enum
from hashlib import sha256
from importlib.metadata import version
from typing import Any, Literal

import griffe
from pydantic import BaseModel, ConfigDict, JsonValue

from .identity import canonical_bytes

SOURCE_INTERFACE_ARTIFACT = "data_operation_source_interfaces.json"


class _Fact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceModuleFacts(_Fact):
    module: str
    path: str
    source_digest: str
    stub_digest: str | None = None
    captured_artifact: str


class SourceCallableFacts(_Fact):
    exposed: str
    declaration: str
    module: str
    path: str
    source_digest: str
    line: int | None = None
    end_line: int | None = None
    signature: dict[str, JsonValue]
    documentation: str | None = None
    sections: tuple[dict[str, JsonValue], ...] = ()
    origin: Literal["extracted", "modeled"] = "extracted"


class SourceOperationFacts(_Fact):
    operation: str
    owner: str
    callables: tuple[SourceCallableFacts, ...]
    metadata: dict[str, JsonValue]
    origins: tuple[dict[str, JsonValue], ...]


class SourceInterfaceProjection(_Fact):
    version: Literal["data-operation-source-interfaces-v1"] = "data-operation-source-interfaces-v1"
    interpreter: str
    interpretation: str
    libraries: dict[str, str]
    modules: tuple[SourceModuleFacts, ...]
    operations: tuple[SourceOperationFacts, ...]
    unknowns: tuple[str, ...] = ()

    @property
    def content(self) -> bytes:
        return canonical_bytes(self.model_dump(mode="json"))

    @property
    def identity(self) -> str:
        return "source-interfaces:" + sha256(self.content).hexdigest()


def _plain(value: Any) -> JsonValue:
    if isinstance(value, Enum):
        return value.value
    if value is None or type(value) in {str, int, bool, float}:
        return value
    if isinstance(value, griffe.Expr):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if hasattr(value, "as_dict"):
        return _plain(value.as_dict())
    # Griffe documentation elements (parameters/returns/etc.) expose these
    # public documentation fields rather than a general model serialization.
    fields = {
        name: _plain(getattr(value, name))
        for name in ("name", "annotation", "description", "value")
        if hasattr(value, name)
    }
    if fields:
        return fields
    raise TypeError("unsupported structured documentation value " + type(value).__name__)


def _record(value: Any) -> dict[str, JsonValue]:
    result = _plain(value)
    if not isinstance(result, dict):
        raise TypeError("structured source fact must be a JSON object")
    return result


def export_source_interfaces(frontend, facts) -> SourceInterfaceProjection:
    """Consume the already resolved/enriched frontend, never create another visitor."""
    modules = tuple(
        SourceModuleFacts(
            module=source.module,
            path=source.filename,
            source_digest=sha256(source.content).hexdigest(),
            stub_digest=sha256(source.stub).hexdigest() if source.stub is not None else None,
            captured_artifact=f"data-operations/python/{index}.py",
        )
        for index, source in enumerate(frontend.inputs.sources)
    )
    by_module = {module.module: module for module in modules}
    operations = []
    unknowns = []
    for fact in facts:
        metadata = json.loads(fact.metadata)
        callables = []
        for surface in fact.surfaces:
            obj = frontend.resolve(surface.declaration)
            module = by_module[frontend._module_for(surface.declaration)]
            documentation = obj.docstring.value if obj.docstring is not None else None
            sections = ()
            if obj.docstring is not None:
                try:
                    # Final signature/parent enrichment has already completed.
                    sections = tuple(
                        _record(section.as_dict()) for section in obj.docstring.parse("google")
                    )
                except (ValueError, TypeError) as error:
                    unknowns.append(surface.declaration + ": documentation: " + str(error))
            signature = asdict(surface)
            signature["overloads"] = [json.loads(item) for item in surface.overloads]
            callables.append(
                SourceCallableFacts(
                    exposed=surface.exposed,
                    declaration=surface.declaration,
                    module=module.module,
                    path=module.path,
                    source_digest=module.source_digest,
                    line=obj.lineno,
                    end_line=obj.endlineno,
                    signature=_record(signature),
                    documentation=documentation,
                    sections=sections,
                    origin="modeled" if surface.declaration in frontend.generated else "extracted",
                )
            )
        operations.append(
            SourceOperationFacts(
                operation=metadata["id"],
                owner=fact.implementation.root,
                callables=tuple(callables),
                metadata=metadata,
                origins=tuple(asdict(origin) for origin in fact.origins),
            )
        )
    return SourceInterfaceProjection(
        interpreter=frontend.inputs.interpreter,
        interpretation=frontend.inputs.interpretation,
        libraries={name: version(name) for name in ("griffe", "libcst", "astroid")},
        modules=modules,
        operations=tuple(sorted(operations, key=lambda item: item.operation)),
        unknowns=tuple(unknowns),
    )


def read_source_interfaces(prepared) -> SourceInterfaceProjection | None:
    """An older archive's missing projection stays unavailable, never reconstructed."""
    matches = [
        artifact for artifact in prepared.artifacts if artifact.kind == SOURCE_INTERFACE_ARTIFACT
    ]
    if len(matches) > 1:
        raise ValueError("repeated archived source interface projection")
    return SourceInterfaceProjection.model_validate_json(matches[0].content) if matches else None

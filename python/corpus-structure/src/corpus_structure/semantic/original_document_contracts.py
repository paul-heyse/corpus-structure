"""Current original-document helper assets of the real source initialization operation."""

from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

from .identity import canonical_bytes
from .native_call_contracts import OperationCallBinding, OperationFieldBinding
from .types import SourceArtifact

if TYPE_CHECKING:
    from .native_program_registry import ProgramDeclaration

OPERATION = "data.initialize_source_project"
ASSET = "native/source-admission-calls.json"
CONTRACT = "source-admission/helper-bindings"
ROLE = "native-original-document-custody"


def source_call_bindings(*, target_metadata=None):
    """Derive fixed transport correspondences from their actual physical field owners."""
    from .metadata import get_metadata
    from .native_call_sources import resolve_call_bindings

    selected = get_metadata() if target_metadata is None else target_metadata

    def field(name, relation, column=None, *, native=None):
        target = selected.tables[relation].c[column or name]
        return OperationFieldBinding(
            name,
            f"physical:{relation}.{target.name}",
            bool(target.nullable),
            native_parameter=native,
        )

    registration = (
        "project_id",
        "key",
        "source_uri",
        "content_hash",
        "original_path",
        "mime",
        "title",
        "meta",
    )
    calls = (
        OperationCallBinding(
            id="source_document_registration",
            symbol="ops.register_original_document",
            parameters=(
                field("release_id", "sem.release", native="p_release"),
                *(
                    field(name, "kb.document", native="p_" + name)
                    for name in registration
                    if name != "key"
                ),
                field("original", "kb.source_artifact", "content", native="p_original"),
            ),
            result_fields=tuple(field(name, "kb.document") for name in ("id", *registration)),
            result_class="RegisteredOriginalDocument",
            cardinality="one",
            ordered=False,
            result_mode="table",
            json_read="json-text-v1",
            requires_context=True,
        ),
        OperationCallBinding(
            id="original_document_descriptor",
            symbol="semantic.original_documents.read_original_document_bytes",
            parameters=tuple(field(name, "kb.document") for name in ("project_id", "key")),
            result_fields=tuple(
                field(name, "kb.document")
                for name in ("id", "project_id", "key", "content_hash", "mime")
            ),
            result_class="OriginalDocumentDescriptor",
            cardinality="optional",
            ordered=False,
            result_mode="table",
            backend="core",
            requires_context=True,
        ),
        OperationCallBinding(
            id="original_document_artifact",
            symbol="semantic.original_documents.read_original_document_bytes",
            parameters=(field("artifact_digest", "kb.source_artifact"),),
            result_fields=(field("content", "kb.source_artifact"),),
            cardinality="optional",
            ordered=False,
            result_mode="scalar",
            backend="core",
            requires_context=True,
        ),
    )
    return resolve_call_bindings(
        tuple((OPERATION, call) for call in calls),
        logical_sources={"linkml:types": selected.info["physical_linkml_types"]},
        physical_sources=selected.info["physical_sources"],
        core_owners={(OPERATION, call.id): call.symbol for call in calls if call.backend == "core"},
    )


def source_admission_asset(*, target_metadata=None) -> SourceArtifact:
    from .metadata import get_metadata
    from .original_document_native import ASSET_DIGEST_BASIS, source_original_programs

    selected = get_metadata() if target_metadata is None else target_metadata

    return SourceArtifact(
        ASSET,
        canonical_bytes(
            {
                "version": "source-admission-helper-bindings-v1",
                "operation": OPERATION,
                "physical_model": selected.info["physical_model_id"],
                "calls": [
                    asdict(call) for _, call in source_call_bindings(target_metadata=selected)
                ],
                "sources": {
                    "original_document_contracts.py": sha256(
                        Path(__file__).read_bytes()
                    ).hexdigest(),
                    "original_documents.py": sha256(
                        Path(__file__).with_name("original_documents.py").read_bytes()
                    ).hexdigest(),
                    "original_document_native.py": sha256(
                        Path(__file__).with_name("original_document_native.py").read_bytes()
                    ).hexdigest(),
                    "source-originals.generated.sql": sha256(
                        source_original_programs(selected, ASSET_DIGEST_BASIS).encode()
                    ).hexdigest(),
                },
            }
        ),
    )


def source_admission_sources(*, target_metadata=None) -> tuple[SourceArtifact, ...]:
    from .metadata import get_metadata
    from .original_document_native import source_original_programs

    selected = get_metadata() if target_metadata is None else target_metadata
    asset = source_admission_asset(target_metadata=selected)
    return (
        asset,
        SourceArtifact("native/original-document-contracts.py", Path(__file__).read_bytes()),
        SourceArtifact(
            "native/original-documents.py",
            Path(__file__).with_name("original_documents.py").read_bytes(),
        ),
        SourceArtifact(
            "native/original-document-native.py",
            Path(__file__).with_name("original_document_native.py").read_bytes(),
        ),
        SourceArtifact(
            "native/source-originals.sql", source_original_programs(selected, asset.digest).encode()
        ),
    )


def operation_asset(sources) -> tuple[str, dict]:
    selected = [source for source in sources if source.name == ASSET]
    if len(selected) != 1:
        raise ValueError("source admission requires one captured helper asset")
    source = selected[0]
    content = json.loads(source.content)
    if (
        content.get("version") != "source-admission-helper-bindings-v1"
        or content.get("operation") != OPERATION
    ):
        raise ValueError("unsupported source admission helper asset")
    return content["operation"], {
        "reference": ASSET,
        "contract": CONTRACT,
        "role": ROLE,
        "content_digest": source.digest,
    }


def require_source_operation_context(prepared):
    from .data_operation_admission import bound_data_operation_model

    owner = bound_data_operation_model(prepared).operation(OPERATION)
    expected = source_admission_asset()
    if not any(
        asset.reference == ASSET
        and asset.contract == CONTRACT
        and asset.role == ROLE
        and asset.content_digest == expected.digest
        for asset in owner.assets
    ):
        raise ValueError("source helper asset differs from the checked operation")
    return owner


def require_source_call_context(prepared, operation: str, variant: str, digest: str) -> None:
    if operation != OPERATION:
        raise ValueError("source helper has a foreign operation owner")
    require_source_operation_context(prepared)
    calls = [asdict(call) for _, call in source_call_bindings() if call.id == variant]
    if len(calls) != 1 or sha256(canonical_bytes(calls)).hexdigest() != digest:
        raise ValueError("source helper call correspondence differs")


def require_source_database_context(connection, prepared) -> None:
    from sqlalchemy import Text, bindparam, func, select

    connection.execute(
        select(
            func.ops.require_source_admission(
                bindparam("_source_release", prepared.release_id, type_=Text())
            )
        )
    ).scalar_one()


def source_original_declarations(
    *, target_metadata=None, sources=None
) -> tuple[ProgramDeclaration, ...]:
    """Regenerate from the explicit model and independently captured helper asset."""
    from .metadata import get_metadata
    from .native_objects import native_sql_script
    from .original_document_native import source_original_native_programs

    selected = get_metadata() if target_metadata is None else target_metadata
    captured = (
        source_admission_sources(target_metadata=selected) if sources is None else tuple(sources)
    )
    by_name = {source.name: source for source in captured}
    declarations = source_original_native_programs(selected, by_name[ASSET].digest)
    if (
        native_sql_script(item.routine.render() for item in declarations).encode()
        != by_name["native/source-originals.sql"].content
    ):
        raise ValueError(
            "original source declarations differ from captured model/helper statements"
        )
    return declarations


def source_original_sql(sources=None) -> str:
    selected = source_admission_sources() if sources is None else sources
    return next(
        source.content.decode()
        for source in selected
        if source.name == "native/source-originals.sql"
    )


def generated_source_calls(*, target_metadata=None) -> str:
    from corpus_structure.schema.code_generation import _format

    from .metadata import get_metadata
    from .native_call_generation import render_call_bindings

    selected = get_metadata() if target_metadata is None else target_metadata
    return _format(
        "semantic/_source_admission_calls.py",
        render_call_bindings(
            source_call_bindings(target_metadata=selected),
            selected,
            canonical_identifiers=True,
            identifiers_module="._source_admission_enums",
            context_validator=(".original_document_contracts", "require_source_call_context"),
            value_base=(".data_operation_ports", "DataOperationWireValue"),
            row_base=(".data_operation_ports", "DataOperationNativeRow"),
        ),
    )


if __name__ == "__main__":
    Path(__file__).with_name("_source_admission_calls.py").write_text(generated_source_calls())

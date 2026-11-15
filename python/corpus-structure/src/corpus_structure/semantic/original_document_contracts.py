"""Current original-document helper assets of the real source initialization operation."""

from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from .identity import canonical_bytes
from .native_call_contracts import OperationCallBinding, OperationFieldBinding
from .types import SourceArtifact

OPERATION = "data.initialize_source_project"
ASSET = "native/source-admission-calls.json"
CONTRACT = "source-admission/helper-bindings"
ROLE = "native-original-document-custody"
_ROOT = Path(__file__).resolve().parents[1]
_SQL = Path(__file__).with_name("sql") / "source_originals.sql"


def source_call_bindings(*, target_metadata=None):
    """Derive fixed transport correspondences from their actual physical field owners."""
    from .metadata import metadata
    from .native_call_sources import resolve_call_bindings

    metadata = metadata if target_metadata is None else target_metadata

    def field(name, relation, column=None, *, native=None):
        target = metadata.tables[relation].c[column or name]
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
                    for name in registration if name != "key"
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
        logical_sources={"linkml:types": metadata.info["physical_linkml_types"]},
        physical_sources=metadata.info["physical_sources"],
        core_owners={(OPERATION, call.id): call.symbol for call in calls if call.backend == "core"},
    )


def source_admission_asset(*, target_metadata=None) -> SourceArtifact:
    from .metadata import metadata

    selected = metadata if target_metadata is None else target_metadata

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
                    "source_originals.sql": sha256(_SQL.read_bytes()).hexdigest(),
                },
            }
        ),
    )


def source_admission_sources(
    *, physical_sources=None, linkml_types=None
) -> tuple[SourceArtifact, ...]:
    from corpus_structure.schema.physical import compile_physical

    if physical_sources is not None and not isinstance(linkml_types, bytes):
        raise ValueError("explicit source helper capture requires LinkML types")
    selected = (
        None
        if physical_sources is None
        else compile_physical(physical_sources, linkml_types=linkml_types)
    )
    return (
        source_admission_asset(target_metadata=selected),
        SourceArtifact("native/original-document-contracts.py", Path(__file__).read_bytes()),
        SourceArtifact(
            "native/original-documents.py",
            Path(__file__).with_name("original_documents.py").read_bytes(),
        ),
        SourceArtifact("native/source-originals.sql", _SQL.read_bytes()),
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


def source_original_sql(sources=None) -> str:
    if sources is None:
        asset, sql = source_admission_asset(), _SQL.read_bytes()
    else:
        selected = {source.name: source for source in sources}
        asset, sql = selected[ASSET], selected["native/source-originals.sql"].content
    return sql.decode().replace("__SOURCE_ADMISSION_ASSET__", asset.digest)


def generated_source_calls() -> str:
    from corpus_structure.schema.generate import _format

    from .metadata import metadata
    from .native_call_generation import render_call_bindings

    return _format(
        "semantic/_source_admission_calls.py",
        render_call_bindings(
            source_call_bindings(),
            metadata,
            canonical_identifiers=True,
            identifiers_module="._source_admission_enums",
            context_validator=(".original_document_contracts", "require_source_call_context"),
            value_base=(".data_operation_ports", "DataOperationWireValue"),
            row_base=(".data_operation_ports", "DataOperationNativeRow"),
        ),
    )


if __name__ == "__main__":
    Path(__file__).with_name("_source_admission_calls.py").write_text(generated_source_calls())

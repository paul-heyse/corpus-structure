"""Released source, schema, codec and library determinants of PDF record fidelity."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from .determinants import determinant_version
from .identity import canonical_bytes
from .types import SourceArtifact, SourceBundle

LOWERING_CONTRACT = "implementation/pdf/lowering-contract.json"
LOWERING_PREFIX = "implementation/pdf/lowering/"
LOWERING_LIBRARIES = (
    "docling-core",
    "pydantic",
    "pydantic-core",
    "jsonschema",
    "referencing",
    "pyarrow",
    "linkml",
    "linkml-runtime",
    "cattrs",
    "PyYAML",
    "sqlalchemy",
    "pglast",
    "python",
    "unicode-identity",
)
# Explicit runtime responsibility closure. These are captured bytes, not a
# checkout hash substituted for an archived lowering contract.
LOWERING_FILES = (
    "semantic/pdf_lowering.py",
    "semantic/pdf_certification.py",
    "semantic/pdf_shared_streams.py",
    "semantic/pdf_shared_stream_queries.py",
    "semantic/pdf_shared_stream_writes.py",
    "semantic/_pdf_native_calls.py",
    "semantic/_pdf_native_ids.py",
    "semantic/operation_value_types.py",
    "semantic/native_sql_body.py",
    "semantic/native_program.py",
    "semantic/native_call_contracts.py",
    "semantic/pdf_certification_native.py",
    "semantic/pdf_publication_read_native.py",
    "semantic/pdf_publication_native.py",
    "semantic/pdf_companion_read_native.py",
    "semantic/pdf_domain_native.py",
    "semantic/pdf_publication.py",
    "semantic/pdf_record_reader.py",
    "semantic/pdf_record_reader_native.py",
    "semantic/pdf_records.py",
    "semantic/pdf_record_identity.py",
    "semantic/pdf_record_model.py",
    "semantic/pdf_staging.py",
    "semantic/metadata.py",
    "schema/physical.py",
    "schema/relational.py",
    "semantic/native_shapes.py",
    "semantic/pdf_staging_native.py",
    "semantic/prepared_sql.py",
    "semantic/pdf_payloads.py",
    "semantic/pdf_payload_validation.py",
    "semantic/pdf_ocr_contracts.py",
    "semantic/pdf_contracts.py",
    "semantic/pdf_integrated.py",
    "semantic/identity.py",
    "semantic/value_codec.py",
    "semantic/arrow_transfer.py",
    "ingest/pdf.py",
    "ingest/pdf_worker.py",
    "ingest/pdf_stream_types.py",
    "ingest/pdf_streaming.py",
    "ingest/pdf_record_product.py",
    "ingest/pdf_build_spool.py",
    "ingest/pdf_hierarchy.py",
    "ingest/pdf_assembly.py",
    "ingest/pdf_candidate_source.py",
    "ingest/pdf_candidates.py",
    "ingest/pdf_ocr.py",
    "ingest/pdf_reconciliation.py",
    "model/semantic/pdf-records.yaml",
    "model/semantic/pdf-staging.yaml",
    "model/semantic/pdf-products.yaml",
    "model/semantic/pdf-payloads.yaml",
    "model/semantic/core.yaml",
    "model/semantic/docling-validation.schema.json",
    "semantic/sql/pdf_record_identity.sql",
    "semantic/sql/pdf_record_artifact_identity.sql",
    "semantic/sql/pdf_record_logical_identity.sql",
    "semantic/sql/pdf_record_access_correspondence.sql",
    "semantic/sql/pdf_record_context.sql",
)


@lru_cache(maxsize=1)
def _current_boundary():
    from importlib.resources import files

    from .file_custody import verified_file
    from .pdf_domain import _action_sources

    _actions, sources, _diagnostics = _action_sources()
    root = Path(__file__).resolve().parents[1] / "model/semantic"
    records = []
    logical_files = {
        "pdf_products": "pdf-products.yaml",
        "core": "core.yaml",
        "pdf_records": "pdf-records.yaml",
        "pdf_staging": "pdf-staging.yaml",
        "read_projections": "read-projections.yaml",
        "companion_projections": "companion-projections.yaml",
        "selected_source": "selected-source.yaml",
    }
    for source in sources:
        if source.name == "pdf-domain/native/actions.yaml":
            records.append(verified_file(root / "pdf-actions.yaml", source.digest))
        elif source.name.startswith("pdf-domain/physical/"):
            records.append(
                verified_file(
                    root / source.name.removeprefix("pdf-domain/physical/"), source.digest
                )
            )
        elif source.name == "pdf-domain/logical/linkml:types":
            records.append(
                verified_file(
                    Path(
                        str(
                            files("linkml_runtime").joinpath("linkml_model/model/schema/types.yaml")
                        )
                    ),
                    source.digest,
                )
            )
        elif source.name.startswith("pdf-domain/logical/"):
            records.append(
                verified_file(
                    root / logical_files[source.name.removeprefix("pdf-domain/logical/")],
                    source.digest,
                )
            )
    return sources, tuple(records)


def lowering_sources(boundary_sources=None) -> tuple[SourceArtifact, ...]:
    """Prepare once for exact captured inputs; mutable file premises still recheck."""
    if boundary_sources is None:
        boundary_sources, records = _current_boundary()
        for record in records:
            record.check()
    sources, records = _prepared_lowering_sources(tuple(boundary_sources))
    for record in records:
        record.check()
    return sources


@lru_cache(maxsize=4)
def _prepared_lowering_sources(boundary_sources):
    sources, custody = _implementation_sources()
    for record in custody:
        record.check()
    import yaml

    from corpus_structure.schema.physical import compile_physical

    from .pdf_payloads import FAMILY, prepare_payload_schema, schema_dump
    from .pdf_publication import COMPANION_STAGE_TARGETS
    from .pdf_record_model import record_arrow_schema
    from .pdf_staging import UPLOAD_STAGE_FAMILIES
    from .prepare import prepare_release

    logical = {
        source.name.removeprefix("pdf-domain/logical/"): source.content
        for source in boundary_sources
        if source.name.startswith("pdf-domain/logical/")
    }
    physical = {
        source.name.removeprefix("pdf-domain/physical/"): source.content
        for source in boundary_sources
        if source.name.startswith("pdf-domain/physical/")
    }
    model = compile_physical(physical, linkml_types=logical["linkml:types"])

    boundary = prepare_release(
        SourceBundle(
            "pdf_domain_schema",
            (
                SourceArtifact("pdf_products", logical["pdf_products"]),
                SourceArtifact("core", logical["core"]),
                SourceArtifact(
                    "pdf_domain_schema",
                    canonical_bytes(
                        {
                            "id": "urn:corpus:pdf-domain-schema",
                            "name": "pdf_domain_schema",
                            "imports": ["pdf_products", "core"],
                        }
                    ),
                ),
            ),
        )
    )
    classes = json.loads(
        yaml.safe_load(logical["pdf_staging"])["annotations"]["pds:metadata_classes"]
    )
    schemas = {kind: boundary.json_schema(cls) for kind, cls in classes.items()}
    sources = (
        *sources,
        *(
            SourceArtifact(
                "pdf-domain/" + LOWERING_PREFIX + "schema/" + kind + ".json", schema_dump(schema)
            )
            for kind, schema in sorted(schemas.items())
        ),
        SourceArtifact(
            "pdf-domain/" + LOWERING_PREFIX + "codec/inline-candidates.arrow",
            prepare_payload_schema(schemas[FAMILY]).arrow_schema.serialize().to_pybytes(),
        ),
    )
    sources = (
        *sources,
        *(
            SourceArtifact(
                "pdf-domain/" + LOWERING_PREFIX + "codec/" + name + ".arrow",
                record_arrow_schema(name, model=model).serialize().to_pybytes(),
            )
            for name in sorted(
                set(UPLOAD_STAGE_FAMILIES.values()) | set(COMPANION_STAGE_TARGETS.values())
            )
        ),
    )
    contract = SourceArtifact(
        "pdf-domain/" + LOWERING_CONTRACT,
        canonical_bytes(
            {
                "profile": "pdf-record-lowering-contract-v1",
                "inputs": [
                    {"name": source.name, "sha256": source.digest}
                    for source in (*sources, *boundary_sources)
                ],
                "libraries": {name: determinant_version(name) for name in LOWERING_LIBRARIES},
            }
        ),
    )
    return (contract, *sources), custody


@lru_cache(maxsize=1)
def _implementation_sources():
    """A new target preparation cannot rebase already loaded executable code."""
    from .file_custody import verified_file

    root = Path(__file__).resolve().parents[1]
    sources = tuple(
        SourceArtifact("pdf-domain/" + LOWERING_PREFIX + name, root.joinpath(name).read_bytes())
        for name in LOWERING_FILES
    )
    custody = tuple(
        verified_file(root / name, source.digest)
        for name, source in zip(LOWERING_FILES, sources, strict=True)
    )
    return sources, custody


def require_lowering_identity(context) -> str:
    """Use the exact retained artifact only after matching its executable closure."""
    from hashlib import sha256

    if context.domain is None:
        raise ValueError("PDF certification requires its released lowering contract")
    retained = context.domain.source(LOWERING_CONTRACT)
    from .metadata import metadata

    current_boundary, _records = _current_boundary()
    actual_physical = {
        source.name.removeprefix("pdf-domain/physical/"): source.content
        for source in current_boundary
        if source.name.startswith("pdf-domain/physical/")
    }
    actual_types = next(
        source.content
        for source in current_boundary
        if source.name == "pdf-domain/logical/linkml:types"
    )
    if (
        metadata.info["physical_sources"] != actual_physical
        or metadata.info["physical_linkml_types"] != actual_types
    ):
        raise ValueError("PDF runtime metadata differs from the lowering basis; restart required")
    current = lowering_sources()
    if retained.content != current[0].content:
        raise ValueError("PDF lowering contract differs from the captured execution basis")
    declared = json.loads(retained.content)
    for item in declared["inputs"]:
        name = item["name"].removeprefix("pdf-domain/")
        captured = context.domain.source(name)
        if sha256(captured.content).hexdigest() != item["sha256"]:
            raise ValueError("captured PDF lowering source differs from its contract")
    return retained.digest

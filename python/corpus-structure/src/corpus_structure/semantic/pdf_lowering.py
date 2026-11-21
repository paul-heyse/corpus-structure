"""Released source, schema, codec and library determinants of PDF record fidelity."""

from __future__ import annotations

import json
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from corpus_structure.caches import declare
from corpus_structure.model.compiled import model_projection

from .determinants import determinant_version
from .identity import canonical_bytes
from .types import SourceArtifact, SourceBundle

LOWERING_CONTRACT = "implementation/pdf/lowering-contract.json"
LOWERING_PREFIX = "implementation/pdf/lowering/"
LOWERING_ENTRY_MODULES = (
    "corpus_structure.semantic.pdf_records",
    "corpus_structure.semantic.pdf_certification",
    "corpus_structure.ingest.pdf_record_product",
    "corpus_structure.semantic.pdf_integrated",
)
LOWERING_ENTRY_CALLABLES = (
    "corpus_structure.semantic.pdf_records.iter_native_records",
    "corpus_structure.semantic.pdf_records.reconstruct_native_document",
    "corpus_structure.semantic.pdf_records.validate_native_callbacks",
    "corpus_structure.semantic.pdf_certification.PdfProducerPayloads.certify",
    "corpus_structure.semantic.pdf_certification.write_pdf_companion_sets",
    "corpus_structure.ingest.pdf_record_product.native_publication_draft",
    "corpus_structure.semantic.pdf_integrated.prepare_integrated_pdf_product",
)

PRODUCER_IDENTITY_INPUTS = frozenset(
    {
        "pdf-domain/" + LOWERING_CONTRACT,
        "pdf-domain/" + LOWERING_PREFIX + "code/meaning.json",
    }
)


@model_projection
def _current_boundary():
    from .pdf_domain import _action_sources

    _, sources, _ = _action_sources()
    return sources


def lowering_sources(
    boundary_sources=None, *, include_producer=True, model_sources=None, standard_producer=None
) -> tuple[SourceArtifact, ...]:
    """Prepare once for exact captured inputs; mutable file premises still recheck."""
    if boundary_sources is None:
        boundary_sources = _current_boundary()
    if model_sources is None:
        from corpus_structure.model.compiled import model_source

        native_schema = model_source("docling-validation.schema.json")
    else:
        native_schema = model_sources["docling-validation.schema.json"]
    sources, records = _prepared_lowering_sources(
        tuple(boundary_sources), include_producer, native_schema, standard_producer
    )
    for record in records:
        record.check()
    return sources


@declare(
    "pdf-lowering",
    "release_bytes",
    weight=lambda result: max(1, sum(len(source.content) for source in result[0])),
)
def _prepared_lowering_sources(boundary_sources, include_producer, native_schema, standard_producer):
    sources, custody = _implementation_sources(include_producer, native_schema, standard_producer)
    for record in custody:
        record.check()
    import yaml

    from corpus_structure.schema.physical import compile_physical

    from .pdf_companion_encoding import COMPANION_STAGE_TARGETS
    from .pdf_payloads import FAMILY, prepare_payload_schema, schema_dump
    from .pdf_record_model import record_arrow_schema
    from .pdf_staging import UPLOAD_STAGE_FAMILIES
    from .prepare import prepare_release
    from .types import SEMANTIC_COMPILER_VERSION

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
                SourceArtifact("pdf-observation-vocabulary", logical["pdf-observation-vocabulary"]),
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
    if not include_producer:
        return sources, custody
    code = _lowering_code() if standard_producer is None else None
    if standard_producer is not None:
        standard_producer.check()
    contract = SourceArtifact(
        "pdf-domain/" + LOWERING_CONTRACT,
        canonical_bytes(
            {
                "profile": "pdf-record-lowering-contract-v2" if standard_producer is None else "pdf-record-lowering-contract-v3",
                "compiler_policy": SEMANTIC_COMPILER_VERSION,
                "code_identity": {
                    **({
                        "complete": code.complete,
                        "sha256": code.digest,
                        "unknowns": sorted({(item.module, item.reason) for item in code.unknowns}),
                    } if code is not None else {
                        "complete": True,
                        "sha256": standard_producer.digest,
                        "scope": "docling-standard-pdf-stream-v1",
                    }),
                },
                "inputs": [
                    {"name": source.name, "sha256": source.digest}
                    for source in (*sources, *boundary_sources)
                ],
                "libraries": {
                    **({distribution: version for _, distribution, version in code.distributions} if code is not None else json.loads(standard_producer.content)["distributions"]),
                    "python": determinant_version("python"),
                    "unicode-identity": determinant_version("unicode-identity"),
                },
            }
        ),
    )
    return (contract, *sources), custody


@lru_cache(maxsize=1)
def _lowering_code():
    from .code_identity import capture_code_identity

    return capture_code_identity(
        Path(__file__).resolve().parents[1],
        LOWERING_ENTRY_MODULES,
        callables=LOWERING_ENTRY_CALLABLES,
    )


def lowering_code_provenance() -> dict:
    """Inspect exact generator custody independently of reusable output meaning."""
    return _lowering_code().provenance()


def lowering_code_complete() -> bool:
    code = _lowering_code()
    if code.complete:
        from corpus_structure._query_custody import capture_workload_sources

        capture_workload_sources(Path(__file__).resolve().parents[1], code)
    return code.complete


@lru_cache(maxsize=2)
def _implementation_sources(include_producer, native_schema: bytes, standard_producer=None):
    """Capture normalized code meaning while retaining exact loaded-file custody."""
    from .file_custody import verified_file

    root = Path(__file__).resolve().parents[1]
    schema_source = SourceArtifact(
        "pdf-domain/" + LOWERING_PREFIX + "schema/docling-native.json", native_schema
    )
    if not include_producer:
        return (schema_source,), ()
    if standard_producer is not None:
        standard_producer.check()
        return (
            SourceArtifact("pdf-domain/" + LOWERING_PREFIX + "code/meaning.json", standard_producer.content),
            schema_source,
        ), tuple(verified_file(Path(path), digest) for path, digest in (*standard_producer.first_party, *standard_producer.files))
    code = _lowering_code()
    if code.complete:
        from corpus_structure._query_custody import capture_workload_sources

        capture_workload_sources(root, code)
    sources = (
        SourceArtifact("pdf-domain/" + LOWERING_PREFIX + "code/meaning.json", code.meaning),
        schema_source,
    )
    custody = (
        *tuple(
            verified_file(root / source.filename, sha256(source.content).hexdigest())
            for source in code.modules
        ),
    )
    return sources, custody


def lowering_reuse_complete(context) -> bool:
    """Computation is available when code identity is incomplete; reuse is withheld."""
    require_lowering_identity(context)
    return json.loads(context.domain.source(LOWERING_CONTRACT).content)["code_identity"]["complete"]


def require_lowering_identity(context) -> str:
    """Use the exact retained artifact only after matching its executable closure."""
    from hashlib import sha256

    if context.domain is None:
        raise ValueError("PDF certification requires its released lowering contract")
    retained = context.domain.source(LOWERING_CONTRACT)
    from .metadata import get_metadata

    current_boundary = _current_boundary()
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
        get_metadata().info["physical_sources"] != actual_physical
        or get_metadata().info["physical_linkml_types"] != actual_types
    ):
        raise ValueError("PDF runtime metadata differs from the lowering basis; restart required")
    standard_producer = None
    if json.loads(retained.content)["profile"] == "pdf-record-lowering-contract-v3":
        from corpus_structure.ingest.pdf_producer_contract import standard_pdf_contract

        standard_producer = standard_pdf_contract()
    current = lowering_sources(standard_producer=standard_producer)
    if retained.content != current[0].content:
        raise ValueError("PDF lowering contract differs from the captured execution basis")
    declared = json.loads(retained.content)
    for item in declared["inputs"]:
        name = item["name"].removeprefix("pdf-domain/")
        captured = context.domain.source(name)
        if sha256(captured.content).hexdigest() != item["sha256"]:
            raise ValueError("captured PDF lowering source differs from its contract")
    return retained.digest

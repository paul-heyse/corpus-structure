"""Released source, schema, codec and library determinants of PDF record fidelity."""

from __future__ import annotations

import json
from pathlib import Path

from .determinants import determinant_version
from .identity import canonical_bytes
from .types import SourceArtifact, SourceBundle

LOWERING_CONTRACT = "implementation/pdf/lowering-contract.json"
LOWERING_PREFIX = "implementation/pdf/lowering/"
LOWERING_LIBRARIES = (
    "docling-core", "pydantic", "pydantic-core", "jsonschema", "referencing",
    "pyarrow", "linkml-runtime", "cattrs", "PyYAML", "msgspec", "sqlalchemy", "python", "unicode-identity",
)
# Explicit runtime responsibility closure. These are captured bytes, not a
# checkout hash substituted for an archived lowering contract.
LOWERING_FILES = (
    "semantic/pdf_lowering.py", "semantic/pdf_certification.py",
    "semantic/pdf_publication_native.py", "semantic/pdf_domain_native.py",
    "semantic/pdf_publication.py", "semantic/pdf_records.py",
    "semantic/pdf_record_identity.py", "semantic/pdf_record_model.py",
    "semantic/pdf_payloads.py", "semantic/pdf_payload_validation.py",
    "semantic/pdf_ocr_contracts.py", "semantic/pdf_contracts.py", "semantic/pdf_integrated.py",
    "semantic/identity.py", "semantic/value_codec.py", "ingest/pdf_streaming.py", "ingest/pdf_record_product.py",
    "model/semantic/pdf-records.yaml", "model/semantic/pdf-staging.yaml",
    "model/semantic/pdf-products.yaml", "model/semantic/core.yaml", "model/semantic/docling-validation.schema.json",
    "semantic/sql/pdf_record_identity.sql", "semantic/sql/pdf_record_artifact_identity.sql",
    "semantic/sql/pdf_record_logical_identity.sql", "semantic/sql/pdf_record_access_correspondence.sql",
)


def lowering_sources() -> tuple[SourceArtifact, ...]:
    root = Path(__file__).resolve().parents[1]
    sources = tuple(SourceArtifact("pdf-domain/" + LOWERING_PREFIX + name,
                                   root.joinpath(name).read_bytes()) for name in LOWERING_FILES)
    from .prepare import prepare_release
    from .pdf_payload_validation import metadata_classes
    from .pdf_payloads import FAMILY, prepare_payload_schema, schema_dump

    boundary = prepare_release(SourceBundle("pdf_domain_schema", (
        SourceArtifact("pdf_products", root.joinpath("model/semantic/pdf-products.yaml").read_bytes()),
        SourceArtifact("core", root.joinpath("model/semantic/core.yaml").read_bytes()),
        SourceArtifact("pdf_domain_schema", canonical_bytes({"id": "urn:corpus:pdf-domain-schema",
            "name": "pdf_domain_schema", "imports": ["pdf_products", "core"]})),
    )))
    schemas = {kind: boundary.json_schema(cls) for kind, cls in metadata_classes().items()}
    sources = (*sources, *(SourceArtifact("pdf-domain/" + LOWERING_PREFIX + "schema/" + kind + ".json",
                                         schema_dump(schema)) for kind, schema in sorted(schemas.items())),
               SourceArtifact("pdf-domain/" + LOWERING_PREFIX + "codec/inline-candidates.arrow",
                              prepare_payload_schema(schemas[FAMILY]).arrow_schema.serialize().to_pybytes()))
    contract = SourceArtifact("pdf-domain/" + LOWERING_CONTRACT, canonical_bytes({
        "profile": "pdf-record-lowering-contract-v1",
        "inputs": [{"name": source.name, "sha256": source.digest} for source in sources],
        "libraries": {name: determinant_version(name) for name in LOWERING_LIBRARIES},
    }))
    return (contract, *sources)


def require_lowering_identity(context) -> str:
    """Use the exact retained artifact only after matching its executable closure."""
    from hashlib import sha256

    if context.domain is None:
        raise ValueError("PDF certification requires its released lowering contract")
    retained = context.domain.source(LOWERING_CONTRACT)
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

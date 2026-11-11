"""Semantic source-project initialization and indexed original-byte acquisition."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import Connection

from corpus_structure.orchestrate.registry import MethodRegistry
from corpus_structure.semantic.product_reference import ProductReference


class ProjectError(ValueError):
    """A project or pack that cannot be registered as it stands."""


class SourceProjectReport(BaseModel):
    project: str
    release_id: str
    realization_id: str
    documents: int


def init_bound_project(
    conn: Connection,
    *,
    domain: str,
    corpus: Path,
    release_id: str,
    realization_id: str,
    name: str | None = None,
    domains: Path | None = None,
    registry: MethodRegistry | None = None,
    native_product: ProductReference | None = None,
    integrated_product: ProductReference | None = None,
) -> SourceProjectReport:
    """Register real indexed source documents against an explicitly admitted interpretation."""
    from corpus_structure.orchestrate.phase0 import registry as registry_for
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.operations import register_document
    from corpus_structure.semantic.releases import load_release

    if native_product is not None and integrated_product is not None:
        raise ProjectError("native and integrated source pins are mutually exclusive")
    try:
        prepared = load_release(conn, release_id)
        from corpus_structure.semantic.contracts import require_bound_operation

        require_bound_operation(prepared, "construct_project")
    except KeyError as exc:
        raise ProjectError("semantic release is not admitted") from exc
    pack = (domains or DOMAINS) / domain
    registry = (registry or registry_for(pack)).bind_release(prepared)
    project_id = name or domain
    retained_document = None
    if native_product is not None or integrated_product is not None:
        from sqlalchemy import select

        from corpus_structure.orchestrate.pdf_source import retained_source_document
        from corpus_structure.orchestrate.phase0 import bind_pdf_selection
        from corpus_structure.semantic.metadata import table

        document = table("kb.document")
        registered = list(
            conn.execute(select(document).where(document.c.project_id == project_id)).mappings()
        )
        exact_product = integrated_product if integrated_product is not None else native_product
        assert exact_product is not None
        retained_document = retained_source_document(
            conn,
            exact_product,
            prepared=prepared,
            project_id=project_id,
            documents=registered,
            role="integrated" if integrated_product is not None else "native",
        )
        registry = bind_pdf_selection(registry, document=retained_document)
    from sqlalchemy.exc import DBAPIError

    try:
        from corpus_structure.semantic._operation_calls import initialize_source_project
        from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId

        initialize_source_project(
            conn,
            project_id=ProjectId(project_id),
            release_id=ReleaseId(release_id),
            realization_id=RealizationId(realization_id),
            projection_context=prepared,
        )
    except DBAPIError as exc:
        if getattr(exc.orig, "sqlstate", None) in {"P0001", "P0004"}:
            raise ProjectError(str(exc.orig).split("\n")[0]) from exc
        raise
    seen = set()
    profiles = set()
    count = 0
    for method, config in registry.named():
        if registry.method(method).family != "ingest":
            continue
        from corpus_structure.ingest.pdf_methods import PdfIngestConfig

        configured = registry.resolve(method, config).config
        if isinstance(configured, PdfIngestConfig):
            profiles.add("pdf-originals")
            for uri in configured.originals:
                if uri in seen:
                    continue
                original = (corpus / uri).resolve()
                if (
                    not original.is_relative_to(corpus.resolve())
                    or original.suffix.lower() != ".pdf"
                ):
                    raise ProjectError("PDF original must remain within the selected corpus")
                raw = original.read_bytes()
                if (
                    retained_document is not None
                    and sha256(raw).hexdigest() != retained_document.content_hash
                ):
                    raise ProjectError("retained PDF file differs from its authenticated original")
                if not raw.startswith(b"%PDF-"):
                    raise ProjectError(f"configured original is not a PDF: {uri}")
                # Exact retained custody already identifies a registered original.
                # Re-registering it would replace its immutable source descriptor
                # with incidental pack title/metadata, even when bytes are unchanged.
                if retained_document is None:
                    register_document(
                        conn,
                        project_id=project_id,
                        source_uri=uri,
                        original_path=str(original),
                        original=raw,
                        mime="application/pdf",
                        title=original.stem,
                        metadata={
                            "input_format": "pdf",
                            "source_inventory": "configured-pdf-originals",
                        },
                        prepared=prepared,
                    )
                seen.add(uri)
                count += 1
            continue
    if not profiles:
        raise ProjectError("method pack declares no PDF originals")
    return SourceProjectReport(
        project=project_id, release_id=release_id, realization_id=realization_id, documents=count
    )

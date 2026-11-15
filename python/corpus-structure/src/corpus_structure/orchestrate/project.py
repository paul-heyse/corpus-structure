"""Register immutable source originals without constructing an execution registry."""

from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import Connection

from corpus_structure.semantic.data_operation_support import OriginalDocumentRef


class ProjectError(ValueError):
    """A project or source pack cannot be registered as supplied."""


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
    originals: tuple[OriginalDocumentRef, ...] = (),
) -> SourceProjectReport:
    """Register pack-declared PDF originals against explicit admitted interpretation.

    The pack supplies an input inventory only. It does not choose executable
    methods, defaults, runtime providers or stage order.
    """
    import yaml

    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.original_document_contracts import require_source_operation_context
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.original_documents import register_original_document
    from corpus_structure.semantic.releases import load_release

    if not domain or Path(domain).name != domain or domain in {".", ".."}:
        raise ProjectError("domain must name a declared pack")
    prepared = load_release(conn, release_id)
    require_source_operation_context(prepared)
    project_id = name or domain
    retained_bytes = {}
    if originals:
        from corpus_structure.semantic.original_documents import acquire_original_document_selection, read_original_document_bytes

        if len({value.document_key for value in originals}) != len(originals):
            raise ProjectError("retained originals must be distinct exact document keys")
        paths = []
        for reference in originals:
            if reference.project_id != project_id:
                raise ProjectError("retained original belongs to another project")
            retained = acquire_original_document_selection(
                conn, project_id=project_id, document_key=reference.document_key
            )
            if retained.reference != reference:
                raise ProjectError("retained original differs from its authenticated metadata")
            raw = read_original_document_bytes(conn, reference, prepared=prepared)
            retained_bytes[reference.document_key] = raw
            paths.append(reference.document_key)
    else:
        pack = (domains or DOMAINS) / domain
        inventory = yaml.safe_load((pack / "methods.yaml").read_text())
        configurations = inventory.get("configs", {})
        paths = []
        for owner in ("ingest.pdf", "ingest.pdf_integrated"):
            for configuration in configurations.get(owner, {}).values():
                values = configuration.get("originals", ())
                if not isinstance(values, (list, tuple)) or any(
                    not isinstance(value, str) or not value for value in values
                ):
                    raise ProjectError("PDF inventory requires exact original paths")
                paths.extend(values)
        paths = list(dict.fromkeys(paths))
    if not paths:
        raise ProjectError("source pack declares no PDF originals")
    root = corpus.resolve()
    acquired = []
    for uri in paths:
        if originals:
            raw = retained_bytes[uri]
            original = None
        else:
            original = (root / uri).resolve()
            if not original.is_relative_to(root) or original.suffix.lower() != ".pdf":
                raise ProjectError("PDF original must remain within the selected corpus")
            raw = original.read_bytes()
        if not raw.startswith(b"%PDF-"):
            raise ProjectError("configured original is not a PDF: " + uri)
        acquired.append((uri, original, raw))
    from corpus_structure.semantic.identifiers import ProjectId, RealizationId, ReleaseId

    result = DataOperationStorage(conn).initialize_source_project({
        "project_id": ProjectId(project_id), "release_id": ReleaseId(release_id),
        "realization_id": RealizationId(realization_id),
    })
    if result != {"project_id": project_id, "release_id": release_id, "realization_id": realization_id}:
        raise ProjectError("initialized project context differs from its exact requested identities")
    for uri, original, raw in acquired:
        if originals:
            continue
        if original is None:
            raise ProjectError("new source registration requires its acquired original path")
        register_original_document(
            conn,
            project_id=project_id,
            source_uri=uri,
            original_path=str(original),
            original=raw,
            mime="application/pdf",
            title=original.stem,
            metadata={"input_format": "pdf", "source_inventory": "configured-pdf-originals"},
            prepared=prepared,
        )
    return SourceProjectReport(
        project=project_id,
        release_id=release_id,
        realization_id=realization_id,
        documents=len(acquired),
    )

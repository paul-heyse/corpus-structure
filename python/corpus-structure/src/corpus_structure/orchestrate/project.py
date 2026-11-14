"""Register immutable source originals without constructing an execution registry."""

from pathlib import Path

from pydantic import BaseModel
from sqlalchemy import Connection


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
) -> SourceProjectReport:
    """Register pack-declared PDF originals against explicit admitted interpretation.

    The pack supplies an input inventory only. It does not choose executable
    methods, defaults, runtime providers or stage order.
    """
    import yaml

    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.contracts import require_bound_operation
    from corpus_structure.semantic.operations import register_document
    from corpus_structure.semantic.releases import load_release

    if not domain or Path(domain).name != domain or domain in {".", ".."}:
        raise ProjectError("domain must name a declared pack")
    prepared = load_release(conn, release_id)
    require_bound_operation(prepared, "construct_project")
    pack = (domains or DOMAINS) / domain
    inventory = yaml.safe_load((pack / "methods.yaml").read_text())
    configurations = inventory.get("configs", {})
    originals = []
    for owner in ("ingest.pdf", "ingest.pdf_integrated"):
        for configuration in configurations.get(owner, {}).values():
            values = configuration.get("originals", ())
            if not isinstance(values, (list, tuple)) or any(
                not isinstance(value, str) or not value for value in values
            ):
                raise ProjectError("PDF inventory requires exact original paths")
            originals.extend(values)
    originals = tuple(dict.fromkeys(originals))
    if not originals:
        raise ProjectError("source pack declares no PDF originals")
    root = corpus.resolve()
    acquired = []
    for uri in originals:
        original = (root / uri).resolve()
        if not original.is_relative_to(root) or original.suffix.lower() != ".pdf":
            raise ProjectError("PDF original must remain within the selected corpus")
        raw = original.read_bytes()
        if not raw.startswith(b"%PDF-"):
            raise ProjectError("configured original is not a PDF: " + uri)
        acquired.append((uri, original, raw))
    from corpus_structure.semantic._operation_calls import initialize_source_project
    from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId

    project_id = name or domain
    initialize_source_project(
        conn,
        project_id=ProjectId(project_id),
        release_id=ReleaseId(release_id),
        realization_id=RealizationId(realization_id),
        projection_context=prepared,
    )
    for uri, original, raw in acquired:
        register_document(
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

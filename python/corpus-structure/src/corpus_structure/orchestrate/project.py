"""Register immutable source originals without constructing an execution registry."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
from sqlalchemy import Connection

from corpus_structure.semantic.data_operation_support import OriginalDocumentRef
from corpus_structure.semantic.refusals import SemanticRefusal


class ProjectError(SemanticRefusal):
    """A project or source pack cannot be registered as supplied."""


class SourceProjectReport(BaseModel):
    project: str
    release_id: str
    documents: int


class OriginalInventory(BaseModel):
    """A source pack's explicit local originals, independent of execution recipes."""

    model_config = ConfigDict(extra="forbid", strict=True)

    originals: list[Annotated[str, Field(min_length=1)]] = Field(min_length=1)


class OriginalDescriptor(BaseModel):
    """Exact immutable original metadata supplied for current registration."""

    model_config = ConfigDict(extra="forbid", strict=True)

    project_id: Annotated[str, Field(min_length=1)]
    key: Annotated[str, Field(pattern=r"^doc:[0-9a-f]{32}$")]
    source_uri: Annotated[str, Field(min_length=1)]
    content_hash: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    original_path: Annotated[str, Field(min_length=1)]
    mime: Literal["application/pdf"]
    title: str | None
    metadata: dict[str, JsonValue]

    def acquire_bytes(self) -> bytes:
        from hashlib import sha256

        from corpus_structure.core.evidence import document_key

        path = Path(self.original_path)
        if not path.is_absolute() or path.suffix.lower() != ".pdf":
            raise ProjectError("original descriptor requires an absolute PDF path")
        raw = path.read_bytes()
        if not raw.startswith(b"%PDF-") or sha256(raw).hexdigest() != self.content_hash:
            raise ProjectError("original descriptor bytes differ from the declared PDF hash")
        if document_key(self.project_id, self.source_uri, self.content_hash) != self.key:
            raise ProjectError("original descriptor document key differs from its source identity")
        return raw


class OriginalDescriptorInventory(BaseModel):
    """A finite descriptor batch with optional retained inventory observations."""

    model_config = ConfigDict(extra="ignore", strict=True)

    descriptors: list[OriginalDescriptor] = Field(min_length=1)
    documents: int = Field(ge=1)
    distinct_paths: int = Field(ge=1)

    @model_validator(mode="after")
    def require_exact_inventory(self):
        if self.documents != len(self.descriptors):
            raise ValueError("original descriptor count differs from declared inventory")
        if self.distinct_paths != len({item.original_path for item in self.descriptors}):
            raise ValueError("original descriptor path count differs from declared inventory")
        identities = {(item.project_id, item.key) for item in self.descriptors}
        if len(identities) != self.documents:
            raise ValueError(
                "original descriptors require distinct project and document identities"
            )
        return self


class OriginalDescriptorReport(BaseModel):
    projects: list[str]
    release_id: str
    documents: int


def init_described_projects(
    conn: Connection, *, inventory: OriginalDescriptorInventory, release_id: str
) -> OriginalDescriptorReport:
    """Register a preflighted batch atomically in the caller's transaction."""
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.identifiers import ProjectId, ReleaseId
    from corpus_structure.semantic.original_document_contracts import (
        require_source_operation_context,
    )
    from corpus_structure.semantic.original_documents import register_original_document
    from corpus_structure.semantic.releases import load_release

    # Validate the complete source batch before initializing any target project.
    for item in inventory.descriptors:
        item.acquire_bytes()

    prepared = load_release(conn, release_id)
    require_source_operation_context(prepared)
    projects = sorted({item.project_id for item in inventory.descriptors})
    storage = DataOperationStorage(conn)
    for project in projects:
        expected = {"project_id": ProjectId(project), "release_id": ReleaseId(release_id)}
        if storage.initialize_source_project(expected) != expected:
            raise ProjectError("initialized project differs from requested descriptor identity")
    for item in inventory.descriptors:
        # Registration independently rechecks bytes and exact returned metadata.
        register_original_document(
            conn,
            prepared=prepared,
            project_id=item.project_id,
            source_uri=item.source_uri,
            original_path=item.original_path,
            original=item.acquire_bytes(),
            mime=item.mime,
            title=item.title,
            metadata=item.metadata,
        )
    return OriginalDescriptorReport(
        projects=projects, release_id=release_id, documents=inventory.documents
    )


def init_bound_project(
    conn: Connection,
    *,
    domain: str,
    corpus: Path,
    release_id: str,
    name: str | None = None,
    domains: Path | None = None,
    originals: tuple[OriginalDocumentRef, ...] = (),
) -> SourceProjectReport:
    """Register pack-declared PDF originals against explicit admitted interpretation.

    The pack supplies an input inventory only. It does not choose executable
    methods, defaults, runtime providers or stage order.
    """
    import yaml

    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.original_document_contracts import (
        require_source_operation_context,
    )
    from corpus_structure.semantic.original_documents import register_original_document
    from corpus_structure.semantic.regeneration import DOMAINS
    from corpus_structure.semantic.releases import load_release

    if not domain or Path(domain).name != domain or domain in {".", ".."}:
        raise ProjectError("domain must name a declared pack")
    prepared = load_release(conn, release_id)
    require_source_operation_context(prepared)
    project_id = name or domain
    retained_bytes = {}
    if originals:
        from corpus_structure.semantic.original_documents import (
            acquire_original_document_selection,
            read_original_document_bytes,
        )

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
        inventory = OriginalInventory.model_validate(
            yaml.safe_load((pack / "originals.yaml").read_text())
        )
        paths = inventory.originals
        if len(set(paths)) != len(paths):
            raise ProjectError("PDF inventory requires distinct exact original paths")
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
    from corpus_structure.semantic.identifiers import ProjectId, ReleaseId

    result = DataOperationStorage(conn).initialize_source_project(
        {
            "project_id": ProjectId(project_id),
            "release_id": ReleaseId(release_id),
        }
    )
    if result != {
        "project_id": project_id,
        "release_id": release_id,
    }:
        raise ProjectError(
            "initialized project context differs from its exact requested identities"
        )
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
        documents=len(acquired),
    )

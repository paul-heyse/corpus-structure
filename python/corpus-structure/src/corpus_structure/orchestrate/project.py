"""Semantic source-project initialization and indexed original-byte acquisition."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Connection, text

from corpus_structure.orchestrate.registry import MethodRegistry


class ProjectError(ValueError):
    """A project or pack that cannot be registered as it stands."""


@dataclass(frozen=True)
class PackVersions:
    """The versions a pack upsert registered or found."""

    schema_version_id: int
    schema_version: str
    model_revision_id: int
    model_revision: str
    guideline_version_id: int | None
    policy_version_id: int
    created: tuple[str, ...] = ()


def source_documents(corpus: Path, profile: Any, profile_name: str):
    """Acquire indexed original bytes for semantic source registration."""
    index = profile.index
    if index is None:
        raise ProjectError(f"source profile {profile_name!r} names no corpus index")
    path = (corpus / index.file).resolve()
    if not path.exists():
        raise ProjectError(f"source profile {profile_name!r}: corpus index {path} is missing")
    with path.open(encoding="utf-8", newline="") as handle:
        for number, row in enumerate(csv.DictReader(handle, delimiter="\t"), 2):
            page = (row.get(index.page) or "").strip()
            if not page:
                raise ProjectError(f"{path.name}:{number}: no {index.page!r} value")
            uri = f"{profile.root.rstrip('/')}/{page}"
            original = (corpus / uri).resolve()
            if not original.is_relative_to(corpus.resolve()):
                raise ProjectError(f"{path.name}:{number}: source path leaves corpus")
            if not original.exists():
                raise ProjectError(f"{path.name}:{number}: {original} is missing")
            raw = original.read_bytes()
            metadata = {k: v for k, v in row.items() if k != index.page and k is not None}
            metadata["page"] = page
            yield {
                "page": page,
                "location": f"{path.name}:{number}",
                "source_uri": uri,
                "content_hash": hashlib.sha256(raw).hexdigest(),
                "original_path": str(original),
                "original": raw,
                "title": row.get("title") or None,
                "meta": metadata,
            }


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
) -> SourceProjectReport:
    """Register real indexed source documents against an explicitly admitted interpretation."""
    from corpus_structure.ingest.profile import SOURCES_DIR, load_profile
    from corpus_structure.orchestrate.phase0 import registry as registry_for
    from corpus_structure.schema.pack import DOMAINS
    from corpus_structure.semantic.operations import register_document
    from corpus_structure.semantic.releases import load_release

    try:
        prepared = load_release(conn, release_id)
    except KeyError as exc:
        raise ProjectError("semantic release is not admitted") from exc
    pack = (domains or DOMAINS) / domain
    registry = (registry or registry_for(pack)).bind_release(prepared)
    project_id = name or domain
    from sqlalchemy.exc import DBAPIError

    try:
        conn.execute(
            text("SELECT data.initialize_source_project(:p,:r,:z)"),
            {"p": project_id, "r": release_id, "z": realization_id},
        ).scalar_one()
    except DBAPIError as exc:
        if getattr(exc.orig, "sqlstate", None) in {"P0001", "P0004"}:
            raise ProjectError(str(exc.orig).split("\n")[0]) from exc
        raise
    seen = set()
    profiles = set()
    count = 0
    for method, config in registry.named():
        if registry.method(method).family.value != "ingest":
            continue
        for _, profile_name in registry.profiles(method, config):
            if profile_name in profiles:
                continue
            profiles.add(profile_name)
            profile = load_profile(profile_name, registry.sources or SOURCES_DIR, prepared=prepared)
            for source in source_documents(corpus, profile, profile_name):
                if source["page"] in seen:
                    raise ProjectError(f"page {source['page']!r} is registered twice")
                seen.add(source["page"])
                register_document(
                    conn,
                    project_id=project_id,
                    source_uri=source["source_uri"],
                    original_path=source["original_path"],
                    original=source["original"],
                    title=source["title"],
                    metadata=source["meta"],
                )
                count += 1
    if not profiles:
        raise ProjectError("method pack declares no source profiles")
    return SourceProjectReport(
        project=project_id, release_id=release_id, realization_id=realization_id, documents=count
    )

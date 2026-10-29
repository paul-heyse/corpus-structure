"""Project initialization and pack versions (orchestration §3.3; D8 §4; D1 §3.1, §10.1).

`init_project(conn, domain, corpus, …)`:
1. get-or-creates `meta.project` (the name defaults to the domain);
2. reads the source profiles the pack's configurations name (`SourceProfileRef`), through
   `load_profile`;
3. registers one document per row of each profile's corpus index through `get_or_create`: the
   source URI is the profile's `root` plus the row's page, the key uses the project name, `meta`
   takes the row's other columns, and two rows with one page are refused;
4. runs the pack-version upsert.
A rerun adds only new documents and versions; new bytes at a known path are a new document.

`ensure_pack_versions(conn, project_id, pack_root, created_by)` runs first in every `ci run` and
`ci ingest`: the schema version and its artifacts through `schema.registry.ensure`; the guideline
version (`guideline.md` by content hash, its label the first heading's `v<N>`, its parent the
domain's latest other version, its schema version the one just ensured); and the policy version
(`policies.yaml` as loaded, by content hash; an empty policy when the pack has none). The slices
are P0-O-2's. Configurations are not upserted here: they are resolved per run (§3.2).
"""

from __future__ import annotations

import csv
import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from corpus_structure.core.db import metadata, repo
from corpus_structure.core.evidence import document_key
from corpus_structure.orchestrate.registry import MethodRegistry, RegistryError
from corpus_structure.schema.pack import DOMAINS

T = metadata.tables


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


class ProjectReport(BaseModel):
    """`ci project init`'s result."""

    project_id: int
    name: str
    domain: str
    documents: int
    documents_added: int
    profiles: list[str]
    schema_version: str
    guideline_version_id: int | None
    policy_version_id: int
    versions_added: list[str]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _label(text: str) -> str:
    first = text.lstrip().splitlines()[0] if text.strip() else ""
    found = re.search(r"\bv(\d+(?:\.\d+)*)\b", first)
    return found.group(1) if found else "0"


def _version_row(
    conn: Connection, table: str, values: dict[str, Any], unique: Sequence[str]
) -> tuple[int, bool]:
    t = T[table]
    stmt = pg_insert(t).values(**values).on_conflict_do_nothing(index_elements=list(unique))
    row = conn.execute(stmt.returning(t.c.id)).first()
    if row is not None:
        return int(row[0]), True
    found = select(t.c.id).where(*(t.c[c] == values[c] for c in unique))
    return int(conn.execute(found).scalar_one()), False


def ensure_pack_versions(
    conn: Connection, project_id: int, pack_root: Path, created_by: str
) -> PackVersions:
    """The pack's schema, guideline and policy versions, registered or found (module doc)."""
    from corpus_structure.schema.registry import ensure

    ref = ensure(conn, project_id, [pack_root], created_by)
    created = ["schema_version"] if ref.created else []
    domain = pack_root.name
    guideline_id = None
    guideline = pack_root / "guideline.md"
    if guideline.exists():
        body = guideline.read_text(encoding="utf-8")
        versions = T["meta.guideline_version"]
        parent = conn.execute(
            select(versions.c.id)
            .where(
                versions.c.project_id == project_id,
                versions.c.domain == domain,
                versions.c.content_hash != sha256_text(body),
            )
            .order_by(versions.c.id.desc())
            .limit(1)
        ).scalar()
        guideline_id, new = _version_row(
            conn,
            "meta.guideline_version",
            {
                "project_id": project_id,
                "domain": domain,
                "label": _label(body),
                "content_hash": sha256_text(body),
                "body": body,
                "schema_version_id": ref.id,
                "parent_id": parent,
                "created_by": created_by,
            },
            ["project_id", "content_hash"],
        )
        created += ["guideline_version"] if new else []
    policies = pack_root / "policies.yaml"
    source = policies.read_text(encoding="utf-8") if policies.exists() else ""
    label = re.search(r"(?m)^version:\s*['\"]?([^'\"\s]+)", source)
    policy_id, new = _version_row(
        conn,
        "ops.policy_version",
        {
            "project_id": project_id,
            "label": label.group(1) if label else "0",
            "content_hash": sha256_text(source),
            "source": source,
            "created_by": created_by,
        },
        ["project_id", "content_hash"],
    )
    created += ["policy_version"] if new else []
    return PackVersions(
        ref.id,
        ref.content_hash,
        ref.model_revision_id,
        ref.model_revision,
        guideline_id,
        policy_id,
        tuple(created),
    )


@dataclass
class _Documents:
    total: int = 0
    added: int = 0
    pages: dict[str, str] = field(default_factory=dict)


def _register_documents(
    conn: Connection,
    project_id: int,
    project_name: str,
    corpus: Path,
    profile: Any,
    profile_name: str,
    found: _Documents,
) -> None:
    index = profile.index
    if index is None:
        raise ProjectError(f"source profile {profile_name!r} names no corpus index")
    path = (corpus / index.file).resolve()
    if not path.exists():
        raise ProjectError(f"source profile {profile_name!r}: corpus index {path} is missing")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    for number, row in enumerate(rows, 2):
        page = (row.get(index.page) or "").strip()
        if not page:
            raise ProjectError(f"{path.name}:{number}: no {index.page!r} value")
        source_uri = f"{profile.root.rstrip('/')}/{page}"
        if page in found.pages:
            raise ProjectError(
                f"page {page!r} is registered twice ({found.pages[page]} and {path.name}:{number})"
            )
        found.pages[page] = f"{path.name}:{number}"
        original = corpus / source_uri
        if not original.exists():
            raise ProjectError(f"{path.name}:{number}: {original} is missing")
        content_hash = hashlib.sha256(original.read_bytes()).hexdigest()
        meta = {k: v for k, v in row.items() if k != index.page and k is not None}
        meta["page"] = page  # the locators' page (D1 §3.4): the source URI less the profile root
        _, new = repo.get_or_create(
            conn,
            T["kb.document"],
            {
                "project_id": project_id,
                "key": document_key(project_name, source_uri, content_hash),
                "source_uri": source_uri,
                "content_hash": content_hash,
                "original_path": str(original.resolve()),
                "mime": "text/html",
                "title": row.get("title") or None,
                "meta": meta,
            },
            ["project_id", "source_uri", "content_hash"],
        )
        found.total += 1
        found.added += int(new)


def init_project(
    conn: Connection,
    *,
    domain: str,
    corpus: Path,
    registry: MethodRegistry,
    name: str | None = None,
    domains: Path = DOMAINS,
    created_by: str = "human:operator",
) -> ProjectReport:
    """`ci project init` (module doc)."""
    from corpus_structure.ingest.profile import SOURCES_DIR, load_profile

    pack_root = domains / domain
    if not pack_root.is_dir():
        raise ProjectError(f"no pack {domain!r} under {domains}")
    name = name or domain
    project_id, _ = repo.get_or_create(
        conn, T["meta.project"], {"name": name, "domain": domain}, ["name"]
    )
    stored_domain = conn.execute(
        select(T["meta.project"].c.domain).where(T["meta.project"].c.id == project_id)
    ).scalar_one()
    if stored_domain != domain:
        raise ProjectError(f"project {name!r} exists with domain {stored_domain!r}")
    profiles: list[str] = []
    try:
        for method, config in registry.named():
            profiles += [p for _, p in registry.profiles(method, config) if p not in profiles]
    except RegistryError as error:
        raise ProjectError(str(error)) from None
    found = _Documents()
    for profile_name in profiles:
        profile = load_profile(profile_name, registry.sources or SOURCES_DIR)
        _register_documents(conn, project_id, name, corpus, profile, profile_name, found)
    versions = ensure_pack_versions(conn, project_id, pack_root, created_by)
    return ProjectReport(
        project_id=project_id,
        name=name,
        domain=domain,
        documents=found.total,
        documents_added=found.added,
        profiles=profiles,
        schema_version=versions.schema_version,
        guideline_version_id=versions.guideline_version_id,
        policy_version_id=versions.policy_version_id,
        versions_added=list(versions.created),
    )

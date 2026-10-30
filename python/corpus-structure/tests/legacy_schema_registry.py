"""Historical installed-model database registration oracle, outside product execution."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from corpus_structure.schema.model import Model, read_log, revision
from corpus_structure.schema.registry import RegistrationError, payload_schema_versions


class ArtifactMismatch(RegistrationError):
    def __init__(self, compiler: str, compiler_version: str, kind: str, stored: str, now: str):
        self.compiler, self.kind = compiler, kind
        super().__init__(
            f"compiler {compiler} {compiler_version}, kind {kind}: the stored artifact's hash "
            f"{stored[:12]} differs from the output now, {now[:12]}; a compiler's output changed "
            "without a version bump"
        )


class ReferencedNameRemoved(RegistrationError):
    def __init__(self, compiler: str, element: str, table: str, referenced_by: str) -> None:
        self.compiler, self.element, self.table, self.referenced_by = (
            compiler,
            element,
            table,
            referenced_by,
        )
        super().__init__(
            f"compiler {compiler} omits {element} from meta.{table}, which {referenced_by} still "
            "references"
        )


class ModelRevisionMismatch(RegistrationError):
    pass


@dataclass(frozen=True)
class SchemaVersionRef:
    """A registered schema version: its id and hash, its model revision's id and hash, and
    whether this call inserted it."""

    id: int
    content_hash: str
    model_revision_id: int
    model_revision: str
    created: bool


CORE_RULES_SOURCE = "core/rules.yaml"
# the projection's tables and their keys beside schema_version_id
PROJECTION: Mapping[str, str] = {
    "schema_class": "name",
    "schema_slot": "name",
    "schema_enum": "name",
    "schema_rule": "rule_id",
    "statement_kind": "value",
    "claim_modality": "value",
}


def _tables() -> Any:
    from corpus_structure.core.db.legacy_metadata import metadata

    return metadata.tables


def _ensure_model_revision(conn: Any, model: Model) -> tuple[int, str]:
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert

    current = revision(model)
    log = read_log()
    entry = next((e for e in log if e["content_hash"] == current.content_hash), None)
    if entry is None:
        raise ModelRevisionMismatch(
            f"model revision {current.content_hash[:12]} is not in the "
            "revision log: run just model generate"
        )
    table = _tables()["meta.model_revision"]
    for entry in log:
        parent_id = None
        if entry.get("parent"):
            parent_id = conn.execute(
                select(table.c.id).where(table.c.content_hash == entry["parent"])
            ).scalar_one()
        conn.execute(
            insert(table)
            .values(
                label=entry["label"],
                content_hash=entry["content_hash"],
                compilers=entry["compilers"],
                key_scheme=entry["key_scheme"],
                parent_id=parent_id,
                change_record=entry.get("change_record"),
            )
            .on_conflict_do_nothing(index_elements=["content_hash"])
        )
        if entry["content_hash"] == current.content_hash:
            break
    found = conn.execute(select(table.c.id).where(table.c.content_hash == current.content_hash))
    return int(found.scalar_one()), current.content_hash


def _ensure_payload_schemas(conn: Any, model: Model, revision_id: int) -> dict[str, int]:
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert

    table = _tables()["meta.payload_schema"]
    out = {}
    for entry in payload_schema_versions(model):
        revision_hash = next(
            r["content_hash"]
            for r in read_log()
            if f"/{r['content_hash'][:12]}/" in entry.json_schema_id
        )
        owner_revision = conn.execute(
            select(_tables()["meta.model_revision"].c.id).where(
                _tables()["meta.model_revision"].c.content_hash == revision_hash
            )
        ).scalar_one()
        parent_id = None
        if entry.parent_version is not None:
            parent_id = conn.execute(
                select(table.c.id).where(
                    table.c["class"] == entry.class_, table.c.version == entry.parent_version
                )
            ).scalar()
        conn.execute(
            insert(table)
            .values(model_revision_id=owner_revision, parent_id=parent_id, **entry.row())
            .on_conflict_do_nothing(index_elements=["class", "version"])
        )
        stored = (
            conn.execute(
                select(table).where(
                    table.c["class"] == entry.class_, table.c.version == entry.version
                )
            )
            .mappings()
            .one()
        )
        expected = {"model_revision_id": owner_revision, "parent_id": parent_id, **entry.row()}
        differing = [name for name, value in expected.items() if stored[name] != value]
        if differing:
            raise RegistrationError(
                f"{entry.class_} version {entry.version}: registered payload differs in "
                + ", ".join(differing)
            )
        out[entry.kind] = int(stored["id"])
    return out


def sources(compiled: Any) -> dict[str, str]:
    """The stored source of a compiled version: each pack file's text under `<pack>/<path>`, and
    the core rules under `core/rules.yaml`."""
    from corpus_structure.schema.pack import CORE_RULES

    out = {f"{p.name}/{rel}": text for p in compiled.packs for rel, text in p.sources.items()}
    out[CORE_RULES_SOURCE] = CORE_RULES.read_text(encoding="utf-8")
    return out


def _project(conn: Any, version_id: int, body: Mapping[str, Any], compiler: str) -> None:
    """Upsert the version's projection from a `schema_tables` body (module doc)."""
    from sqlalchemy import delete
    from sqlalchemy.dialects.postgresql import insert
    from sqlalchemy.exc import IntegrityError

    tables = _tables()
    for name, key in PROJECTION.items():
        table = tables[f"meta.{name}"]
        rows = [{**row, "schema_version_id": version_id} for row in body.get(name, [])]
        keep = [row[key] for row in rows]
        try:
            with conn.begin_nested():
                conn.execute(
                    delete(table).where(
                        table.c.schema_version_id == version_id, table.c[key].not_in(keep)
                    )
                )
        except IntegrityError as error:
            detail = str(getattr(error.orig, "diag", None) and error.orig.diag.message_detail)
            element = re.search(r"\)=\([^,]*, ([^)]*)\)", detail)
            referencing = re.search(r'referenced from table "([^"]+)"', detail)
            raise ReferencedNameRemoved(
                compiler,
                element.group(1) if element else "a name",
                name,
                referencing.group(1) if referencing else "another table",
            ) from None
        if not rows:
            continue
        stmt = insert(table).values(rows)
        updates = {c: stmt.excluded[c] for c in rows[0] if c not in ("schema_version_id", key)}
        conn.execute(
            stmt.on_conflict_do_update(index_elements=["schema_version_id", key], set_=updates)
            if updates
            else stmt.on_conflict_do_nothing()
        )


def ensure(conn: Any, project_id: int, roots: Sequence[Any], created_by: str) -> SchemaVersionRef:
    """Register the packs at `roots` as a schema version of the project (module doc)."""
    import legacy_db_repo as repo
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert

    from corpus_structure.schema.compile import compile_paths
    from corpus_structure.schema.model import load

    model = load()
    revision_id, revision_hash = _ensure_model_revision(conn, model)
    compiled = compile_paths(list(roots), model_revision=revision_hash)
    payload_ids = _ensure_payload_schemas(conn, model, revision_id)
    versions = _tables()["meta.schema_version"]
    domain = "+".join(p.name for p in compiled.packs)
    label = "+".join(str(p.schema.get("version", "")) for p in compiled.packs)
    parent = conn.execute(
        select(versions.c.id)
        .where(
            versions.c.project_id == project_id,
            versions.c.domain == domain,
            versions.c.content_hash != compiled.schema_version,
        )
        .order_by(versions.c.id.desc())
        .limit(1)
    ).scalar()
    inserted = conn.execute(
        insert(versions)
        .values(
            project_id=project_id,
            domain=domain,
            label=label,
            content_hash=compiled.schema_version,
            model_revision_id=revision_id,
            parent_id=parent,
            source=sources(compiled),
            created_by=created_by,
        )
        .on_conflict_do_nothing(index_elements=["project_id", "content_hash"])
        .returning(versions.c.id)
    ).first()
    version_id = (
        int(inserted[0])
        if inserted is not None
        else int(
            conn.execute(
                select(versions.c.id).where(
                    versions.c.project_id == project_id,
                    versions.c.content_hash == compiled.schema_version,
                )
            ).scalar_one()
        )
    )
    _ensure_artifacts(conn, version_id, compiled, payload_ids["compiled_artifact"], repo)
    return SchemaVersionRef(
        version_id, compiled.schema_version, revision_id, revision_hash, inserted is not None
    )


def _ensure_artifacts(
    conn: Any, version_id: int, compiled: Any, payload_id: int, repo: Any
) -> None:
    from sqlalchemy import select

    table = _tables()["meta.compiled_artifact"]
    for a in compiled.artifacts:
        new = repo.insert_artifact(
            conn,
            {
                "schema_version_id": version_id,
                "compiler": a.compiler,
                "compiler_version": a.compiler_version,
                "kind": a.kind,
                "hash": a.hash,
                "body": a.body,
                "payload_schema_id": payload_id,
            },
        )
        if new is not None:
            if a.compiler == "schema_tables":
                _project(conn, version_id, a.body, f"{a.compiler} {a.compiler_version}")
            continue
        stored = conn.execute(
            select(table.c.hash).where(
                table.c.schema_version_id == version_id,
                table.c.compiler == a.compiler,
                table.c.compiler_version == a.compiler_version,
                table.c.kind == a.kind,
            )
        ).scalar_one()
        if stored != a.hash:
            raise ArtifactMismatch(a.compiler, a.compiler_version, a.kind, stored, a.hash)


def compiled_for(conn: Any, schema_version_id: int) -> Any:
    """The version's `CompiledSchema`, rebuilt from its stored source (module doc)."""
    import tempfile
    from pathlib import Path

    from sqlalchemy import select

    from corpus_structure.core._model.revision import CONTENT_HASH
    from corpus_structure.schema.compile import compile_schema
    from corpus_structure.schema.pack import load_pack

    tables = _tables()
    versions, revisions = tables["meta.schema_version"], tables["meta.model_revision"]
    row = conn.execute(
        select(versions.c.source, versions.c.content_hash, revisions.c.content_hash)
        .join(revisions, revisions.c.id == versions.c.model_revision_id)
        .where(versions.c.id == schema_version_id)
    ).one()
    source, version_hash, model_hash = row
    if model_hash != CONTENT_HASH:
        raise ModelRevisionMismatch(
            f"schema version {schema_version_id} was compiled under model revision "
            f"{model_hash[:12]}, the installed one is {CONTENT_HASH[:12]}: a code release changed "
            "the model"
        )
    with tempfile.TemporaryDirectory(prefix="cs_source_") as tmp:
        root = Path(tmp)
        for rel, text in source.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        names = sorted({rel.split("/", 1)[0] for rel in source if rel != CORE_RULES_SOURCE})
        packs = [load_pack(root / name) for name in names]
        compiled = compile_schema(
            packs, core_rules=root / CORE_RULES_SOURCE, model_revision=model_hash
        )
    if compiled.schema_version != version_hash:
        raise RegistrationError(
            f"schema version {schema_version_id}: its stored source hashes to "
            f"{compiled.schema_version[:12]}, not {version_hash[:12]}"
        )
    artifacts = tables["meta.compiled_artifact"]
    stored = {
        (r.compiler, r.compiler_version, r.kind): r.hash
        for r in conn.execute(
            select(
                artifacts.c.compiler,
                artifacts.c.compiler_version,
                artifacts.c.kind,
                artifacts.c.hash,
            ).where(artifacts.c.schema_version_id == schema_version_id)
        )
    }
    for a in compiled.artifacts:
        key = (a.compiler, a.compiler_version, a.kind)
        if key not in stored:
            raise RegistrationError(
                f"schema version {schema_version_id} has no {a.compiler} "
                f"{a.compiler_version} {a.kind} artifact: run ensure"
            )
        if stored[key] != a.hash:
            raise ArtifactMismatch(a.compiler, a.compiler_version, a.kind, stored[key], a.hash)
    return compiled

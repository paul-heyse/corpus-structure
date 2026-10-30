"""Exact immutable release archives and optimistic project activation.

The caller owns the SQLAlchemy transaction. Preparation happens before persistence;
only an explicit archive load recompiles the archived, entirely local inputs.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .authored_sql import AuthoredSQL

from sqlalchemy import Connection, select

from .determinants import BYTE_LIBRARIES as _LIBRARIES
from .determinants import BYTE_LIBRARIES_V11, determinant_version
from .identity import canonical_bytes
from .prepare import prepare_release
from .types import (
    PreparationProfile,
    PreparedRelease,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    VocabularyMember,
    VocabularySnapshot,
)


class ReleaseConflict(ValueError):
    """An identity already denotes different bytes or an archive is inconsistent."""


class ActivationConflict(ValueError):
    """The project's active release/generation differs from the expected token."""


@dataclass(frozen=True)
class ActivationToken:
    release_id: str | None
    generation: int


def _table(name: str):
    # This module never imports the installed legacy schema or its model defaults.
    from .metadata import table

    return table(name)


def _digest(content: bytes) -> str:
    return sha256(content).hexdigest()


def _products(prepared: PreparedRelease) -> dict[str, Any]:
    products = {
        "release_id": prepared.release_id,
        "definitions": [asdict(x) for x in prepared.definitions],
        "vocabularies": [asdict(x) for x in prepared.vocabularies],
        "registry_rows": [
            {"kind": x.kind, "name": x.name, "body_hex": x.body.hex()}
            for x in prepared.registry_rows
        ],
        "queries": [asdict(x) for x in prepared.queries],
        "artifacts": [{"kind": x.kind, "digest": x.digest} for x in prepared.artifacts],
        "required_capabilities": prepared.required_capabilities,
        "diagnostics": [
            {key: value for key, value in asdict(item).items() if value is not None}
            for item in prepared.diagnostics
        ],
    }
    if prepared.execution_model_id is not None:
        products["execution_model_id"] = prepared.execution_model_id
    return products


def _archive_bytes(
    bundle: SourceBundle, dependencies: ResolvedDependencies, prepared: PreparedRelease
) -> bytes:
    return canonical_bytes(
        {
            "format": (
                "semantic-release-archive-3"
                if json.loads(prepared.manifest)["profile"]["compiler_version"] == "12"
                else "semantic-release-archive-2"
                if prepared.execution_model_id is not None
                else "semantic-release-archive-1"
            ),
            "root": bundle.root,
            "sources": [s.name for s in bundle.sources],
            "dependencies": [s.name for s in dependencies.artifacts],
            "products": _products(prepared),
        }
    )


def _validate_manifest(
    bundle: SourceBundle,
    dependencies: ResolvedDependencies,
    profile: PreparationProfile,
    prepared: PreparedRelease,
) -> None:
    manifest: dict[str, Any] = {
        "root": bundle.root,
        "profile": asdict(profile),
        "libraries": {
            name: determinant_version(name)
            for name in (_LIBRARIES if profile.compiler_version == "12" else BYTE_LIBRARIES_V11)
        },
        "sources": sorted((s.name, s.digest) for s in bundle.sources),
        "dependencies": sorted((s.name, s.digest) for s in dependencies.artifacts),
        "ontology_sources": sorted(dependencies.ontology_sources),
        "vocabularies": [asdict(v) for v in prepared.vocabularies],
    }
    if profile.version == "semantic-2":
        from .composed import execution_model_from_dependencies

        try:
            execution = execution_model_from_dependencies(dependencies)
        except Exception as exc:
            raise ReleaseConflict(f"cannot reconstruct execution inputs: {exc}") from exc
        if prepared.execution_model_id != execution.model_id:
            raise ReleaseConflict("prepared execution model differs from exact inputs")
        manifest["execution_model_id"] = execution.model_id
    elif prepared.execution_model_id is not None:
        raise ReleaseConflict("execution model requires the composed semantic-2 profile")
    expected = canonical_bytes(manifest)
    if prepared.manifest != expected or prepared.release_id != "release:" + _digest(expected):
        raise ReleaseConflict(
            "prepared release does not match exact inputs, profile or compiler versions"
        )
    for values, identity in (
        (bundle.sources, "source"),
        (dependencies.artifacts, "dependency"),
        (prepared.artifacts, "artifact"),
    ):
        names = [getattr(v, "name", getattr(v, "kind", None)) for v in values]
        if len(names) != len(set(names)):
            raise ReleaseConflict(f"duplicate {identity} names")


def _projection_rows(prepared: PreparedRelease) -> dict[str, list[dict[str, Any]]]:
    from .publication import native_constraints

    constraints = native_constraints(prepared)
    rid = prepared.release_id
    rows: dict[str, list[dict[str, Any]]] = {
        name: []
        for name in (
            "class_definition",
            "property_definition",
            "class_hierarchy",
            "property_applicability",
            "identity_slot",
            "vocabulary_member",
            "registry_row",
            "conditional_rule",
            "conditional_atom",
            "metric_definition",
        )
    }
    properties: dict[str, str] = {}
    class_ids = {cls.name: cls.iri for cls in prepared.definitions}
    for cls in prepared.definitions:
        rows["class_definition"].append(
            {
                "release_id": rid,
                "class_id": cls.iri,
                "name": cls.name,
                "iri": cls.iri,
                "abstract": cls.abstract,
            }
        )
        rows["class_hierarchy"].extend(
            {"release_id": rid, "class_id": cls.iri, "ancestor_id": class_ids[a]}
            for a in cls.ancestors
        )
        for prop in cls.properties:
            properties.setdefault(prop.iri, prop.name)
            rows["property_applicability"].append(
                {
                    "release_id": rid,
                    "class_id": cls.iri,
                    "property_id": prop.iri,
                    "range_name": prop.range,
                    "required": prop.required,
                    "multivalued": prop.multivalued,
                    "minimum_cardinality": prop.minimum_cardinality,
                    "maximum_cardinality": prop.maximum_cardinality,
                    "constraint_scope": prop.constraint_scope,
                    "constraints": constraints[cls.iri, prop.iri],
                }
            )
        for group_id, group in enumerate(cls.identity_groups):
            rows["identity_slot"].extend(
                {
                    "release_id": rid,
                    "class_id": cls.iri,
                    "group_id": str(group_id),
                    "position": position,
                    "property_id": next(p.iri for p in cls.properties if p.name == name),
                }
                for position, name in enumerate(group)
            )
    rows["property_definition"] = [
        {"release_id": rid, "property_id": iri, "name": name, "iri": iri, "value_kind": None}
        for iri, name in sorted(properties.items())
    ]
    rows["vocabulary_member"] = [
        {
            "release_id": rid,
            "vocabulary_id": vocab.enum,
            "value": member.value,
            "meaning": member.meaning,
            "label": member.label,
        }
        for vocab in prepared.vocabularies
        for member in vocab.members
    ]
    rows["registry_row"] = [
        {"release_id": rid, "kind": row.kind, "name": row.name, "body": row.body}
        for row in prepared.registry_rows
    ]
    for artifact in prepared.artifacts:
        if artifact.kind != "conditional_rules_native.json":
            continue
        for rule in json.loads(artifact.content):
            rows["conditional_rule"].append(
                {
                    "release_id": rid,
                    "rule_id": rule["rule_id"],
                    "class_id": rule["class_id"],
                    "scope": rule["scope"],
                }
            )
            for branch, atoms in rule["branches"].items():
                rows["conditional_atom"].extend(
                    {
                        "release_id": rid,
                        "rule_id": rule["rule_id"],
                        "branch": branch,
                        "position": position,
                        "property_name": atom["property"],
                        "presence": atom["presence"],
                        "choices": atom["choices"],
                    }
                    for position, atom in enumerate(atoms)
                )
    rows["metric_definition"] = [
        {
            "release_id": rid,
            "metric_id": row.name,
            **{key: value for key, value in json.loads(row.body).items() if key != "id"},
        }
        for row in prepared.registry_rows
        if row.kind == "metric_definition"
    ]
    return rows


def _row_bytes(row: dict[str, Any]) -> bytes:
    return canonical_bytes(
        {
            key: {"bytes_hex": bytes(value).hex()}
            if isinstance(value, (bytes, memoryview))
            else value
            for key, value in row.items()
        }
    )


def _compare_rows(
    conn: Connection, name: str, release_id: str, expected: list[dict[str, Any]]
) -> None:
    table = _table("sem." + name)
    # Compare the entire relation for this release, including unexpected rows.
    columns = list(expected[0]) if expected else [c.name for c in table.columns]
    actual = [
        {column: row[column] for column in columns}
        for row in conn.execute(
            select(*(table.c[c] for c in columns)).where(table.c.release_id == release_id)
        ).mappings()
    ]
    if sorted(map(_row_bytes, actual)) != sorted(map(_row_bytes, expected)):
        raise ReleaseConflict(f"archived {name} bytes differ for {release_id}")


def persist_release(
    conn: Connection,
    bundle: SourceBundle,
    dependencies: ResolvedDependencies,
    profile: PreparationProfile,
    prepared: PreparedRelease,
    *,
    parent_release_id: str | None = None,
) -> str:
    """Atomically archive a previously prepared release; identical replay is idempotent.

    This trusts the compiler's prepared product, checks its complete input manifest,
    and never recompiles while writing projection rows. The caller commits or rolls back.
    """
    _validate_manifest(bundle, dependencies, profile, prepared)
    if profile.compiler_version == "12":
        derived = prepare_release(bundle, dependencies, profile)
        if _archive_bytes(bundle, dependencies, derived) != _archive_bytes(
            bundle, dependencies, prepared
        ):
            raise ReleaseConflict("prepared products differ from exact-source verification")

    if prepared.execution_model_id is not None:
        from .execution_admission import require_archive_fence

        require_archive_fence(conn)
    archive = _archive_bytes(bundle, dependencies, prepared)
    release_row = {
        "release_id": prepared.release_id,
        "parent_release_id": parent_release_id,
        "content_digest": _digest(archive),
        "profile": profile.version,
        "prepared_bytes": archive,
        "manifest_bytes": prepared.manifest,
    }
    inputs = [
        {
            "release_id": prepared.release_id,
            "input_kind": kind,
            "input_name": item.name,
            "content": item.content,
            "content_digest": item.digest,
        }
        for kind, items in (("source", bundle.sources), ("dependency", dependencies.artifacts))
        for item in items
    ]
    for kind, content in (
        ("profile", canonical_bytes(asdict(profile))),
        ("vocabulary", canonical_bytes([asdict(v) for v in dependencies.vocabularies])),
    ):
        inputs.append(
            {
                "release_id": prepared.release_id,
                "input_kind": kind,
                "input_name": kind,
                "content": content,
                "content_digest": _digest(content),
            }
        )
    artifacts = [
        {
            "release_id": prepared.release_id,
            "artifact_name": item.kind,
            "media_type": "application/octet-stream",
            "content": item.content,
            "content_digest": item.digest,
        }
        for item in prepared.artifacts
    ]
    ontology_sources = canonical_bytes(list(dependencies.ontology_sources))
    inputs.append(
        {
            "release_id": prepared.release_id,
            "input_kind": "ontology_sources",
            "input_name": "ontology_sources",
            "content": ontology_sources,
            "content_digest": _digest(ontology_sources),
        }
    )
    projections = _projection_rows(prepared)

    def transport(row: dict[str, Any]) -> dict[str, Any]:
        return {
            key: "\\x" + bytes(value).hex() if isinstance(value, (bytes, memoryview)) else value
            for key, value in row.items()
        }

    from sqlalchemy import text

    payload = {
        "release": [transport(release_row)],
        "input": [transport(row) for row in inputs],
        "artifact": [transport(row) for row in artifacts],
        **{name: [transport(row) for row in rows] for name, rows in projections.items()},
    }
    from sqlalchemy.exc import DBAPIError

    try:
        with conn.begin_nested():
            archived = conn.execute(
                text("SELECT sem.publish_release_archive(CAST(:payload AS jsonb))"),
                {"payload": json.dumps(payload)},
            ).scalar_one()
    except DBAPIError as error:
        if getattr(error.orig, "sqlstate", None) in {"23505", "23514"}:
            raise ReleaseConflict(str(error.orig).splitlines()[0]) from error
        raise
    return str(archived)


def open_release(conn: Connection, release_id: str) -> PreparedRelease:
    """Open immutable archived products for reading; this never establishes admission."""
    from .archive_reader import open_archived_release

    return open_archived_release(conn, release_id)


def verify_release(conn: Connection, release_id: str) -> PreparedRelease:
    """Fully rederive at explicit verification/admission boundaries."""
    return load_release(conn, release_id)


def load_release(conn: Connection, release_id: str) -> PreparedRelease:
    """Reprepare once, offline, and compare every archived product and exact byte string."""
    table = _table("sem.release")
    row = (
        conn.execute(select(table).where(table.c.release_id == release_id)).mappings().one_or_none()
    )
    if row is None:
        raise KeyError(release_id)
    try:
        archive_bytes = bytes(row["prepared_bytes"])
        if _digest(archive_bytes) != row["content_digest"]:
            raise ReleaseConflict("archive digest differs")
        archive = json.loads(archive_bytes)
        if archive["format"] not in {
            "semantic-release-archive-1",
            "semantic-release-archive-2",
            "semantic-release-archive-3",
        }:
            raise ReleaseConflict("unsupported archive format")
        inputs = _table("sem.input")
        source: dict[tuple[str, str], bytes] = {}
        for item in conn.execute(
            select(inputs).where(inputs.c.release_id == release_id)
        ).mappings():
            content = bytes(item["content"])
            if _digest(content) != item["content_digest"]:
                raise ReleaseConflict("input digest differs")
            source[item["input_kind"], item["input_name"]] = content
        bundle = SourceBundle(
            archive["root"],
            tuple(SourceArtifact(name, source["source", name]) for name in archive["sources"]),
        )
        snapshots = tuple(
            VocabularySnapshot(
                enum=v["enum"],
                members=tuple(VocabularyMember(**m) for m in v["members"]),
                dependency=v["dependency"],
                definition_digest=v["definition_digest"],
                dependency_digest=v["dependency_digest"],
                unchecked=tuple(v["unchecked"]),
            )
            for v in json.loads(source["vocabulary", "vocabulary"])
        )
        dependencies = ResolvedDependencies(
            tuple(
                SourceArtifact(name, source["dependency", name]) for name in archive["dependencies"]
            ),
            snapshots,
            tuple(json.loads(source["ontology_sources", "ontology_sources"])),
        )
        profile = PreparationProfile(**json.loads(source["profile", "profile"]))
        if len(source) != len(bundle.sources) + len(dependencies.artifacts) + 3:
            raise ReleaseConflict("unexpected archived inputs")
        # Detect version changes before attempting to interpret with another compiler.
        manifest = json.loads(bytes(row["manifest_bytes"]))
        if manifest["libraries"] != {name: determinant_version(name) for name in _LIBRARIES}:
            raise ReleaseConflict("archived compiler library versions differ")
        prepared = prepare_release(bundle, dependencies, profile)
        _validate_manifest(bundle, dependencies, profile, prepared)
        if (
            prepared.release_id != release_id
            or prepared.manifest != bytes(row["manifest_bytes"])
            or _archive_bytes(bundle, dependencies, prepared) != archive_bytes
            or row["profile"] != profile.version
        ):
            raise ReleaseConflict("offline preparation differs from archived products")
        artifacts = [
            {
                "release_id": release_id,
                "artifact_name": item.kind,
                "media_type": "application/octet-stream",
                "content": item.content,
                "content_digest": item.digest,
            }
            for item in prepared.artifacts
        ]
        _compare_rows(conn, "artifact", release_id, artifacts)
        for name, expected in _projection_rows(prepared).items():
            _compare_rows(conn, name, release_id, expected)
        return prepared
    except ReleaseConflict:
        raise
    except Exception as exc:
        raise ReleaseConflict(f"cannot reconstruct exact release {release_id}: {exc}") from exc


def activation_token(conn: Connection, project_id: str) -> ActivationToken:
    project = _table("data.project")
    row = conn.execute(
        select(project.c.active_release_id, project.c.generation).where(
            project.c.project_id == project_id
        )
    ).one_or_none()
    if row is None:
        raise KeyError(project_id)
    return ActivationToken(row.active_release_id, row.generation)


def activate_release(
    conn: Connection,
    project_id: str,
    release_id: str,
    *,
    expected_parent: str | None,
    expected_generation: int,
    sql_reader: Connection | None = None,
    sql_admissions: Mapping[str, AuthoredSQL] | None = None,
) -> ActivationToken:
    """Admit the exact archived release, then CAS the pointer and generation together.

    Existing realizations retain their release FK; activation never updates them.
    A stale token fails even after a pointer changes away and returns (ABA).
    """
    from .authored_sql import admit_archived_sql
    from .publication import admit_release

    prepared = load_release(conn, release_id)
    with conn.begin_nested():
        admit_archived_sql(conn, release_id, reader_conn=sql_reader, analyzed=sql_admissions)
        admit_release(prepared, connection=conn)
        from sqlalchemy import text
        from sqlalchemy.exc import DBAPIError

        try:
            generation = conn.execute(
                text("SELECT sem.activate_release(:project,:release,:parent,:generation)"),
                {
                    "project": project_id,
                    "release": release_id,
                    "parent": expected_parent,
                    "generation": expected_generation,
                },
            ).scalar_one()
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) == "40001":
                raise ActivationConflict(
                    f"stale activation token for project {project_id}"
                ) from exc
            raise
        return ActivationToken(release_id, generation)

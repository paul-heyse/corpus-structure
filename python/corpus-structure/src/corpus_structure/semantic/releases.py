"""Exact immutable release archives and optimistic project activation.

The caller owns the SQLAlchemy transaction. Preparation happens before persistence;
only an explicit archive load recompiles the archived, entirely local inputs.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Annotated, Any

if TYPE_CHECKING:
    from .authored_sql import AuthoredSQL

import yaml
from cattrs.errors import BaseValidationError
from pydantic import Field, TypeAdapter
from sqlalchemy import BigInteger, Connection, Text, bindparam, func, select

from .determinants import release_library_versions
from .identifiers import ProjectId, ReleaseId
from .identity import canonical_bytes
from .operation_value_types import OperationResult, native_result_scope
from .types import (
    SEMANTIC_COMPILER_VERSION,
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


class ArchiveDecodeError(ReleaseConflict):
    """Typed archive shape failure retaining wire locations and its original cause."""

    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        super().__init__("; ".join(f"{d.location}: {d.message}" for d in diagnostics))


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
    from .archive_wire import encode_products

    return encode_products(prepared)


def _archive_bytes(
    bundle: SourceBundle, dependencies: ResolvedDependencies, prepared: PreparedRelease
) -> bytes:
    return canonical_bytes(
        {
            "format": "semantic-release-archive-3",
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
    try:
        libraries = release_library_versions(dependencies)
    except ValueError as error:
        raise ReleaseConflict(str(error)) from error
    manifest: dict[str, Any] = {
        "root": bundle.root,
        "profile": asdict(profile),
        "libraries": libraries,
        "sources": sorted((s.name, s.digest) for s in bundle.sources),
        "dependencies": sorted((s.name, s.digest) for s in dependencies.artifacts),
        "ontology_sources": sorted(dependencies.ontology_sources),
        "vocabularies": [asdict(v) for v in prepared.vocabularies],
    }
    target = any(a.name.startswith("data-operations/") for a in dependencies.artifacts)
    if target:
        from .composed import data_operations_from_dependencies

        model = data_operations_from_dependencies(
            bundle, dependencies, prepared.definitions, prepared.vocabularies
        )
        if model is None:
            raise ReleaseConflict("target release lacks its effective model")
        manifest["data_operation_model"] = _digest(model.content)
        if model.source_interfaces is not None:
            manifest["data_operation_source_interfaces"] = _digest(model.source_interfaces)
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
    from .property_constraints import native_constraints
    from .record_contracts import record_product_classes

    constraints = native_constraints(prepared)
    products = record_product_classes(prepared.definitions)
    rid = prepared.release_id
    from .archive_transport import archive_tables

    rows: dict[str, list[dict[str, Any]]] = {
        relation.name: []
        for relation in archive_tables()
        if relation.info["archive_role"] == "projection"
    }
    properties: dict[str, str] = {}
    class_ids = {cls.name: cls.iri for cls in prepared.definitions}
    product_iris = {class_ids[name] for name in products}
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
            if cls.name in products:
                continue
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
        for group_id, group in enumerate(cls.identity_groups if cls.name not in products else ()):
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
            if rule["class_id"] in product_iris:
                continue
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
    # The index shares contextual role derivation with public Core property queries.
    rows["operation_property_role"] = [
        {"release_id": rid, "class_id": cls, "property_id": prop, "role": role}
        for (cls, prop), roles in sorted(prepared.index.property_roles.items())
        if cls not in product_iris
        for role in sorted(roles)
    ]
    for artifact in prepared.artifacts:
        if artifact.kind == "operation/scientific-policy.json":
            rows["scientific_decision_rule"] = [
                {"release_id": rid, **rule}
                for rule in json.loads(artifact.content)["decision_rules"]
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
    # Pure schema artifacts may be archived without granting execution authority.
    # Current executable releases additionally require the trusted native archive fence.
    if profile.compiler_version != SEMANTIC_COMPILER_VERSION:
        raise ReleaseConflict(f"unsupported archive compiler {profile.compiler_version}")
    from .prepare import prepare_release

    derived = prepare_release(bundle, dependencies, profile)
    if _archive_bytes(bundle, dependencies, derived) != _archive_bytes(
        bundle, dependencies, prepared
    ):
        raise ReleaseConflict("prepared products differ from exact-source verification")

    if any(a.kind == "data_operations.json" for a in prepared.artifacts):
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

    from sqlalchemy.exc import DBAPIError

    from .archive_native import prepare_release_archive, publish_release_archive
    from .archive_transport import (
        archive_batches,
        archive_tables,
        archive_write_profile,
        scratch_name,
    )
    from .arrow_transfer import copy_arrow_stream

    relations = {"release": [release_row], "input": inputs, "artifact": artifacts, **projections}
    try:
        with conn.begin_nested():
            release_id = ReleaseId(prepared.release_id)
            prepare_release_archive(conn, release_id)
            for relation in archive_tables():
                write = archive_write_profile(relation, prepared.release_id)
                copy_arrow_stream(
                    conn,
                    write,
                    target=("pg_temp", scratch_name(relation)),
                    batches=archive_batches(relation, write, relations[relation.name]),
                )
            archived = publish_release_archive(conn, release_id)
    except DBAPIError as error:
        if getattr(error.orig, "sqlstate", None) in {"23505", "23514"}:
            raise ReleaseConflict(str(error.orig).splitlines()[0]) from error
        raise
    return archived


def open_release(conn: Connection, release_id: str) -> PreparedRelease:
    """Open immutable archived products for reading; this never establishes admission."""
    from .archive_reader import open_archived_release

    return open_archived_release(conn, release_id)


def verify_release(conn: Connection, release_id: str) -> PreparedRelease:
    """Fully rederive at explicit verification/admission boundaries."""
    return load_release(conn, release_id)


def load_release(conn: Connection, release_id: str) -> PreparedRelease:
    return load_release_inputs(conn, release_id)[3]


def load_release_inputs(
    conn: Connection, release_id: str
) -> tuple[SourceBundle, ResolvedDependencies, PreparationProfile, PreparedRelease]:
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
        if archive["format"] != "semantic-release-archive-3":
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
        if profile.compiler_version != SEMANTIC_COMPILER_VERSION:
            raise ReleaseConflict(
                f"unsupported archive compiler {profile.compiler_version}; "
                f"current compiler is {SEMANTIC_COMPILER_VERSION}"
            )
        if len(source) != len(bundle.sources) + len(dependencies.artifacts) + 3:
            raise ReleaseConflict("unexpected archived inputs")
        # Detect version changes before attempting to interpret with another compiler.
        manifest = json.loads(bytes(row["manifest_bytes"]))
        if manifest["libraries"] != release_library_versions(dependencies):
            raise ReleaseConflict("archived compiler library versions differ")
        from .prepare import prepare_release

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
        return bundle, dependencies, profile, prepared
    except ReleaseConflict:
        raise
    except (
        ValueError,
        KeyError,
        TypeError,
        IndexError,
        BaseValidationError,
        yaml.YAMLError,
    ) as exc:
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


class _ActivationRequest(OperationResult):
    project_id: ProjectId
    release_id: ReleaseId
    expected_parent: ReleaseId | None
    expected_generation: Annotated[int, Field(ge=-(2**63), le=2**63 - 1)]


_activate_release = select(
    func.sem.activate_release(
        bindparam("project_id", type_=Text()),
        bindparam("release_id", type_=Text()),
        bindparam("expected_parent", type_=Text()),
        bindparam("expected_generation", type_=BigInteger()),
        type_=BigInteger(),
    )
)
_generation = TypeAdapter(int)


def activate_release(
    conn: Connection,
    project_id: str,
    release_id: str,
    *,
    expected_parent: str | None,
    expected_generation: int,
    sql_reader: Connection | None = None,
    verify_sql_reader: Callable[[Connection], object] | None = None,
    sql_admissions: Mapping[str, AuthoredSQL] | None = None,
) -> ActivationToken:
    """Admit the exact archived release, then CAS the pointer and generation together.

    Existing results retain their original producer attribution.
    A stale token fails even after a pointer changes away and returns (ABA).
    """
    from .authored_sql import admit_archived_sql
    from .data_operation_admission import admit_data_operation_release
    from .migrations import migration_fence

    migration_fence(conn)
    prepared = load_release(conn, release_id)
    with conn.begin_nested():
        admit_archived_sql(
            conn,
            release_id,
            reader_conn=sql_reader,
            verify_reader=verify_sql_reader,
            analyzed=sql_admissions,
        )
        admit_data_operation_release(conn, prepared)
        from sqlalchemy.exc import DBAPIError

        try:
            request = _ActivationRequest(
                project_id=ProjectId(project_id),
                release_id=ReleaseId(prepared.release_id),
                expected_parent=None if expected_parent is None else ReleaseId(expected_parent),
                expected_generation=expected_generation,
            )
            result = conn.execute(_activate_release, request.model_dump())
            with native_result_scope("activate", "activate_release"):
                row = result.one()
                with native_result_scope("activate", "activate_release", "generation"):
                    generation = _generation.validate_python(row[0], strict=True)
        except DBAPIError as exc:
            if getattr(exc.orig, "sqlstate", None) == "40001":
                raise ActivationConflict(
                    f"stale activation token for project {project_id}"
                ) from exc
            raise
        return ActivationToken(release_id, generation)

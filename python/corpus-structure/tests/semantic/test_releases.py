"""Native archive/CAS tests; this path uses only the new semantic physical schema."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from threading import Barrier
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import Engine, insert, select, text, update

from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
    releases,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.types import PreparedArtifact

from .archive_faults import administrative_archive_edit


def source_bundle(extra: bytes = b"") -> SourceBundle:
    # Deliberately preserve comments, CRLF and source/dependency ordering independently
    # of YAML's interpreted meaning and the compiler's sorted digest manifest.
    return SourceBundle(
        "archive",
        (
            SourceArtifact(
                "archive",
                b"""id: https://example.org/archive
name: archive
prefixes:
  ex: https://example.org/
default_prefix: ex
imports: [base]
classes:
  Child:
    is_a: Parent
    attributes:
      label:
        range: string
"""
                + extra,
            ),
            SourceArtifact(
                "base",
                b"""# exact imported bytes
id: https://example.org/base
name: base
prefixes:
  ex: https://example.org/
default_prefix: ex
types:
  string:
    base: str
    uri: xsd:string
classes:
  Parent:
    attributes:
      id:
        identifier: true
""".replace(b"\n", b"\r\n"),
            ),
        ),
    )


def stage(conn, bundle=None):
    bundle = source_bundle() if bundle is None else bundle
    dependencies = ResolvedDependencies(
        (SourceArtifact("opaque", b"\x00exact external bytes\xff"),)
    )
    profile = PreparationProfile()
    prepared = prepare_release(bundle, dependencies, profile)
    releases.persist_release(conn, bundle, dependencies, profile, prepared)
    return bundle, dependencies, profile, prepared


def project(conn, release_id=None):
    project_id = str(uuid4())
    conn.execute(
        insert(table("data.project")).values(
            project_id=project_id, active_release_id=release_id, generation=0
        )
    )
    return project_id


def test_archive_is_exact_offline_and_idempotent(semantic_db_engine: Engine, monkeypatch):
    with semantic_db_engine.begin() as conn:
        bundle, dependencies, profile, prepared = stage(conn)
        calls = []
        compiler = releases.prepare_release

        def counted(*args):
            calls.append(args)
            return compiler(*args)

        monkeypatch.setattr(releases, "prepare_release", counted)
        assert (
            releases.persist_release(conn, bundle, dependencies, profile, prepared)
            == prepared.release_id
        )
        assert calls == [(bundle, dependencies, profile)]  # one explicit persistence verification
        opened = releases.open_release(conn, prepared.release_id)
        assert opened == prepared
        assert len(calls) == 1  # ordinary opening never invokes preparation
        source_rows = conn.execute(select(table("sem.input"))).mappings().all()
        archived = {
            (r["input_kind"], r["input_name"]): bytes(r["content"])
            for r in source_rows
            if r["release_id"] == prepared.release_id
        }
        assert archived["source", "base"].startswith(b"# exact imported bytes\r\n")
        assert archived["source", "base"] == bundle.sources[1].content
        assert archived["dependency", "opaque"] == b"\x00exact external bytes\xff"
        loaded = releases.verify_release(conn, prepared.release_id)
        assert len(calls) == 2
        assert calls[0] == (bundle, dependencies, profile)
        assert loaded == prepared
        assert loaded.validate_json("Child", '{"id":"a"}').model_dump() == {"id": "a"}
        assert dict(
            conn.execute(
                select(
                    table("sem.class_hierarchy").c.class_id,
                    table("sem.class_hierarchy").c.ancestor_id,
                )
            ).all()
        ) == {"https://example.org/Child": "https://example.org/Parent"}
        identity = table("sem.identity_slot")
        assert set(
            conn.execute(
                select(
                    identity.c.class_id,
                    identity.c.property_id,
                    identity.c.group_id,
                    identity.c.position,
                )
            ).all()
        ) == {
            ("https://example.org/Child", "https://example.org/id", "0", 0),
            ("https://example.org/Parent", "https://example.org/id", "0", 0),
        }


def test_conflicting_artifact_refuses_without_partial_changes(semantic_db_engine: Engine):
    with semantic_db_engine.begin() as conn:
        bundle, dependencies, profile, prepared = stage(conn)
        pid = project(conn, prepared.release_id)
        forged = replace(prepared, artifacts=(PreparedArtifact("forged", b"different bytes"),))
        with pytest.raises(releases.ReleaseConflict):
            releases.persist_release(conn, bundle, dependencies, profile, forged)
        assert releases.load_release(conn, prepared.release_id) == prepared
        assert releases.activation_token(conn, pid) == releases.ActivationToken(
            prepared.release_id, 0
        )
        mismatched = SourceBundle(bundle.root, (replace(bundle.sources[0], content=b"other"),))
        with pytest.raises(releases.ReleaseConflict, match="exact inputs"):
            releases.persist_release(conn, mismatched, dependencies, profile, prepared)


@pytest.mark.parametrize(
    "relation,key,changed",
    [
        ("input", {"input_kind": "source", "input_name": "archive"}, {"content": b"tampered"}),
        ("artifact", {"artifact_name": "definitions.json"}, {"content": b"tampered"}),
        ("registry_row", {"kind": "class", "name": "Child"}, {"body": b"tampered"}),
        (
            "property_applicability",
            {
                "class_id": "https://example.org/Child",
                "property_id": "https://example.org/label",
            },
            {"required": True},
        ),
    ],
)
def test_tampered_archive_or_projection_refuses(semantic_db_engine: Engine, relation, key, changed):
    with semantic_db_engine.begin() as conn:
        *_, prepared = stage(conn)
        target = table("sem." + relation)
        with administrative_archive_edit(conn, target):
            conn.execute(
                update(target)
                .where(
                    target.c.release_id == prepared.release_id,
                    *(target.c[k] == v for k, v in key.items()),
                )
                .values(**changed)
            )
        with pytest.raises(releases.ReleaseConflict):
            releases.load_release(conn, prepared.release_id)


def test_changed_compiler_version_refuses_before_reprepare(semantic_db_engine: Engine, monkeypatch):
    with semantic_db_engine.begin() as conn:
        *_, prepared = stage(conn)
        manifest = json.loads(prepared.manifest)
        manifest["libraries"]["pydantic"] = "0.0.0"
        with administrative_archive_edit(conn, table("sem.release")):
            conn.execute(
                update(table("sem.release"))
                .where(table("sem.release").c.release_id == prepared.release_id)
                .values(manifest_bytes=json.dumps(manifest).encode())
            )

        def unexpected(*args):
            pytest.fail("a changed compiler must refuse before recompilation")

        monkeypatch.setattr(releases, "prepare_release", unexpected)
        with pytest.raises(releases.ReleaseConflict, match="compiler library versions"):
            releases.load_release(conn, prepared.release_id)


def test_release_extension_changes_rows_without_ddl(semantic_db_engine: Engine):
    snapshot_sql = text("""SELECT n.nspname,c.relname,c.relkind,a.attname,a.atttypid,a.attnotnull
        FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        LEFT JOIN pg_attribute a ON a.attrelid=c.oid AND a.attnum>0
        WHERE n.nspname IN ('sem','data') ORDER BY 1,2,4""")
    with semantic_db_engine.begin() as conn:
        *_, first = stage(conn)
        before = conn.execute(snapshot_sql).all()
        head = conn.execute(text("SELECT version_num FROM semantic_alembic_version")).all()
        *_, second = stage(conn, source_bundle(b"  Additional:\n    is_a: Parent\n"))
        assert first.release_id != second.release_id
        assert conn.execute(snapshot_sql).all() == before
        assert conn.execute(text("SELECT version_num FROM semantic_alembic_version")).all() == head
        classes = table("sem.class_definition")
        assert set(
            conn.execute(
                select(classes.c.class_id).where(classes.c.release_id == second.release_id)
            ).scalars()
        ) == {
            "https://example.org/Parent",
            "https://example.org/Child",
            "https://example.org/Additional",
        }


def test_activation_rejects_aba_and_preserves_existing_realization(semantic_db_engine: Engine):
    with semantic_db_engine.begin() as conn:
        *_, first = stage(conn)
        *_, second = stage(conn, source_bundle(b"# release two\n"))
        pid = project(conn, first.release_id)
        realization_id = str(uuid4())
        conn.execute(
            insert(table("data.realization")).values(
                realization_id=realization_id, project_id=pid, release_id=first.release_id
            )
        )
        assert (
            releases.activate_release(
                conn,
                pid,
                second.release_id,
                expected_parent=first.release_id,
                expected_generation=0,
            ).generation
            == 1
        )
        assert (
            releases.activate_release(
                conn,
                pid,
                first.release_id,
                expected_parent=second.release_id,
                expected_generation=1,
            ).generation
            == 2
        )
        with pytest.raises(releases.ActivationConflict):
            releases.activate_release(
                conn,
                pid,
                second.release_id,
                expected_parent=first.release_id,
                expected_generation=0,
            )
        assert releases.activation_token(conn, pid) == releases.ActivationToken(first.release_id, 2)
        realization = table("data.realization")
        assert (
            conn.execute(
                select(realization.c.release_id).where(
                    realization.c.realization_id == realization_id
                )
            ).scalar_one()
            == first.release_id
        )


def test_failed_constraint_admission_preserves_pointer(semantic_db_engine: Engine):
    with semantic_db_engine.begin() as conn:
        *_, first = stage(conn)
        bad = source_bundle().sources
        bad_bundle = SourceBundle(
            "archive",
            (
                replace(
                    bad[0],
                    content=bad[0].content.replace(
                        b"range: string", b"range: string\n        pattern: '(?=a)a'"
                    ),
                ),
                bad[1],
            ),
        )
        *_, unsupported = stage(conn, bad_bundle)
        pid = project(conn, first.release_id)
        with pytest.raises(ValueError):
            releases.activate_release(
                conn,
                pid,
                unsupported.release_id,
                expected_parent=first.release_id,
                expected_generation=0,
            )
        assert releases.activation_token(conn, pid) == releases.ActivationToken(first.release_id, 0)


def test_concurrent_activation_has_one_winner(semantic_db_engine: Engine):
    with semantic_db_engine.begin() as conn:
        *_, first = stage(conn)
        *_, second = stage(conn, source_bundle(b"# second\n"))
        *_, third = stage(conn, source_bundle(b"# third\n"))
        pid = project(conn, first.release_id)
    barrier = Barrier(2)

    def attempt(release_id):
        with semantic_db_engine.begin() as conn:
            barrier.wait(timeout=15)
            try:
                return releases.activate_release(
                    conn, pid, release_id, expected_parent=first.release_id, expected_generation=0
                )
            except releases.ActivationConflict:
                return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, (second.release_id, third.release_id)))
    assert sum(result is not None for result in results) == 1
    winner = next(result for result in results if result is not None)
    with semantic_db_engine.begin() as conn:
        assert releases.activation_token(conn, pid) == winner
        assert winner.generation == 1


def test_failed_archive_leaves_no_partial_release(semantic_db_engine: Engine):
    from sqlalchemy.exc import IntegrityError

    bundle = source_bundle()
    prepared = prepare_release(bundle)
    with semantic_db_engine.begin() as conn:
        with pytest.raises(IntegrityError):
            releases.persist_release(
                conn,
                bundle,
                ResolvedDependencies(),
                PreparationProfile(),
                prepared,
                parent_release_id="release:missing",
            )
        assert conn.execute(select(table("sem.release").c.release_id)).all() == []
        assert conn.execute(select(table("sem.input").c.release_id)).all() == []
        assert conn.execute(select(table("sem.artifact").c.release_id)).all() == []


def test_authenticated_writer_cannot_modify_definitions(
    semantic_db_engine: Engine,
    semantic_writer_engine: Engine,
):
    from sqlalchemy.exc import DBAPIError

    with semantic_db_engine.begin() as conn:
        *_, prepared = stage(conn)
    for name in (
        "release",
        "input",
        "artifact",
        "class_definition",
        "property_definition",
        "property_applicability",
        "class_hierarchy",
        "identity_slot",
        "vocabulary_member",
        "registry_row",
    ):
        target = table("sem." + name)
        with pytest.raises(DBAPIError) as error, semantic_writer_engine.begin() as conn:
            conn.execute(
                update(target)
                .where(target.c.release_id == prepared.release_id)
                .values(release_id=prepared.release_id)
            )
        assert isinstance(error.value.orig, psycopg.Error)
        assert error.value.orig.sqlstate == "42501"


def test_same_local_property_name_retains_distinct_iris(semantic_db_engine: Engine):
    with semantic_db_engine.begin() as conn:
        *_, prepared = stage(
            conn,
            source_bundle(b"""  Other:
    attributes:
      label:
        range: string
        slot_uri: https://another.example/label
"""),
        )
        properties = table("sem.property_definition")
        assert set(
            conn.execute(
                select(properties.c.property_id).where(
                    properties.c.release_id == prepared.release_id,
                    properties.c.name == "label",
                )
            ).scalars()
        ) == {"https://example.org/label", "https://another.example/label"}
        assert releases.load_release(conn, prepared.release_id) == prepared


def test_archive_retains_explicit_ontology_dependency_selection(semantic_db_engine: Engine):
    bundle = source_bundle()
    dependencies = ResolvedDependencies(
        artifacts=(
            SourceArtifact("opaque", b"\xff\x00"),
            SourceArtifact("ontology", b"format-version: 1.2\r\n"),
        ),
        ontology_sources=("ontology",),
    )
    prepared = prepare_release(bundle, dependencies)
    with semantic_db_engine.begin() as conn:
        releases.persist_release(conn, bundle, dependencies, PreparationProfile(), prepared)
        inputs = table("sem.input")
        assert (
            conn.execute(
                select(inputs.c.content).where(
                    inputs.c.release_id == prepared.release_id,
                    inputs.c.input_kind == "ontology_sources",
                    inputs.c.input_name == "ontology_sources",
                )
            ).scalar_one()
            == b'["ontology"]'
        )
        assert releases.load_release(conn, prepared.release_id) == prepared


def test_sql_admission_and_pointer_share_activation_savepoint(
    semantic_db_engine: Engine,
    semantic_reader_engine: Engine,
):
    from corpus_structure.semantic.authored_sql import SQLAdmissionError

    with semantic_db_engine.begin() as conn:
        *_, first = stage(conn)
        bundle = source_bundle()
        dependencies = ResolvedDependencies(
            (SourceArtifact("authored-sql/entities.sql", b"SELECT entity_id FROM data.entity"),)
        )
        prepared = prepare_release(bundle, dependencies)
        releases.persist_release(conn, bundle, dependencies, PreparationProfile(), prepared)
        pid = project(conn, first.release_id)
        with pytest.raises(SQLAdmissionError, match="restricted reader"):
            releases.activate_release(
                conn,
                pid,
                prepared.release_id,
                expected_parent=first.release_id,
                expected_generation=0,
            )
        with (
            semantic_reader_engine.connect() as reader,
            pytest.raises(releases.ActivationConflict),
        ):
            releases.activate_release(
                conn,
                pid,
                prepared.release_id,
                expected_parent=None,
                expected_generation=0,
                sql_reader=reader,
            )
        admission = table("sem.sql_admission")
        assert conn.execute(select(admission.c.release_id)).all() == []
        assert releases.activation_token(conn, pid) == releases.ActivationToken(first.release_id, 0)
        with semantic_reader_engine.connect() as reader:
            token = releases.activate_release(
                conn,
                pid,
                prepared.release_id,
                expected_parent=first.release_id,
                expected_generation=0,
                sql_reader=reader,
            )
        assert token == releases.ActivationToken(prepared.release_id, 1)
        assert conn.execute(select(admission.c.release_id)).scalars().all() == [prepared.release_id]

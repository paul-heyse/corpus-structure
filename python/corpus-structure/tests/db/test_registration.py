"""Registration (P0-S-1b): `ensure` and `compiled_for` against the migrated test database.

The packs are the minimal test pack (`fixtures/packs/minimal`) and copies of it. Expected rows are
written from schema and rules §3.4 and the revision log, not from `ensure`'s own code.
"""

from __future__ import annotations

import shutil
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import legacy_schema_registry as registry
import pytest
from sqlalchemy import Connection, Engine, text

from corpus_structure.core._model.revision import CONTENT_HASH
from corpus_structure.core.vocab import ObservationKind
from corpus_structure.schema import compile as compile_module
from corpus_structure.schema.model import read_log

REPO = Path(__file__).resolve().parents[4]
MINIMAL = REPO / "fixtures" / "packs" / "minimal"


def sql(conn: Connection, statement: str, **params: Any) -> Any:
    return conn.execute(text(statement), params)


def project(conn: Connection, name: str = "reg") -> int:
    return sql(
        conn, "INSERT INTO meta.project (name, domain) VALUES (:n, 'minimal') RETURNING id", n=name
    ).scalar_one()


def artifacts(conn: Connection, version: int) -> dict[tuple[str, str, str], tuple[str, str]]:
    rows = sql(
        conn,
        "SELECT compiler, compiler_version, kind, hash, body::text FROM "
        "meta.compiled_artifact WHERE schema_version_id = :v",
        v=version,
    )
    return {(r[0], r[1], r[2]): (r[3], r[4]) for r in rows}


def counts(conn: Connection) -> dict[str, int]:
    tables = (
        "meta.model_revision",
        "meta.schema_version",
        "meta.payload_schema",
        "meta.compiled_artifact",
        "meta.schema_slot",
        "meta.statement_kind",
        "meta.claim_modality",
        "meta.schema_rule",
        "meta.schema_class",
        "meta.schema_enum",
    )
    return {t: sql(conn, f"SELECT count(*) FROM {t}").scalar_one() for t in tables}


def test_ensure_twice_is_idempotent(db: Connection) -> None:
    pid = project(db)
    first = registry.ensure(db, pid, [MINIMAL], "human:test")
    before = counts(db)
    again = registry.ensure(db, pid, [MINIMAL], "human:test")
    assert first.created and not again.created
    assert (again.id, again.model_revision_id) == (first.id, first.model_revision_id)
    assert counts(db) == before
    assert before["meta.compiled_artifact"] == 6 and before["meta.schema_version"] == 1


def test_the_model_revision_and_payload_schema_rows(db: Connection) -> None:
    ref = registry.ensure(db, project(db), [MINIMAL], "human:test")
    entry = next(e for e in read_log() if e["content_hash"] == CONTENT_HASH)
    row = sql(
        db,
        "SELECT label, content_hash, key_scheme, compilers FROM meta.model_revision WHERE id = :i",
        i=ref.model_revision_id,
    ).one()
    assert tuple(row) == (entry["label"], CONTENT_HASH, entry["key_scheme"], entry["compilers"])
    kinds = set(
        sql(
            db,
            "SELECT kind FROM meta.payload_schema",
        ).scalars()
    )
    # every payload the version's writers write has a registered schema
    assert {k.value for k in ObservationKind} | {"compiled_artifact"} <= kinds
    unregistered = sql(
        db,
        "SELECT count(*) FROM meta.compiled_artifact a JOIN meta.payload_schema "
        "p ON p.id = a.payload_schema_id WHERE a.schema_version_id = :v AND "
        "p.kind <> 'compiled_artifact'",
        v=ref.id,
    ).scalar_one()
    assert unregistered == 0
    version = sql(
        db,
        "SELECT model_revision_id, parent_id, migration, source FROM "
        "meta.schema_version WHERE id = :v",
        v=ref.id,
    ).one()
    assert version[0] == ref.model_revision_id and version[1] is None and version[2] is None
    assert version[3]["minimal/schema/minimal.yaml"] == (MINIMAL / "schema/minimal.yaml").read_text(
        encoding="utf-8"
    )
    assert "core/rules.yaml" in version[3]


def test_the_projection_is_upserted_in_the_inserting_transaction(db: Connection) -> None:
    ref = registry.ensure(db, project(db), [MINIMAL], "human:test")
    body = sql(
        db,
        "SELECT body FROM meta.compiled_artifact WHERE schema_version_id = :v AND "
        "compiler = 'schema_tables'",
        v=ref.id,
    ).scalar_one()
    for table, key in registry.PROJECTION.items():
        stored = set(
            sql(
                db, f"SELECT {key} FROM meta.{table} WHERE schema_version_id = :v", v=ref.id
            ).scalars()
        )
        assert stored == {row[key] for row in body[table]}, table
        assert stored, table


def test_another_connection_sees_the_projection_only_with_the_commit(
    committing_db: Engine,
) -> None:
    with committing_db.connect() as writer, committing_db.connect() as reader:
        tx = writer.begin()
        ref = registry.ensure(writer, project(writer), [MINIMAL], "human:test")
        assert sql(reader, "SELECT count(*) FROM meta.schema_slot").scalar_one() == 0
        tx.commit()
        assert (
            sql(
                reader,
                "SELECT count(*) FROM meta.schema_slot WHERE schema_version_id = :v",
                v=ref.id,
            ).scalar_one()
            > 0
        )
        assert sql(reader, "SELECT count(*) FROM meta.compiled_artifact").scalar_one() == 6


def test_a_compiler_bump_adds_rows_and_keeps_the_old_ones(
    db: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = project(db)
    ref = registry.ensure(db, pid, [MINIMAL], "human:test")
    before = artifacts(db, ref.id)
    monkeypatch.setitem(compile_module.COMPILERS, "rules", "2")
    registry.ensure(db, pid, [MINIMAL], "human:test")
    after = artifacts(db, ref.id)
    assert {k: v for k, v in after.items() if k in before} == before  # byte-identical
    added = set(after) - set(before)
    assert len(added) == 1 and next(iter(added))[0] == "rules"
    assert next(iter(added))[1].startswith("2+")


def test_changed_output_without_a_version_bump_is_refused(
    db: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    pid = project(db)
    ref = registry.ensure(db, pid, [MINIMAL], "human:test")
    before = artifacts(db, ref.id)
    original = compile_module.schema_tables

    def changed(packs: Any, lookup: Any) -> dict[str, Any]:
        out = original(packs, lookup)
        return {**out, "schema_rule": []}

    monkeypatch.setattr(compile_module, "schema_tables", changed)
    refused = pytest.raises(
        registry.ArtifactMismatch, match=r"compiler schema_tables .*kind tables"
    )
    with refused, db.begin_nested():
        registry.ensure(db, pid, [MINIMAL], "human:test")
    assert artifacts(db, ref.id) == before


def test_removing_a_referenced_name_is_refused(
    db: Connection, world: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref = registry.ensure(db, world.project, [MINIMAL], "human:test")
    run = sql(
        db,
        "INSERT INTO ops.run (project_id, kind, phase, corpus_hash, model_revision_id, "
        "schema_version_id, key_scheme, policy_version_id, code_commit, status) VALUES (:p, "
        "'full', 0, 'c', :m, :v, 1, :pol, 't', 'running') RETURNING id",
        p=world.project,
        m=ref.model_revision_id,
        v=ref.id,
        pol=world.policy,
    ).scalar_one()
    sql(
        db,
        "INSERT INTO kb.entity (run_id, key, schema_version_id, type, label, scope, kind) "
        "VALUES (:r, 'stm:1', :v, 'core:Statement', 's', 'global', 'theorem')",
        r=run,
        v=ref.id,
    )
    original = compile_module.schema_tables

    def without_theorem(packs: Any, lookup: Any) -> dict[str, Any]:
        out = original(packs, lookup)
        kinds = [m for m in out["statement_kind"] if m["value"] != "theorem"]
        return {**out, "statement_kind": kinds}

    monkeypatch.setattr(compile_module, "schema_tables", without_theorem)
    monkeypatch.setitem(compile_module.COMPILERS, "schema_tables", "2")
    with pytest.raises(registry.ReferencedNameRemoved) as err, db.begin_nested():
        registry.ensure(db, world.project, [MINIMAL], "human:test")
    assert (err.value.element, err.value.table, err.value.referenced_by) == (
        "theorem",
        "statement_kind",
        "entity",
    )
    assert err.value.compiler.startswith("schema_tables 2+")


def test_compiled_for_rebuilds_from_stored_source(db: Connection, tmp_path: Path) -> None:
    pack = tmp_path / "minimal"
    shutil.copytree(MINIMAL, pack)
    ref = registry.ensure(db, project(db), [pack], "human:test")
    stored = artifacts(db, ref.id)
    (pack / "schema" / "minimal.yaml").write_text(
        "not: a pack\n", encoding="utf-8"
    )  # disk moved on
    compiled = registry.compiled_for(db, ref.id)
    assert compiled.schema_version == ref.content_hash
    assert {(a.compiler, a.compiler_version, a.kind): a.hash for a in compiled.artifacts} == {
        k: v[0] for k, v in stored.items()
    }


def test_compiled_for_refuses_another_model_revision_and_a_changed_hash(db: Connection) -> None:
    ref = registry.ensure(db, project(db), [MINIMAL], "human:test")
    sql(
        db,
        "UPDATE meta.compiled_artifact SET hash = 'tampered' WHERE schema_version_id = :v "
        "AND compiler = 'rules'",
        v=ref.id,
    )
    with pytest.raises(registry.ArtifactMismatch, match="compiler rules"):
        registry.compiled_for(db, ref.id)
    other = sql(
        db,
        "INSERT INTO meta.model_revision (label, content_hash, compilers, key_scheme) "
        "VALUES ('0.0.0', :h, '{}', 1) RETURNING id",
        h="f" * 64,
    ).scalar_one()
    sql(
        db, "UPDATE meta.schema_version SET model_revision_id = :m WHERE id = :v", m=other, v=ref.id
    )
    with pytest.raises(registry.ModelRevisionMismatch, match="a code release changed the model"):
        registry.compiled_for(db, ref.id)


def test_concurrent_ensure_leaves_one_row_per_identity(committing_db: Engine) -> None:
    with committing_db.begin() as conn:
        pid = project(conn)
    barrier = threading.Barrier(2)
    results: list[Any] = []

    def register() -> None:
        try:
            with committing_db.begin() as conn:
                barrier.wait(timeout=30)
                results.append(registry.ensure(conn, pid, [MINIMAL], "human:test"))
        except Exception as error:  # surfaced below
            results.append(error)

    threads = [threading.Thread(target=register) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=120)
    assert all(isinstance(r, registry.SchemaVersionRef) for r in results), results
    assert sorted(r.created for r in results) == [False, True]
    assert len({r.id for r in results}) == 1
    with committing_db.connect() as conn:
        c = counts(conn)
        duplicates = sql(
            conn,
            "SELECT count(*) - count(DISTINCT (schema_version_id, compiler, "
            "compiler_version, kind)) FROM meta.compiled_artifact",
        ).scalar_one()
    assert c["meta.schema_version"] == 1 and c["meta.model_revision"] == 3
    assert c["meta.compiled_artifact"] == 6 and duplicates == 0


def test_fresh_registry_preserves_payload_parent_artifacts(db: Connection) -> None:
    import pyarrow as pa

    registry.ensure(db, project(db), [MINIMAL], "human:test")
    rows = sql(
        db,
        "SELECT p.id, p.version, p.parent_id, p.arrow_schema, r.label "
        "FROM meta.payload_schema p JOIN meta.model_revision r "
        "ON r.id = p.model_revision_id "
        "WHERE p.kind = 'policy_action' ORDER BY p.version",
    ).all()
    assert len(rows) == 2
    old, new = rows
    assert (old[1], old[2], old[4]) == (1, None, "0.3.0")
    assert (new[1], new[2], new[4]) == (2, old[0], "0.4.0")
    assert pa.ipc.read_schema(pa.BufferReader(old[3])).field("limit").nullable is False
    assert pa.ipc.read_schema(pa.BufferReader(new[3])).field("limit").nullable is True


def test_unchanged_payloads_keep_original_defining_revision(db: Connection) -> None:
    registry.ensure(db, project(db), [MINIMAL], "human:test")
    versions = sql(
        db,
        "SELECT p.version, p.json_schema_id, r.label FROM meta.payload_schema p "
        "JOIN meta.model_revision r ON r.id = p.model_revision_id",
    ).all()
    initial = [row for row in versions if row[0] == 1]
    assert len(initial) == 22
    assert all(row[2] == "0.3.0" and "/a59196c4a894/" in row[1] for row in initial)
    assert [(row[2], row[1]) for row in versions if row[0] == 2] == [
        ("0.4.0", "https://corpus-structure.dev/schemas/eceef3291d1f/policy_action.json")
    ]


def test_conflicting_registered_payload_bytes_are_refused(db: Connection) -> None:
    pid = project(db)
    registry.ensure(db, pid, [MINIMAL], "human:test")
    sql(
        db,
        "UPDATE meta.payload_schema SET arrow_schema = :bad WHERE class = 'sys:PolicyAction' "
        "AND version = 1",
        bad=b"corrupt",
    )
    with pytest.raises(
        registry.RegistrationError, match="registered payload differs in arrow_schema"
    ):
        registry.ensure(db, pid, [MINIMAL], "human:test")

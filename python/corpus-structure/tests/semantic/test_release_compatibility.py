"""Versioned reader, runtime and cache controls with independent historical artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import pytest
from pydantic import AfterValidator, TypeAdapter, ValidationError

from corpus_structure.semantic import determinants
from corpus_structure.semantic.archive_reader import reconstruct_release
from corpus_structure.semantic.types import PreparationProfile

from .test_archive_reader import archived


@pytest.mark.parametrize("compiler", ["10", "11", "12"])
def test_genuine_historical_archive_acceptance_and_no_current_compile(compiler, monkeypatch):
    import corpus_structure.semantic.prepare as current

    def unavailable(*args, **kwargs):
        raise AssertionError("historical reading cannot call the current compiler")

    monkeypatch.setattr(current, "prepare_release", unavailable)
    path = Path(__file__).parents[1] / f"fixtures/semantic/reader-v{compiler}.json"
    data, bundle, artifacts = archived(path)
    assert data["profile"]["compiler_version"] == compiler
    if compiler in {"11", "12"}:
        assert len(data["historical_producer_commit"]) == 40
    release = reconstruct_release(
        data["products"],
        bytes.fromhex(data["manifest"]),
        bundle,
        PreparationProfile(**data["profile"]),
        artifacts,
    )
    value = release.validate_json("Circle", '{"id":"c","kind":"Circle","exact_amount":"1.2300"}')
    assert str(value.model_dump()["amount"]) == "1.2300"
    with pytest.raises(ValidationError):
        release.validate_json("Circle", '{"id":"c","kind":"Circle","exact_amount":"-1"}')
    assert determinants.boundary_compatible(json.loads(release.manifest)["libraries"], compiler)


@pytest.mark.parametrize("compiler", ["10", "11", "12", "13"])
@pytest.mark.parametrize("changed", ["pydantic", "pydantic-core", "python", "jsonschema", "cattrs"])
def test_runtime_compatibility_is_explicit_not_schema_equivalence(monkeypatch, compiler, changed):
    # These validators export exactly the same schema, but disagree on acceptance.
    def positive(value: int) -> int:
        if value <= 0:
            raise ValueError("positive required")
        return value

    old = TypeAdapter(int)
    changed_acceptance = TypeAdapter(Annotated[int, AfterValidator(positive)])
    assert old.json_schema() == changed_acceptance.json_schema()
    assert old.validate_python(0) == 0
    with pytest.raises(ValidationError):
        changed_acceptance.validate_python(0)
    recorded = {
        name: determinants.determinant_version(name)
        for name in (*determinants.BOUNDARY_LIBRARIES, "linkml-runtime")
    }
    assert determinants.boundary_compatible(recorded, compiler)
    original = determinants.determinant_version
    if compiler in {"10", "11"} and changed == "pydantic-core":
        installed = determinants.version
        monkeypatch.setattr(
            determinants, "version", lambda name: "changed" if name == changed else installed(name)
        )
    elif compiler in {"10", "11"} and changed == "python":
        monkeypatch.setattr(determinants.platform, "python_version", lambda: "3.14.11")
    else:
        monkeypatch.setattr(
            determinants,
            "determinant_version",
            lambda name: "changed" if name == changed else original(name),
        )
    assert not determinants.boundary_compatible(recorded, compiler)


def _restore_old_selected_result(admin, writer, admitter):
    """Restore a known historical-shaped snapshot; do not execute or regrade the old run.

    Archive bytes are genuine compiler10 output. The small fact/result snapshot is independent
    test data, not a copy of operational runs 1/2. Administrative trigger bypass is confined to
    restoring finished run/cut metadata, like a backup restore; serving uses actual read roles.
    """
    from decimal import Decimal
    from hashlib import sha256

    from sqlalchemy import insert

    from corpus_structure.semantic.identity import fact_key
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.publication import (
        EntityRow,
        EvidenceRow,
        FactRow,
        MembershipRow,
        MembershipSupportRow,
        PublicationBatch,
        SelectionRow,
        ValueRow,
        publish_batch,
    )
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.runtime import select_completed_result
    from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact

    path = Path(__file__).parents[1] / "fixtures/semantic/reader-v10-analytics.json"
    data, bundle, artifacts = archived(path)
    profile = PreparationProfile(**data["profile"])
    old = reconstruct_release(
        data["products"], bytes.fromhex(data["manifest"]), bundle, profile, artifacts
    )
    deps = ResolvedDependencies(
        tuple(SourceArtifact(x["name"], bytes.fromhex(x["content"])) for x in data["dependencies"])
    )
    r = old.release_id
    z = "historical:answer"
    project = "historical-project"
    fact = fact_key(r, z, "circle", "https://example.org/amount", Decimal("1.2300"), {})
    with admin.begin() as conn:
        persist_release(conn, bundle, deps, profile, old)
        conn.execute(insert(table("data.project")).values(project_id=project))
        conn.execute(
            insert(table("data.realization")),
            [
                dict(realization_id=key, release_id=r, project_id=project)
                for key in (z, "historical:source")
            ],
        )
    facts = tuple(
        FactRow(
            fact_key(r, z, "circle", "https://example.org/" + name, value, {}),
            "circle",
            "https://example.org/" + name,
            name,
        )
        for name, value in (("id", "circle"), ("kind", "Circle"), ("amount", Decimal("1.2300")))
    )
    publish_batch(
        writer,
        PublicationBatch(
            r,
            z,
            "historical-batch",
            entity=(EntityRow("circle"),),
            membership=(MembershipRow("circle", "https://example.org/Circle", "stated"),),
            typed_value=(
                ValueRow("id", "string", text_value="circle"),
                ValueRow("kind", "string", text_value="Circle"),
                ValueRow("amount", "decimal", decimal_lexical="1.2300"),
            ),
            fact=facts,
            selection=tuple(SelectionRow(row.fact_id) for row in facts),
            evidence=(EvidenceRow("ev", "urn:historical-source", "line:1", "fixture", "1"),),
            membership_support=(
                MembershipSupportRow("circle", "https://example.org/Circle", "ev"),
            ),
        ),
    )

    with admin.begin() as conn:
        conn.exec_driver_sql("SET LOCAL session_replication_role = replica")
        run = conn.execute(
            insert(table("ops.run"))
            .values(
                project_id=project,
                release_id=r,
                input_realization_id="historical:source",
                input_revision=0,
                dependency_digest=sha256(b"{}").hexdigest(),
                dependencies=b"{}",
                kind="extract",
                phase=0,
                options={"domain": "statistics"},
                guideline="",
                status="finished",
                code_commit="historical-fixture",
                result_realization_id=z,
                sealed=True,
            )
            .returning(table("ops.run").c.id)
        ).scalar_one()
        cut = conn.execute(
            insert(table("ops.input_cut"))
            .values(run_id=run, name="final", final=True, release_id=r, source_revision=0)
            .returning(table("ops.input_cut").c.id)
        ).scalar_one()
        conn.execute(
            insert(table("ops.completed_result")).values(
                run_id=run,
                release_id=r,
                output_realization_id=z,
                cut_id=cut,
                batch_id="historical-batch",
                dependency_digest=sha256(b"{}").hexdigest(),
                source_receipts=[],
                proof_receipts=[],
            )
        )
        conn.exec_driver_sql("SET LOCAL session_replication_role = origin")
    with admitter.begin() as conn:
        generation = select_completed_result(conn, project, run, 0)
    assert generation == 1
    return old, bundle, deps, project, run, fact


def test_selected_compiler10_answer_survives_new_activation(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_reader_engine,
    semantic_admitter_engine,
    monkeypatch,
    tmp_path,
):
    from decimal import Decimal

    from sqlalchemy import select

    from corpus_structure.semantic import prepare_release
    from corpus_structure.semantic.analytics import load_packet
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.query import QuerySpec, bind_completed_result, read_snapshot
    from corpus_structure.semantic.releases import activate_release, persist_release
    from corpus_structure.serve.export import export_packet
    from corpus_structure.serve.journey import select_run

    old, bundle, deps, project, run, fact = _restore_old_selected_result(
        semantic_db_engine, semantic_writer_engine, semantic_admitter_engine
    )
    new = prepare_release(bundle, deps)
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, deps, PreparationProfile(), new)
    uri = semantic_reader_engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )

    def answer(label):
        with read_snapshot(semantic_reader_engine) as conn:
            assert select_run(conn, project) == run
            session = bind_completed_result(conn, run)
            assert session.binding.release_id == old.release_id
            circle = session.class_handle("Circle")
            result = session.query(
                QuerySpec(circle, session.property_handle(circle, "amount"), "accepted")
            )
            assert len(result.rows) == 1
            assert result.rows[0].object == Decimal("1.2300")
            assert session.explain(fact).fact_id == fact
            packet = load_packet(session, uri)
            assert (
                next(
                    row
                    for row in packet.relations["typed_value"].to_pylist()
                    if row["value_id"] == "amount"
                )["decimal_lexical"]
                == "1.2300"
            )
        manifest = export_packet(packet, tmp_path / label)
        assert manifest["binding"]["release_id"] == old.release_id
        return result.rows[0].model_dump(), manifest["binding"]["realization_id"]

    before = answer("before")
    with semantic_db_engine.begin() as conn:
        token = activate_release(
            conn, project, new.release_id, expected_parent=None, expected_generation=1
        )
        assert token.generation == 2
    import corpus_structure.semantic.prepare as compiler

    def unavailable(*args, **kwargs):
        raise AssertionError("old answer access must not recompile")

    monkeypatch.setattr(compiler, "prepare_release", unavailable)
    after = answer("after")
    assert after == before
    with semantic_db_engine.connect() as conn:
        projects = table("data.project")
        state = conn.execute(
            select(projects.c.active_release_id, projects.c.selected_result_run_id).where(
                projects.c.project_id == project
            )
        ).one()
        assert tuple(state) == (new.release_id, run)


@pytest.mark.parametrize("compiler", ["10", "11", "12"])
def test_historical_reading_does_not_authorize_current_verification_or_activation(
    semantic_db_engine, compiler
):
    from sqlalchemy import insert

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.releases import (
        ReleaseConflict,
        activate_release,
        open_release,
        persist_release,
        verify_release,
    )
    from corpus_structure.semantic.types import ResolvedDependencies

    path = Path(__file__).parents[1] / f"fixtures/semantic/reader-v{compiler}.json"
    data, bundle, artifacts = archived(path)
    profile = PreparationProfile(**data["profile"])
    old = reconstruct_release(
        data["products"], bytes.fromhex(data["manifest"]), bundle, profile, artifacts
    )
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, ResolvedDependencies(), profile, old)
        conn.execute(insert(table("data.project")).values(project_id="transition"))
        assert open_release(conn, old.release_id).release_id == old.release_id
        with pytest.raises(ReleaseConflict, match="historical compiler"):
            verify_release(conn, old.release_id)
        with pytest.raises(ReleaseConflict, match="historical compiler"):
            activate_release(
                conn, "transition", old.release_id, expected_parent=None, expected_generation=0
            )


def test_warm_cache_does_not_admit_changed_runtime_or_failed_source_verification(
    semantic_db_engine, monkeypatch
):
    from sqlalchemy import insert

    from corpus_structure.semantic import releases
    from corpus_structure.semantic.metadata import table

    from .test_releases import stage

    with semantic_db_engine.begin() as conn:
        _, _, _, prepared = stage(conn)
        conn.execute(insert(table("data.project")).values(project_id="cached"))
        opened = releases.open_release(conn, prepared.release_id)
        assert releases.open_release(conn, prepared.release_id) is opened
        actual = determinants.determinant_version
        with monkeypatch.context() as changed:
            changed.setattr(
                determinants,
                "determinant_version",
                lambda name: "changed-core" if name == "pydantic-core" else actual(name),
            )
            with pytest.raises(releases.ReleaseConflict, match="boundary library versions"):
                releases.open_release(conn, prepared.release_id)
        assert releases.open_release(conn, prepared.release_id) is opened

        def unavailable(*args, **kwargs):
            raise ValueError("independent exact-source verification failed")

        monkeypatch.setattr(releases, "prepare_release", unavailable)
        with pytest.raises(releases.ReleaseConflict):
            releases.verify_release(conn, prepared.release_id)
        with pytest.raises(releases.ReleaseConflict):
            releases.activate_release(
                conn, "cached", prepared.release_id, expected_parent=None, expected_generation=0
            )
        # A read-cache hit is not an admission receipt.
        assert releases.open_release(conn, prepared.release_id) is opened


def test_cache_is_database_scoped_and_rechecks_current_archive_digest(
    semantic_db_engine, semantic_database_at
):
    from sqlalchemy import update

    from corpus_structure.semantic import releases
    from corpus_structure.semantic.metadata import table

    from .archive_faults import administrative_archive_edit
    from .test_releases import stage

    with (
        semantic_database_at("head") as other,
        semantic_db_engine.begin() as left,
        other.begin() as right,
    ):
        _, _, _, first = stage(left)
        _, _, _, second = stage(right)
        assert first.release_id == second.release_id
        one = releases.open_release(left, first.release_id)
        two = releases.open_release(right, second.release_id)
        assert one is not two
        assert releases.open_release(left, first.release_id) is one
        release = table("sem.release")
        with administrative_archive_edit(left, release):
            left.execute(
                update(release)
                .where(release.c.release_id == first.release_id)
                .values(prepared_bytes=b"{}")
            )
        with pytest.raises(releases.ReleaseConflict, match="archive digest"):
            releases.open_release(left, first.release_id)
        assert releases.open_release(right, second.release_id) is two


def test_shared_snapshot_restores_connection_state_after_failure(semantic_reader_engine):
    from corpus_structure.semantic.query import read_snapshot

    with pytest.raises(RuntimeError, match="cancelled consumer"):
        with read_snapshot(semantic_reader_engine) as conn:
            assert conn.get_isolation_level() == "REPEATABLE READ"
            assert conn.exec_driver_sql("SHOW transaction_read_only").scalar_one() == "on"
            raise RuntimeError("cancelled consumer")
    with semantic_reader_engine.connect() as conn:
        assert conn.get_isolation_level() == "READ COMMITTED"
        assert conn.exec_driver_sql("SHOW transaction_read_only").scalar_one() == "off"

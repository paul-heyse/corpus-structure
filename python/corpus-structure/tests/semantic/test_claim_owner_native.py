"""Actual native renewal/terminal fences under one attempt lifetime owner."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
from threading import Event
from time import monotonic, sleep
from types import SimpleNamespace

import psycopg
import pytest
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic import claim_lifetime
from corpus_structure.semantic.operation_results import CompletionResult
from corpus_structure.semantic.operations import (
    OperationBinding,
    OperationConflict,
    claim_tasks,
    complete_task,
    create_run,
    create_task,
    record_method,
)

from .operation_scenario_support import prepare_operation_scenario


class Config(BaseModel):
    pass


def claims(admin, writer, count=1):
    prepared = prepare_operation_scenario(admin)
    with writer.begin() as conn:
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="test",
        )
        method = SimpleNamespace(
            name="owned",
            version="1",
            family="profile",
            tier="deterministic",
            confidence_source=None,
            unit_type="run",
            Config=Config,
        )
        config = record_method(conn, method, "default", {}, "owned-config", prepared=prepared)
        for n in range(count):
            create_task(
                conn,
                run_id=run,
                config_id=config,
                stage="ingest",
                unit_type="run",
                input_hash=f"owned-{n}",
                unit_key=f"{n}",
            )
        tasks = claim_tasks(conn, run_id=run, config_id=config, holder="owner", limit=count)
    return prepared, tasks


def completion(prepared, claim):
    return lambda conn: complete_task(
        conn,
        task_id=claim.task_id,
        attempt=claim.attempt,
        holder=claim.holder,
        prepared=prepared,
        observations=(),
        outcome="empty",
    )


@pytest.mark.parametrize("release_lock", [True, False])
def test_run_row_contention_retries_only_once_with_current_lease(
    semantic_db_engine, semantic_writer_engine, monkeypatch, release_lock
):
    prepared, (claim,) = claims(semantic_db_engine, semantic_writer_engine)
    started, timed_out, proceed, renewed = Event(), Event(), Event(), Event()
    borrowers = []
    actual = claim_lifetime.renew_claim

    def observe(conn, **values):
        borrowers.append(conn.scalar(text("SELECT pg_backend_pid()")))
        started.set()
        try:
            actual(conn, **values)
        except DBAPIError:
            if len(borrowers) == 1:
                timed_out.set()
                assert proceed.wait(5)
            raise
        renewed.set()

    monkeypatch.setattr(claim_lifetime, "renew_claim", observe)
    settings = claim_lifetime.DatabaseSettings(
        renewal_statement_timeout_seconds=0.5,
        renewal_lock_timeout_seconds=0.5,
    )
    expected = nullcontext() if release_lock else pytest.raises(DBAPIError)
    with (
        expected as failure,
        semantic_db_engine.connect() as blocker,
        semantic_db_engine.connect() as observer,
    ):
        blocker_pid = blocker.scalar(text("SELECT pg_backend_pid()"))
        blocker.execute(
            text("SELECT id FROM ops.run WHERE id=:id FOR UPDATE"), {"id": claim.run_id}
        )
        with claim_lifetime.maintained_claims(
            semantic_writer_engine, (claim,), "owner", interval=0.01, database=settings
        ) as owner:
            try:
                assert started.wait(5)
                deadline = monotonic() + 5
                while True:
                    blockers = observer.scalar(
                        text("SELECT pg_blocking_pids(:pid)"), {"pid": borrowers[0]}
                    )
                    if blocker_pid in blockers:
                        break
                    assert not timed_out.is_set() and monotonic() < deadline
                    sleep(0.005)
                assert timed_out.wait(5)
                if release_lock:
                    blocker.rollback()
            finally:
                proceed.set()
            if release_lock:
                assert renewed.wait(5)
                result = owner.settle(claim, completion(prepared, claim))
                assert isinstance(result, CompletionResult) and result.transaction == "applied"
            else:
                deadline = monotonic() + 5
                while monotonic() < deadline:
                    owner()
                    sleep(0.005)
                pytest.fail("renewal remained active after its retry was exhausted")
    if failure is not None:
        assert getattr(failure.value.orig, "sqlstate", None) == "57014"
        assert len(borrowers) == 2


def test_renewal_refuses_expired_owner_before_and_after_reassignment(
    semantic_db_engine, semantic_writer_engine
):
    _, (claim,) = claims(semantic_db_engine, semantic_writer_engine)
    with semantic_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.execute(
            text(
                "UPDATE ops.task SET lease_until=clock_timestamp()-interval '1 second' WHERE id=:id"
            ),
            {"id": claim.task_id},
        )

    def renew(conn, owner):
        claim_lifetime.renew_claim(
            conn, task_id=owner.task_id, attempt=owner.attempt, holder=owner.holder
        )

    with pytest.raises(OperationConflict), semantic_writer_engine.begin() as conn:
        renew(conn, claim)
    with semantic_writer_engine.begin() as conn:
        (new_owner,) = claim_tasks(
            conn, run_id=claim.run_id, config_id=claim.method_config_id, holder="new-owner"
        )
        assert new_owner.attempt > claim.attempt
        renew(conn, new_owner)
    with pytest.raises(OperationConflict), semantic_writer_engine.begin() as conn:
        renew(conn, claim)


@pytest.mark.parametrize("completion_seconds", [1.0, 0.05])
def test_completion_owns_its_finite_deadline_instead_of_renewal_budget(
    semantic_db_engine, semantic_writer_engine, completion_seconds
):
    prepared, (claim,) = claims(semantic_db_engine, semantic_writer_engine)
    database = claim_lifetime.DatabaseSettings(
        renewal_statement_timeout_seconds=0.03,
        renewal_lock_timeout_seconds=0.01,
        completion_statement_timeout_seconds=completion_seconds,
    )
    owner = claim_lifetime.ClaimOwner(
        semantic_writer_engine, (claim,), "owner", database, lambda: None
    )
    seen = []

    def delayed_completion(conn):
        seen.append(
            conn.execute(
                text(
                    "SELECT current_setting('statement_timeout')::interval, "
                    "current_setting('lock_timeout')::interval"
                )
            ).one()
        )
        conn.execute(text("SELECT pg_sleep(0.15)"))
        return completion(prepared, claim)(conn)

    if completion_seconds > 0.15:
        result = owner.settle(claim, delayed_completion)
        assert isinstance(result, CompletionResult)
        assert not owner.active
    else:
        with pytest.raises(DBAPIError) as caught:
            owner.settle(claim, delayed_completion)
        assert getattr(caught.value.orig, "sqlstate", None) == "57014"
        assert (claim.task_id, claim.attempt, "owner") in owner.active
        with semantic_writer_engine.connect() as conn:
            assert (
                conn.scalar(
                    text("SELECT status FROM ops.task WHERE id=:id"), dict(id=claim.task_id)
                )
                == "running"
            )
    assert seen[0][0].total_seconds() == completion_seconds
    assert seen[0][1].total_seconds() == 0.01


def test_renewal_is_serialized_through_terminal_commit_and_retirement(
    semantic_db_engine, semantic_writer_engine, monkeypatch
):
    prepared, (claim,) = claims(semantic_db_engine, semantic_writer_engine)
    entered, release, completed = Event(), Event(), Event()
    renewals = []
    actual = claim_lifetime.renew_claim

    def delayed(conn, **values):
        renewals.append(values)
        entered.set()
        assert release.wait(5)
        assert not completed.is_set()
        actual(conn, **values)

    monkeypatch.setattr(claim_lifetime, "renew_claim", delayed)
    with claim_lifetime.maintained_claims(
        semantic_writer_engine, [claim], "owner", interval=0.01
    ) as owner:
        assert entered.wait(5)
        with ThreadPoolExecutor(1) as pool:
            pending = pool.submit(owner.settle, claim, completion(prepared, claim))
            assert not pending.done()
            release.set()
            result = pending.result(5)
        completed.set()
        assert isinstance(result, CompletionResult)
        assert result.transaction == "applied" and result.receipt.attempt == claim.attempt
        assert not owner.active
    assert len(renewals) == 1
    with semantic_writer_engine.begin() as conn, pytest.raises(OperationConflict):
        actual(conn, task_id=claim.task_id, attempt=claim.attempt, holder="owner")


def test_lost_commit_response_replays_exact_completion_before_retirement(
    semantic_db_engine, semantic_writer_engine
):
    prepared, (claim,) = claims(semantic_db_engine, semantic_writer_engine)
    lost = []

    class ResponseLost:
        @contextmanager
        def connect(self):
            with semantic_writer_engine.connect() as conn:

                class Connection:
                    @contextmanager
                    def begin(self):
                        with conn.begin():
                            yield
                        if not lost:
                            lost.append(True)
                            raise psycopg.OperationalError("commit response lost")

                    def __getattr__(self, name):
                        return getattr(conn, name)

                yield Connection()

    owner = claim_lifetime.ClaimOwner(
        ResponseLost(), [claim], "owner", claim_lifetime.DatabaseSettings(), lambda: None
    )
    result = owner.settle(claim, completion(prepared, claim))
    assert isinstance(result, CompletionResult)
    assert result.transaction == "replay" and result.receipt.attempt == claim.attempt
    assert not owner.active
    with semantic_db_engine.connect() as conn:
        assert (
            conn.scalar(text("SELECT status FROM ops.task WHERE id=:id"), {"id": claim.task_id})
            == "empty"
        )
        assert (
            conn.scalar(
                text("SELECT count(*) FROM kb.observation WHERE task_id=:id"), {"id": claim.task_id}
            )
            == 0
        )


def test_later_failure_preserves_earlier_durable_completion(
    semantic_db_engine, semantic_writer_engine
):
    prepared, owned = claims(semantic_db_engine, semantic_writer_engine, 2)
    first, second = owned
    with (
        pytest.raises(OperationConflict, match="later task failed"),
        claim_lifetime.maintained_claims(semantic_writer_engine, owned, "owner") as owner,
    ):
        owner.settle(first, completion(prepared, first))

        def fail(conn):
            raise OperationConflict("later task failed")

        owner.settle(second, fail)
    with semantic_db_engine.connect() as conn:
        assert (
            conn.scalar(text("SELECT status FROM ops.task WHERE id=:id"), {"id": first.task_id})
            == "empty"
        )
        assert (
            conn.scalar(text("SELECT status FROM ops.task WHERE id=:id"), {"id": second.task_id})
            == "running"
        )


def test_owned_reader_selection_snapshot_and_references_survive_closure(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    from sqlalchemy import select
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.orchestrate.source_reader import ScopedSourceReader
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.operations import BoundReader, register_document

    prepared = prepare_operation_scenario(semantic_db_engine)
    path = tmp_path / "original.pdf"
    path.write_bytes(b"retained controlled original")
    with semantic_writer_engine.begin() as conn:
        doc = register_document(
            conn,
            project_id="p",
            source_uri="selected.pdf",
            original_path=str(path),
            original=path.read_bytes(),
            mime="application/pdf",
        )
        other = register_document(
            conn,
            project_id="p",
            source_uri="excluded.pdf",
            original_path=str(path),
            original=path.read_bytes(),
            mime="application/pdf",
        )
        key = conn.scalar(
            select(table("kb.document").c.key).where(table("kb.document").c.id == doc)
        )
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="full",
            options={"corpus": {"documents": [key]}},
            code_commit="test",
        )
        bound = BoundReader(conn, run, prepared)
    reader = ScopedSourceReader(semantic_writer_engine, bound)
    selected = reader.documents(("selected.pdf", "excluded.pdf"))
    assert [(ref.unit_id, ref.unit_key) for ref in selected] == [(doc, key)]
    assert reader.documents(("excluded.pdf",)) == ()
    # The actual document query is run on the selected-view references; dedup/order are owned.
    monkeypatch.setattr(
        bound,
        "source_views",
        lambda: (SimpleNamespace(document_id=doc), SimpleNamespace(document_id=doc)),
    )
    assert reader.source_view_documents() == selected
    assert selected[0].unit_key == key and selected[0].unit_id != other
    assert not hasattr(reader, "connection")
    with pytest.raises(DBAPIError) as denied:
        reader._read(
            lambda owner: owner.conn.execute(
                text("UPDATE kb.document SET title='forbidden' WHERE id=:id"), {"id": doc}
            )
        )
    assert isinstance(denied.value.orig, psycopg.Error)
    assert denied.value.orig.sqlstate == "25006"
    with pytest.raises(DBAPIError) as registration:
        reader._read(
            lambda owner: register_document(
                owner.conn,
                project_id="p",
                source_uri="forbidden.pdf",
                original_path=str(path),
                original=path.read_bytes(),
                mime="application/pdf",
            )
        )
    assert isinstance(registration.value.orig, psycopg.Error)
    assert registration.value.orig.sqlstate == "25006"
    # Connection ownership is restored after both failures.
    assert reader.documents(("selected.pdf",)) == selected


def test_uncertain_intent_cannot_be_suppressed_on_normal_owner_exit(
    semantic_db_engine, semantic_writer_engine, monkeypatch
):
    prepared, (claim,) = claims(semantic_db_engine, semantic_writer_engine)
    del prepared
    with (
        pytest.raises(claim_lifetime.ClaimSettlementUncertain),
        claim_lifetime.maintained_claims(semantic_writer_engine, [claim], "owner") as owner,
    ):
        intent = claim_lifetime.ClaimSettlementUncertain(claim, "owner", lambda conn: None)
        owner.uncertain[(claim.task_id, claim.attempt, "owner")] = intent


def test_slow_later_original_does_not_hold_earlier_task_custody_lock(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    from corpus_structure.orchestrate.semantic import _retain_source_originals
    from corpus_structure.semantic import operations

    prepared = prepare_operation_scenario(semantic_db_engine, observations=True)
    method = SimpleNamespace(
        name="owned",
        version="custody-control",
        family="profile",
        tier="deterministic",
        confidence_source=None,
        unit_type="document",
        Config=Config,
        original_recipe=lambda config: b'{"recipe":"owned-custody-control"}',
    )
    with semantic_writer_engine.begin() as conn:
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="custody-control",
        )
        config = record_method(conn, method, "default", {}, "custody-config", prepared=prepared)
        documents = []
        for number in range(2):
            path = tmp_path / f"custody-{number}.pdf"
            original = f"%PDF-1.7\nindependent original {number}".encode()
            path.write_bytes(original)
            identity = operations.register_document(
                conn,
                project_id="p",
                source_uri=f"custody-{number}.pdf",
                original_path=str(path),
                original=original,
                mime="application/pdf",
            )
            documents.append(identity)
            create_task(
                conn,
                run_id=run,
                config_id=config,
                stage="ingest",
                unit_type="document",
                unit_id=identity,
                unit_key=f"custody-{number}",
                input_hash=f"custody-{number}",
            )
        owned = claim_tasks(conn, run_id=run, config_id=config, holder="owner", limit=2)
    first = next(task for task in owned if task.unit_id == documents[0])
    later_read, renewed_first = Event(), Event()
    actual_read, actual_renew = operations.read_original, claim_lifetime.renew_claim

    def slow_read(conn, identity, **values):
        if identity == documents[1]:
            later_read.set()
            # Renewal must finish while the later original is still being prepared.
            assert renewed_first.wait(5)
        return actual_read(conn, identity, **values)

    def observed_renewal(conn, **values):
        actual_renew(conn, **values)
        if later_read.is_set() and values["task_id"] == first.task_id:
            renewed_first.set()

    monkeypatch.setattr(operations, "read_original", slow_read)
    monkeypatch.setattr(claim_lifetime, "renew_claim", observed_renewal)
    with claim_lifetime.maintained_claims(
        semantic_writer_engine, owned, "owner", interval=0.01
    ) as owner:
        _retain_source_originals(
            semantic_writer_engine, owned, method, Config(), "owner", prepared, owner
        )
        assert renewed_first.is_set()
        for claim in owned:
            owner.settle(claim, completion(prepared, claim))
    with semantic_db_engine.connect() as conn:
        assert (
            conn.scalar(
                text("SELECT count(*) FROM ops.source_build WHERE task_id = ANY(:ids)"),
                {"ids": [claim.task_id for claim in owned]},
            )
            == 2
        )
        assert (
            conn.scalar(
                text("SELECT count(*) FROM ops.task WHERE run_id=:run AND status='empty'"),
                {"run": run},
            )
            == 2
        )

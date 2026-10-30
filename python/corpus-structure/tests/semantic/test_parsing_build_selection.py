"""Pinned build selection never chooses a competing source product implicitly."""

from types import SimpleNamespace

import pytest
from pydantic import create_model
from sqlalchemy import select, text

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    BoundReader,
    OperationConflict,
    claim_tasks,
    create_task,
    read_rendition,
    record_method,
    store_rendition,
)
from corpus_structure.semantic.parsing_products import (
    prepare_parsing_product,
    store_parsing_product,
)

from .test_operations import setup
from .test_parsing_products import _native_build, product_values


def test_competing_builds_require_a_pin_even_when_rendition_content_is_identical(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    prepared = setup(semantic_db_engine, observations=True, composed=True)
    original = b"a\xc3\xa9 "
    first_product = prepare_parsing_product(product_values(), original)
    second_values = product_values()
    second_values["semantic_state"] = "ambiguous"
    second_product = prepare_parsing_product(second_values, original)
    with semantic_writer_engine.begin() as conn:
        run, first, attempt, rendition = _native_build(conn, prepared, original, tmp_path)
        assert BoundReader(conn, run, prepared).parsing_product(rendition) is None
        store_parsing_product(
            conn, task_id=first, attempt=attempt, holder="fixture", product=first_product
        )
        document = conn.execute(
            select(table("ops.rendition_build").c.document_id).where(
                table("ops.rendition_build").c.task_id == first
            )
        ).scalar_one()
        method = SimpleNamespace(
            name="ingest.fixture",
            version="1",
            family="ingest",
            tier="deterministic",
            confidence_source=None,
            unit_type="document",
            Config=create_model("FixtureConfig"),
        )
        config = record_method(conn, method, "other", {}, "other-source-config")
        second = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="ingest",
            unit_type="document",
            unit_id=document,
            input_hash="other-input",
        )
        claimed = claim_tasks(conn, run_id=run, config_id=config, holder="fixture")[0]
        assert (
            store_rendition(
                conn,
                run_id=run,
                document_id=document,
                content=read_rendition(conn, rendition, prepared=prepared),
                task_id=second,
                config_id=config,
                parse_detail={},
                prepared=prepared,
            )
            == rendition
        )
        store_parsing_product(
            conn,
            task_id=second,
            attempt=claimed.attempt,
            holder="fixture",
            product=second_product,
        )
    with semantic_reader_engine.begin() as conn:
        reader = BoundReader(conn, run, prepared)
        with pytest.raises(OperationConflict, match="multiple parsing product builds"):
            reader.parsing_product(rendition)
        assert reader.parsing_product(rendition, producing_task_id=first) == first_product
        assert reader.parsing_product(rendition, producing_task_id=second) == second_product


def test_publication_waits_for_run_before_locking_its_task(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    from concurrent.futures import ThreadPoolExecutor
    from queue import Queue
    from time import monotonic, sleep

    from corpus_structure.semantic.parsing_products import parsing_context_for_release

    prepared = setup(semantic_db_engine, observations=True, composed=True)
    original = b"a\xc3\xa9 "
    product = prepare_parsing_product(product_values(), original)
    with semantic_writer_engine.begin() as conn:
        run, task, attempt, _ = _native_build(conn, prepared, original, tmp_path)
        context = parsing_context_for_release(conn, prepared)
    backend: Queue[int] = Queue()

    def publish() -> str:
        with semantic_writer_engine.begin() as conn:
            backend.put(conn.execute(text("SELECT pg_backend_pid()")).scalar_one())
            return store_parsing_product(
                conn,
                task_id=task,
                attempt=attempt,
                holder="fixture",
                product=product,
                context=context,
            )

    with ThreadPoolExecutor(max_workers=1) as workers:
        with semantic_db_engine.connect() as blocker:
            transaction = blocker.begin()
            blocker_pid = blocker.execute(text("SELECT pg_backend_pid()")).scalar_one()
            blocker.execute(text("SELECT id FROM ops.run WHERE id=:run FOR UPDATE"), {"run": run})
            pending = workers.submit(publish)
            try:
                pid = backend.get(timeout=5)
                deadline = monotonic() + 5
                with semantic_db_engine.connect() as observer:
                    while (
                        observer.execute(
                            text("SELECT :blocker = ANY(pg_blocking_pids(:pid))"),
                            {"pid": pid, "blocker": blocker_pid},
                        ).scalar_one()
                        is not True
                    ):
                        if pending.done():
                            pending.result()
                            pytest.fail("publication did not wait for its locked source run")
                        assert monotonic() < deadline, "publisher did not reach its run lock"
                        sleep(0.01)
                    # A waiter must not hold the task while waiting on the enclosing run:
                    # complete_unit acquires these in the opposite order otherwise.
                    observer.execute(
                        text("SELECT id FROM ops.task WHERE id=:task FOR UPDATE NOWAIT"),
                        {"task": task},
                    )
            finally:
                transaction.rollback()
        assert pending.result(timeout=5) == product.digest

"""Native source reuse retains declared product custody across retained source tasks."""

from hashlib import sha256
from importlib.resources import files
from types import SimpleNamespace
from typing import Any

import pytest
from docling_core.types.doc import DocItemLabel, DoclingDocument, GroupLabel
from pydantic import create_model
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from corpus_structure.ingest.pdf import PdfConversion, publication_payload
from corpus_structure.ingest.pdf_hierarchy import snapshot
from corpus_structure.semantic._operation_calls import select_source_view
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    BoundReader,
    OperationBinding,
    claim_tasks,
    complete_task,
    create_run,
    create_task,
    end_source_run,
    record_method,
    register_document,
)
from corpus_structure.semantic.pdf_contracts import prepare_pdf_product, store_pdf_original
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import (
    select_reused_source_views,
    selected_source_views,
    store_source_view,
)

from .native_record_fixtures import publish_native_record_fixture
from .operation_scenario_support import prepare_operation_scenario


@pytest.fixture
def reuse_sources(semantic_db_engine, semantic_writer_engine, tmp_path):
    prepared = prepare_operation_scenario(semantic_db_engine, observations=True, composed=True)
    writer = semantic_writer_engine
    original = b"%PDF-1.7 retained source reuse custody"
    recipe = b'{"fixture":"retained-source-reuse"}'
    schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    config_type = create_model(
        "RetainedSourceReuseFixture",
        native_product=(dict[str, Any] | None, None),
        integrated_product=(dict[str, Any] | None, None),
    )
    method = SimpleNamespace(
        name="pdf.view-fixture",
        version="1",
        family="ingest",
        tier="deterministic",
        confidence_source=None,
        unit_type="document",
        Config=config_type,
    )

    def run(conn):
        return create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, b"{}"),
            kind="full",
            options={},
            code_commit="retained-source-reuse-test",
        )

    def config(conn, params):
        return record_method(
            conn,
            method,
            "default",
            params,
            sha256(canonical_bytes(params)).hexdigest(),
            prepared=prepared,
        )

    def task(conn, run_id, config_id, document_id, identity, *, fresh=False):
        return create_task(
            conn,
            run_id=run_id,
            config_id=config_id,
            stage="ingest",
            unit_type="document",
            unit_id=document_id,
            unit_key="source-reuse",
            input_hash=identity,
            fresh=fresh,
        )

    def complete(conn, claim):
        complete_task(
            conn,
            task_id=claim.task_id,
            attempt=claim.attempt,
            holder=claim.holder,
            prepared=prepared,
            observations=[],
            outcome="empty",
        )

    with writer.begin() as conn:
        path = tmp_path / "source.pdf"
        path.write_bytes(original)
        document_id = register_document(
            conn,
            project_id="p",
            source_uri="file:source-reuse",
            original_path=str(path),
            original=original,
            mime="application/pdf",
        )
        origin_run = run(conn)
        native_config = config(conn, {})

    def publish(index, source_run, source_config):
        document = DoclingDocument(name=f"Native product {index}")
        section = document.add_group(label=GroupLabel.SECTION, name=f"Section {index}")
        document.add_text(
            label=DocItemLabel.TEXT, text=f"Independent source {index}.", parent=section
        )
        conversion = PdfConversion(
            sha256(original).hexdigest(), recipe, snapshot(document), "success", (), (), (), None
        )
        payload = publication_payload(
            conversion,
            product_key=f"native-{index}",
            schema_digest=sha256(schema).hexdigest(),
            section_refs=frozenset({section.self_ref}),
        )
        product = prepare_pdf_product(payload, original, schema, recipe)
        identity = f"native-input-{index}"
        with writer.begin() as conn:
            native_task = task(conn, source_run, source_config, document_id, identity, fresh=True)
            claim = claim_tasks(
                conn, run_id=source_run, config_id=source_config, holder="native-reuse-fixture"
            )[0]
            store_pdf_original(
                conn,
                task_id=native_task,
                attempt=claim.attempt,
                holder=claim.holder,
                original=original,
                recipe_bytes=recipe,
            )
        published = publish_native_record_fixture(
            writer,
            tmp_path / f"native-{index}",
            task_id=native_task,
            attempt=claim.attempt,
            holder=claim.holder,
            product=product,
            document=document,
        )
        pin = ProductReference(native_task, f"native-{index}", published.logical_digest)
        with writer.begin() as conn:
            reader = BoundReader(conn, source_run, prepared)
            reader.bind_source_tasks({document_id: native_task})
            drafts = reader.native_section_drafts(
                pin,
                document_id=document_id,
                selections=(),
                membership="descendants",
                scope=None,
                consumer_release=prepared.release_id,
            )
            assert len(drafts) == 1
            view_id = store_source_view(
                conn,
                run_id=source_run,
                task_id=native_task,
                attempt=claim.attempt,
                holder=claim.holder,
                draft=drafts[0],
                position=index,
            )
            complete(conn, claim)
        return SimpleNamespace(pin=pin, task=native_task, view=view_id, identity=identity)

    products = [publish(index, origin_run, native_config) for index in range(2)]
    return SimpleNamespace(
        writer=writer,
        prepared=prepared,
        original=original,
        recipe=recipe,
        document=document_id,
        origin_run=origin_run,
        native_config=native_config,
        products=products,
        run=run,
        config=config,
        task=task,
        complete=complete,
        publish=publish,
    )


def retained_origin(scenario, params, *, document_id=None, original=None):
    """A successful retained-source task with two legitimate same-document selections."""
    document_id = scenario.document if document_id is None else document_id
    original = scenario.original if original is None else original
    with scenario.writer.begin() as conn:
        run_id = scenario.run(conn)
        config_id = scenario.config(conn, params)
        task_id = scenario.task(conn, run_id, config_id, document_id, "retained-input", fresh=True)
        claim = claim_tasks(
            conn, run_id=run_id, config_id=config_id, holder="retained-reuse-fixture"
        )[0]
        store_pdf_original(
            conn,
            task_id=task_id,
            attempt=claim.attempt,
            holder=claim.holder,
            original=original,
            recipe_bytes=scenario.recipe,
        )
        for product in scenario.products:
            select_source_view(
                conn,
                run_id=run_id,
                source_run_id=scenario.origin_run,
                source_view_id=product.view,
                projection_context=scenario.prepared,
            )
        scenario.complete(conn, claim)
        # The source task completed before another operation cancelled its owning run.
        end_source_run(conn, run_id, prepared=scenario.prepared)
    return config_id, task_id


def reuse(scenario, config_id, identity="retained-input", *, document_id=None):
    document_id = scenario.document if document_id is None else document_id
    with scenario.writer.begin() as conn:
        run_id = scenario.run(conn)
        task_id = scenario.task(conn, run_id, config_id, document_id, identity)
        task_table = table("ops.task")
        origin = conn.scalar(select(task_table.c.reused_task_id).where(task_table.c.id == task_id))
        assert origin is not None
        select_reused_source_views(conn, run_id=run_id, task_id=task_id)
        selected = selected_source_views(conn, run_id)
    return run_id, task_id, origin, selected


@pytest.mark.parametrize("selector", ["native_product", "integrated_product"])
def test_retained_source_reuse_keeps_exact_declared_pin_and_repeated_origin(
    reuse_sources, selector
):
    s = reuse_sources
    expected, sibling = s.products
    config_id, origin_task = retained_origin(s, {selector: expected.pin.values()})
    assert origin_task != expected.task
    for _ in range(2):
        _, _, origin, selected = reuse(s, config_id)
        # Reuse resolution stays anchored to the successful task, not a reused task chain.
        assert origin == origin_task
        assert [(view.id, view.native_product) for view in selected] == [
            (expected.view, expected.pin)
        ]
        assert sibling.view not in {view.id for view in selected}


def test_new_native_producer_reuse_keeps_only_its_own_product(reuse_sources):
    s = reuse_sources
    expected, sibling = s.products
    _, _, origin, selected = reuse(s, s.native_config, expected.identity)
    assert origin == expected.task
    assert [(view.id, view.native_product) for view in selected] == [(expected.view, expected.pin)]
    assert sibling.view not in {view.id for view in selected}


def test_configured_native_input_preserves_producers_different_own_output(reuse_sources):
    s = reuse_sources
    retained_input = s.products[0]
    with s.writer.begin() as conn:
        producer_run = s.run(conn)
        config_id = s.config(conn, {"native_product": retained_input.pin.values()})
    output = s.publish(2, producer_run, config_id)
    assert output.pin.task_id != retained_input.pin.task_id
    assert output.pin.product_key != retained_input.pin.product_key
    assert output.pin.content_digest != retained_input.pin.content_digest
    _, _, origin, selected = reuse(s, config_id, output.identity)
    assert origin == output.task
    assert [(view.id, view.native_product) for view in selected] == [(output.view, output.pin)]


@pytest.mark.parametrize("fault", ["digest", "key", "task", "malformed_task"])
def test_retained_source_reuse_excludes_mismatched_complete_pin(reuse_sources, fault):
    s = reuse_sources
    pin = s.products[0].pin.values()
    if fault == "digest":
        pin["content_digest"] = "0" * 64
    elif fault == "key":
        pin["product_key"] = "absent-product"
    elif fault == "task":
        pin["task_id"] = s.products[1].task
    else:
        pin["task_id"] = "not-a-numeric-task"
    config_id, origin_task = retained_origin(s, {"integrated_product": pin})
    _, _, origin, selected = reuse(s, config_id)
    assert origin == origin_task
    assert selected == ()


def test_closed_run_cannot_acquire_reused_source_selection(reuse_sources):
    s = reuse_sources
    expected = s.products[0]
    with s.writer.begin() as conn:
        run_id = s.run(conn)
        task_id = s.task(conn, run_id, s.native_config, s.document, expected.identity)
        end_source_run(conn, run_id, prepared=s.prepared)
    with pytest.raises(DBAPIError, match="successful source origin"), s.writer.begin() as conn:
        select_reused_source_views(conn, run_id=run_id, task_id=task_id)
    with s.writer.connect() as conn:
        assert selected_source_views(conn, run_id) == ()


def test_retained_source_reuse_excludes_another_document(reuse_sources, tmp_path):
    s = reuse_sources
    original = b"%PDF-1.7 another registered original"
    path = tmp_path / "other.pdf"
    path.write_bytes(original)
    with s.writer.begin() as conn:
        document_id = register_document(
            conn,
            project_id="p",
            source_uri="file:another-source-reuse-original",
            original_path=str(path),
            original=original,
            mime="application/pdf",
        )
    assert document_id != s.document
    config_id, origin_task = retained_origin(
        s,
        {"native_product": s.products[0].pin.values()},
        document_id=document_id,
        original=original,
    )
    _, _, origin, selected = reuse(s, config_id, document_id=document_id)
    assert origin == origin_task
    assert selected == ()


def test_retained_source_reuse_refuses_two_declared_products(reuse_sources):
    s = reuse_sources
    config_id, _ = retained_origin(
        s,
        {
            "native_product": s.products[0].pin.values(),
            "integrated_product": s.products[1].pin.values(),
        },
    )
    with pytest.raises(DBAPIError, match="one declared retained product"):
        reuse(s, config_id)

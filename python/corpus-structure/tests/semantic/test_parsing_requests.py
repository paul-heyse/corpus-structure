"""On-demand parsing owns a real new native attempt over pinned archived products."""
from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select

from corpus_structure.core.evidence import RenditionContent, Segment
from corpus_structure.core.vocab import SegmentKind
from corpus_structure.ingest.html import _parse_with_capture
from corpus_structure.ingest.source_capture import Extent, Projection
from corpus_structure.ingest.text_product import text_product_artifacts, text_product_payload
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (OperationBinding, claim_tasks, complete_task,
    create_run, create_task, record_method, register_document, seal_cut, store_rendition)
from corpus_structure.semantic.parsing_products import (PreparedParsingProductSet, ProductReference,
    prepare_layered_product, prepare_parsing_product, read_layered_product, select_layered_products,
    store_layered_products, store_parsing_product)
from corpus_structure.semantic.parsing_requests import ParsingRequestUnavailable, request_parsing

from .test_operations import setup


def source_build(admin, writer, tmp_path, *, canonical="x+x", macros=None):
    from pydantic import create_model
    from types import SimpleNamespace
    from corpus_structure.core.evidence import MacroDef

    prepared = setup(admin, observations=True, composed=True)
    raw = ("<p>" + canonical + "</p>").encode()
    _, _, capture = _parse_with_capture(raw)
    pure = capture.finish(canonical, (Projection(0, len(canonical), (Extent(3, 3 + len(canonical)),), category="math"),))
    source = prepare_parsing_product(pure.values(), raw)
    dependencies = canonical_bytes({"operations": {"normalize.formula": {"parameters": {
        "math": {"macros": macros or {}, "constants": []}}}}})
    with writer.begin() as conn:
        run = create_run(conn, project_id="p", binding=OperationBinding(prepared.release_id, "z", 0, dependencies),
                         kind="slice", options={}, code_commit="request-fixture")
        method = SimpleNamespace(name="ingest.fixture", version="1", family="ingest", tier="deterministic",
                                 confidence_source=None, unit_type="document", Config=create_model("SourceFixture"))
        config = record_method(conn, method, "fixture", {}, "request-source-fixture")
        path = tmp_path / "source.html"
        path.write_bytes(raw)
        doc = register_document(conn, project_id="p", source_uri="request-source", original_path=str(path), original=raw)
        task = create_task(conn, run_id=run, config_id=config, stage="ingest", unit_type="document", unit_id=doc,
                           input_hash="source-fixture", unit_key="source-fixture")
        claim = claim_tasks(conn, run_id=run, config_id=config, holder="fixture")[0]
        content = RenditionContent(canonical_text=canonical, document=Segment(kind=SegmentKind.DOCUMENT,
            start=0, end=len(canonical), children=(Segment(kind=SegmentKind.MATH_INLINE, start=0, end=len(canonical)),)))
        rendition = store_rendition(conn, run_id=run, document_id=doc, content=content, task_id=task,
                                   config_id=config, parse_detail={}, prepared=prepared)
        store_parsing_product(conn, task_id=task, attempt=claim.attempt, holder="fixture", product=source)
        root = ProductReference(task, "source", source.digest)
        payload = text_product_payload(canonical, root=root.values(), math_ranges=[(0, len(canonical), None, None)],
            fallback_macros={n: MacroDef(body=b) for n,b in (macros or {}).items()}, fallback_source_ref="fixture:archived-math", structure=False)
        text = prepare_layered_product(payload)
        refs = store_layered_products(conn, task_id=task, attempt=claim.attempt, holder="fixture",
            products=PreparedParsingProductSet((text,), required=("text",), artifacts=text_product_artifacts(payload)))
        complete_task(conn, task_id=task, attempt=claim.attempt, holder="fixture", prepared=prepared,
                      observations=[], outcome="empty")
        seal_cut(conn, run, "source", final=True)
    return prepared, run, root, refs[0], rendition


def test_native_weak_requests_use_pinned_inputs_and_leave_source_sealed(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, monkeypatch
):
    from corpus_structure.methods.math import grammar
    def forbidden(*args, **kwargs):
        raise AssertionError("weak demand entered mathematical recognition")
    _, source_run, root, text, rendition = source_build(semantic_db_engine, semantic_writer_engine, tmp_path,
        macros={r"\archived": "OLD"})
    monkeypatch.setattr(grammar, "parser_for", forbidden)
    for demand in ("lexical", "structure"):
        result = request_parsing(semantic_writer_engine, root=root, text_product=text,
                                 demand=demand, code_commit="request-test")
        assert result.status == "source_ready"
        assert result.run_id != source_run and result.task_id != root.task_id
        with semantic_reader_engine.begin() as conn:
            products = select_layered_products(conn, run_id=result.run_id, rendition_id=rendition)
            assert {p.kind for p in products} == {"source", "text"}
            product = read_layered_product(conn, next(r for r in result.products if r.product_key == "text"))
            artifacts = [r["text_content"] for r in product.values()["representations"] if r["kind"] == "artifact"]
            assert any('"body":"OLD"' in a for a in artifacts)
            source = conn.execute(select(table("ops.run").c.sealed, table("ops.run").c.status).where(table("ops.run").c.id == source_run)).one()
            assert source.sealed and source.status == "consolidating"
            assert conn.scalar(select(func.count()).select_from(table("ops.task")).where(table("ops.task").c.run_id == source_run)) == 1


@pytest.mark.parametrize("demand", ["syntax", "interpretation"])
def test_native_syntax_request_does_not_interpret_or_construct_symbolic_values(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, monkeypatch, demand
):
    from corpus_structure.methods.math import grammar
    _, _, root, text, _ = source_build(semantic_db_engine, semantic_writer_engine, tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("syntax demand entered stronger work")
    if demand == "syntax":
        monkeypatch.setattr(grammar, "interpret", forbidden)
    monkeypatch.setattr(grammar._SymbolicResolver, "equivalent", forbidden)
    monkeypatch.setattr(grammar, "to_sympy", forbidden)
    result = request_parsing(semantic_writer_engine, root=root, text_product=text,
        demand=demand, math_index=0, code_commit="request-test")
    assert result.status == "source_ready", result.diagnostic
    assert all(p.product_key != "text" for p in result.products)
    assert result.inputs == (root, text)
    with semantic_reader_engine.begin() as conn:
        product = read_layered_product(conn, next(r for r in result.products if r.product_key == "math"))
        if demand == "syntax":
            assert product.values()["interpretations"] == []
            assert product.values()["semantic_state"] == "unknown"
        else:
            assert product.values()["interpretations"]


def test_native_symbolic_and_named_assessment_publish_new_immutable_products(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    _, _, root, text, rendition = source_build(semantic_db_engine, semantic_writer_engine, tmp_path, canonical="x/x")
    symbolic = request_parsing(semantic_writer_engine, root=root, text_product=text,
        demand="symbolic", start=0, end=3, code_commit="request-test")
    assert symbolic.status == "source_ready", symbolic.diagnostic
    assessed = request_parsing(semantic_writer_engine, root=root, text_product=text,
        demand="assessment", math_index=0, question="definedness", code_commit="request-test")
    assert assessed.status == "source_ready", assessed.diagnostic
    with semantic_reader_engine.begin() as conn:
        products = select_layered_products(conn, run_id=assessed.run_id, rendition_id=rendition)
        assert {p.kind for p in products} == {"source", "text", "interpretation", "assessment"}
        value = read_layered_product(conn, next(r for r in symbolic.products if r.product_key == "math")).values()
        details = json.loads(value["nodes"][0]["value"])
        assert details["native_evidence"]["text"] == "Integer(1)"
        assessment = read_layered_product(conn, next(r for r in assessed.products if r.product_key == "assessment")).values()
        details = json.loads(assessment["nodes"][0]["value"])
        assert details["question"] == "definedness"
        assert details["conditions"][0]["requirement"] == "nonzero"


def test_native_invalid_pin_and_selector_refuse_before_new_run(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    _, _, root, text, _ = source_build(semantic_db_engine, semantic_writer_engine, tmp_path)
    with semantic_writer_engine.connect() as conn:
        before = conn.scalar(select(func.count()).select_from(table("ops.run")))
    with pytest.raises(ParsingRequestUnavailable, match="math index"):
        request_parsing(semantic_writer_engine, root=root, text_product=text,
            demand="syntax", math_index=9, code_commit="request-test")
    with semantic_writer_engine.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(table("ops.run"))) == before


def test_native_cancelled_attempt_publishes_no_complete_products(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    _, source_run, root, text, _ = source_build(semantic_db_engine, semantic_writer_engine, tmp_path)
    def cancelled(*args, **kwargs):
        raise KeyboardInterrupt("cancelled request")
    monkeypatch.setattr("corpus_structure.semantic.parsing_requests._products", cancelled)
    with pytest.raises(KeyboardInterrupt):
        request_parsing(semantic_writer_engine, root=root, text_product=text,
            demand="lexical", code_commit="request-test")
    with semantic_writer_engine.connect() as conn:
        run = conn.execute(select(table("ops.run")).where(table("ops.run").c.id != source_run)).mappings().one()
        assert run["status"] == "cancelled"
        task = conn.execute(select(table("ops.task")).where(table("ops.task").c.run_id == run["id"])).mappings().one()
        assert task["status"] == "cancelled"
        assert conn.scalar(select(func.count()).select_from(table("ops.parsing_layer_product")).where(table("ops.parsing_layer_product").c.task_id == task["id"])) == 0


def test_native_failed_attempt_retains_failure_without_product_publication(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    _, _, root, text, _ = source_build(semantic_db_engine, semantic_writer_engine, tmp_path)
    def failed(*args, **kwargs):
        raise RuntimeError("injected producer failure")
    monkeypatch.setattr("corpus_structure.semantic.parsing_requests._products", failed)
    result = request_parsing(semantic_writer_engine, root=root, text_product=text,
        demand="lexical", code_commit="request-test")
    assert result.status == "failed" and result.products == ()
    with semantic_writer_engine.connect() as conn:
        assert conn.scalar(select(table("ops.task").c.status).where(table("ops.task").c.id == result.task_id)) == "failed"
        assert conn.scalar(select(func.count()).select_from(table("ops.parsing_layer_product")).where(table("ops.parsing_layer_product").c.task_id == result.task_id)) == 0


def test_native_historical_source_without_admitted_parsing_abi_requires_rebuild(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    from hashlib import sha256
    from .test_parsing_products import _native_build
    prepared = setup(semantic_db_engine, observations=True)
    with semantic_writer_engine.begin() as conn:
        _, task, _, _ = _native_build(conn, prepared, b"a\xc3\xa9 ", tmp_path)
    # Historical source builds do not have the new immutable products. Naming them cannot
    # authorize reinterpreting that build against today's execution schema or pack.
    unavailable = sha256(b"historical source lacks parsing products").hexdigest()
    with pytest.raises(ParsingRequestUnavailable) as refused:
        request_parsing(semantic_writer_engine, root=ProductReference(task, "source", unavailable),
            text_product=ProductReference(task, "text", unavailable), demand="lexical", code_commit="request-test")
    assert refused.value.reason == "rebuild_required"
    assert refused.value.rebuild_required


def test_native_request_uses_archived_fallback_after_current_configuration_changes(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, monkeypatch
):
    from corpus_structure.core.evidence import MacroDef
    from corpus_structure.methods.math.methods import MathSection
    _, _, root, text, _ = source_build(semantic_db_engine, semantic_writer_engine, tmp_path,
        canonical=r"\Archived", macros={r"\Archived": r"\mathbb{R}"})
    monkeypatch.setattr(MathSection, "macro_table", lambda self: {r"\Archived": MacroDef(body=r"\mathbb{Z}")})
    result = request_parsing(semantic_writer_engine, root=root, text_product=text,
        demand="symbolic", math_index=0, code_commit="request-test")
    assert result.status == "source_ready", result.diagnostic
    with semantic_reader_engine.begin() as conn:
        product = read_layered_product(conn, next(p for p in result.products if p.product_key == "math"))
        assert json.loads(product.values()["nodes"][0]["value"])["native_evidence"]["text"] == "Reals"


def test_native_cancellation_after_computation_fences_publication(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    from corpus_structure.semantic import parsing_requests
    from corpus_structure.semantic.operations import end_source_run
    _, _, root, text, _ = source_build(semantic_db_engine, semantic_writer_engine, tmp_path)
    actual = parsing_requests._products
    def cancelled_before_publication(*args, **kwargs):
        products = actual(*args, **kwargs)
        with semantic_writer_engine.begin() as conn:
            run_id = conn.scalar(select(table("ops.task").c.run_id).where(table("ops.task").c.id == kwargs["task_id"]))
            end_source_run(conn, run_id)
        return products
    monkeypatch.setattr(parsing_requests, "_products", cancelled_before_publication)
    result = request_parsing(semantic_writer_engine, root=root, text_product=text,
        demand="lexical", code_commit="request-test")
    assert result.status == "cancelled" and result.products == ()
    with semantic_writer_engine.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(table("ops.parsing_layer_product")).where(table("ops.parsing_layer_product").c.task_id == result.task_id)) == 0

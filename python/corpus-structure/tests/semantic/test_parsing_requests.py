"""On-demand parsing owns a real new native attempt over pinned archived products."""

from __future__ import annotations

import json

import pytest
from sqlalchemy import func, select

from corpus_structure.core.evidence import RenditionContent, Segment
from corpus_structure.core.vocab import SegmentKind
from corpus_structure.ingest.text_product import text_product_artifacts, text_product_payload
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    complete_task,
    create_run,
    create_task,
    record_method,
    register_document,
    seal_cut,
    store_rendition,
)
from corpus_structure.semantic.parsing_products import (
    PreparedParsingProductSet,
    ProductReference,
    prepare_layered_product,
    prepare_parsing_product,
    read_layered_product,
    select_layered_products,
    store_layered_products,
    store_parsing_product,
)
from corpus_structure.semantic.parsing_requests import ParsingRequestUnavailable, request_parsing

from .test_operations import setup


def source_build(admin, writer, tmp_path, *, canonical="x+x", macros=None, ranges=None):
    from types import SimpleNamespace

    from pydantic import create_model

    from corpus_structure.core.evidence import MacroDef

    prepared = setup(admin, observations=True, composed=True)
    from hashlib import sha256

    # Independently constructed source data exercises the retained layered-request ABI.
    # It is neither an HTML conversion nor a Docling/PDF qualification result.
    raw = canonical.encode()
    source = prepare_parsing_product(
        dict(
            recipe="source-products-v1",
            artifact_digest=sha256(raw).hexdigest(),
            lifecycle="available",
            semantic_state="ok",
            provenance_state="partial",
            representations=[
                dict(
                    representation_id="raw",
                    kind="original",
                    unit="byte",
                    extent_length=len(raw),
                    partition_state="complete",
                    recognition_state="complete",
                ),
                dict(
                    representation_id="canonical",
                    kind="canonical",
                    unit="codepoint",
                    extent_length=len(canonical),
                    text_content=canonical,
                    partition_state="complete",
                    recognition_state="complete",
                ),
            ],
            components=[
                dict(
                    component_id="r0",
                    representation_id="raw",
                    unit="byte",
                    start_offset=0,
                    end_offset=len(raw),
                    ordinal=0,
                    category="text",
                ),
                dict(
                    component_id="c0",
                    representation_id="canonical",
                    unit="codepoint",
                    start_offset=0,
                    end_offset=len(canonical),
                    ordinal=0,
                    category="math",
                ),
            ],
            nodes=[],
            relationships=[],
            endpoints=[],
            mappings=[
                dict(
                    mapping_id="source",
                    operation="decode",
                    fidelity="unknown",
                    reason="Independent fixture declares canonical text without an exact original-origin claim",
                )
            ],
            mapping_endpoints=[
                dict(
                    mapping_id="source",
                    side="source",
                    ordinal=0,
                    representation_id="raw",
                    unit="byte",
                    start_offset=0,
                    end_offset=len(raw),
                ),
                dict(
                    mapping_id="source",
                    side="target",
                    ordinal=0,
                    representation_id="canonical",
                    unit="codepoint",
                    start_offset=0,
                    end_offset=len(canonical),
                ),
            ],
        ),
        raw,
    )
    dependencies = canonical_bytes(
        {
            "operations": {
                "normalize.formula": {
                    "parameters": {"math": {"macros": macros or {}, "constants": []}}
                }
            }
        }
    )
    with writer.begin() as conn:
        run = create_run(
            conn,
            project_id="p",
            binding=OperationBinding(prepared.release_id, "z", 0, dependencies),
            kind="slice",
            options={},
            code_commit="request-fixture",
        )
        method = SimpleNamespace(
            name="ingest.fixture",
            version="1",
            family="ingest",
            tier="deterministic",
            confidence_source=None,
            unit_type="document",
            Config=create_model("SourceFixture"),
        )
        config = record_method(conn, method, "fixture", {}, "request-source-fixture")
        path = tmp_path / "source.txt"
        path.write_bytes(raw)
        doc = register_document(
            conn,
            project_id="p",
            source_uri="request-source",
            original_path=str(path),
            original=raw,
            mime="text/plain",
        )
        task = create_task(
            conn,
            run_id=run,
            config_id=config,
            stage="ingest",
            unit_type="document",
            unit_id=doc,
            input_hash="source-fixture",
            unit_key="source-fixture",
        )
        claim = claim_tasks(conn, run_id=run, config_id=config, holder="fixture")[0]
        content = RenditionContent(
            canonical_text=canonical,
            document=Segment(
                kind=SegmentKind.DOCUMENT,
                start=0,
                end=len(canonical),
                children=tuple(
                    Segment(kind=SegmentKind.MATH_INLINE, start=a, end=b)
                    for a, b in (ranges or [(0, len(canonical))])
                ),
            ),
        )
        rendition = store_rendition(
            conn,
            run_id=run,
            document_id=doc,
            content=content,
            task_id=task,
            config_id=config,
            parse_detail={},
            prepared=prepared,
        )
        store_parsing_product(
            conn, task_id=task, attempt=claim.attempt, holder="fixture", product=source
        )
        root = ProductReference(task, "source", source.digest)
        payload = text_product_payload(
            canonical,
            root=root.values(),
            math_ranges=[(a, b, None, None) for a, b in (ranges or [(0, len(canonical))])],
            fallback_macros={n: MacroDef(body=b) for n, b in (macros or {}).items()},
            fallback_source_ref="fixture:archived-math",
            structure=False,
        )
        text = prepare_layered_product(payload)
        refs = store_layered_products(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="fixture",
            products=PreparedParsingProductSet(
                (text,), required=("text",), artifacts=text_product_artifacts(payload)
            ),
        )
        complete_task(
            conn,
            task_id=task,
            attempt=claim.attempt,
            holder="fixture",
            prepared=prepared,
            observations=[],
            outcome="empty",
        )
        seal_cut(conn, run, "source", final=True)
    return prepared, run, root, refs[0], rendition


def test_native_weak_requests_use_pinned_inputs_and_leave_source_sealed(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, monkeypatch
):
    from corpus_structure.methods.math import grammar
    from corpus_structure.methods.math.prepared import PreparedMathInput

    def forbidden(*args, **kwargs):
        raise AssertionError("weak demand entered mathematical recognition")

    _, source_run, root, text, rendition = source_build(
        semantic_db_engine, semantic_writer_engine, tmp_path, macros={r"\archived": "OLD"}
    )
    for name in ("interpretation", "symbolic_reading", "symbolic_value", "assess"):
        monkeypatch.setattr(PreparedMathInput, name, forbidden)
    monkeypatch.setattr(grammar, "interpret", forbidden)
    for demand in ("lexical", "structure"):
        with monkeypatch.context() as demand_guard:
            if demand == "lexical":
                demand_guard.setattr(grammar, "parser_for", forbidden)
            result = request_parsing(
                semantic_writer_engine,
                root=root,
                text_product=text,
                demand=demand,
                code_commit="request-test",
            )
        assert result.status == "source_ready", result.diagnostic
        assert result.run_id != source_run and result.task_id != root.task_id
        with semantic_reader_engine.begin() as conn:
            products = select_layered_products(conn, run_id=result.run_id, rendition_id=rendition)
            assert {p.kind for p in products} == {"source", "text"}
            product = read_layered_product(
                conn, next(r for r in result.products if r.product_key == "text:" + demand)
            )
            assert product is not None
            views = [
                json.loads(node["value"])
                for node in product.values()["nodes"]
                if node["kind"] == "parse_view"
            ]
            assert [view["structure_outcome"] for view in views] == [
                "not_requested" if demand == "lexical" else "available"
            ]
            if demand == "structure":
                from copy import deepcopy

                from pydantic import ValidationError

                syntax = [node for node in product.values()["nodes"] if node["kind"] == "syntax"]
                assert [
                    (node["name"], node["start_offset"], node["end_offset"])
                    for node in syntax
                    if node["syntax_kind"] == "token"
                ] == [("x", 0, 1), ("+", 1, 2), ("x", 2, 3)]
                assert {node["grammar_revision"] for node in syntax} == {"sympy-1.14.0-lark-1.3.1"}
                assert {node["upstream_role"] for node in syntax} == {"content"}
                malformed = deepcopy(product.values())
                malformed["nodes"] = syntax
                malformed["nodes"][0].pop("syntax_kind")
                with pytest.raises(ValidationError, match="syntax_kind"):
                    prepare_layered_product(malformed)
                stale = deepcopy(product.values())
                next(node for node in stale["nodes"] if node["kind"] == "syntax")[
                    "grammar_revision"
                ] = "unqualified-grammar"
                with pytest.raises(ValueError, match="released frontend"):
                    prepare_layered_product(stale)
            artifacts = [
                r["text_content"]
                for r in product.values()["representations"]
                if r["kind"] == "artifact"
            ]
            assert any('"body":"OLD"' in a for a in artifacts)
            source = conn.execute(
                select(table("ops.run").c.sealed, table("ops.run").c.status).where(
                    table("ops.run").c.id == source_run
                )
            ).one()
            assert source.sealed and source.status == "consolidating"
            assert (
                conn.scalar(
                    select(func.count())
                    .select_from(table("ops.task"))
                    .where(table("ops.task").c.run_id == source_run)
                )
                == 1
            )


@pytest.mark.parametrize("demand", ["syntax", "interpretation"])
def test_native_syntax_request_does_not_interpret_or_construct_symbolic_values(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_reader_engine,
    tmp_path,
    monkeypatch,
    demand,
):
    from corpus_structure.methods.math import grammar

    _, _, root, text, _ = source_build(semantic_db_engine, semantic_writer_engine, tmp_path)

    def forbidden(*args, **kwargs):
        raise AssertionError("syntax demand entered stronger work")

    if demand == "syntax":
        monkeypatch.setattr(grammar, "interpret", forbidden)
    monkeypatch.setattr(grammar._SymbolicResolver, "equivalent", forbidden)
    monkeypatch.setattr(grammar, "to_sympy", forbidden)
    result = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand=demand,
        math_index=0,
        code_commit="request-test",
    )
    assert result.status == "source_ready", result.diagnostic
    assert all(p.product_key != "text" for p in result.products)
    assert result.inputs == (root, text)
    with semantic_reader_engine.begin() as conn:
        product = read_layered_product(
            conn, next(r for r in result.products if r.product_key == "math")
        )
        assert product is not None
        if demand == "syntax":
            assert product.values()["interpretations"] == []
            assert product.values()["semantic_state"] == "unknown"
        else:
            assert product.values()["interpretations"]


def test_native_symbolic_and_named_assessment_publish_new_immutable_products(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    _, _, root, text, rendition = source_build(
        semantic_db_engine, semantic_writer_engine, tmp_path, canonical="x/x"
    )
    symbolic = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand="symbolic",
        start=0,
        end=3,
        code_commit="request-test",
    )
    assert symbolic.status == "source_ready", symbolic.diagnostic
    assessed = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand="assessment",
        math_index=0,
        question="definedness",
        code_commit="request-test",
    )
    assert assessed.status == "source_ready", assessed.diagnostic
    with semantic_reader_engine.begin() as conn:
        products = select_layered_products(conn, run_id=assessed.run_id, rendition_id=rendition)
        assert {p.kind for p in products} == {"source", "text", "interpretation", "assessment"}
        product = read_layered_product(
            conn, next(r for r in symbolic.products if r.product_key == "math")
        )
        assert product is not None
        value = product.values()
        details = json.loads(value["nodes"][0]["value"])
        assert details["native_evidence"]["text"] == "Integer(1)"
        product = read_layered_product(
            conn, next(r for r in assessed.products if r.product_key == "assessment")
        )
        assert product is not None
        assessment = product.values()
        details = json.loads(assessment["nodes"][0]["value"])
        assert details["question"] == "definedness"
        assert details["conditions"][0]["requirement"] == "nonzero"


def test_native_request_uses_prior_source_definition_with_qualified_basis(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    _, _, root, text, _ = source_build(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path,
        canonical="f(t)=t^2 f(x)",
        ranges=[(0, 8), (9, 13)],
    )
    result = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand="interpretation",
        math_index=1,
        code_commit="request-source-definition",
    )
    assert result.status == "source_ready", result.diagnostic
    with semantic_reader_engine.begin() as conn:
        retained = read_layered_product(conn, result.products[0])
        assert retained is not None
        product = retained.values()
    assert product["semantic_state"] == "ok"
    basis = product["interpretations"][0]["declaration_basis"]
    assert len(basis) == 1
    declaration = basis[0]
    assert declaration["declaration"]["symbol"] == "f"
    assert declaration["declaration"]["role"] == "function"
    assert declaration["rule_id"] == "function-definition-1"
    assert (declaration["declaration_start"], declaration["declaration_end"]) == (0, 8)
    assert (declaration["head_start"], declaration["head_end"]) == (0, 4)
    assert declaration["source_view_node_id"] == "view:0"
    endpoints = [
        e for e in product["endpoints"] if e["relationship_id"] == declaration["relationship_id"]
    ]
    source = next(e for e in endpoints if e["role"] == "source")
    assert source["node_id"] == "view:0"
    assert source["target_task_id"] == text.task_id
    assert source["target_product_key"] == text.product_key
    assert source["target_content_digest"] == text.content_digest


def test_native_invalid_pin_and_selector_refuse_before_new_run(
    semantic_db_engine, semantic_writer_engine, tmp_path
):
    _, _, root, text, _ = source_build(semantic_db_engine, semantic_writer_engine, tmp_path)
    with semantic_writer_engine.connect() as conn:
        before = conn.scalar(select(func.count()).select_from(table("ops.run")))
    with pytest.raises(ParsingRequestUnavailable, match="math index"):
        request_parsing(
            semantic_writer_engine,
            root=root,
            text_product=text,
            demand="syntax",
            math_index=9,
            code_commit="request-test",
        )
    with semantic_writer_engine.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(table("ops.run"))) == before


def test_native_cancelled_attempt_publishes_no_complete_products(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    _, source_run, root, text, _ = source_build(
        semantic_db_engine, semantic_writer_engine, tmp_path
    )

    def cancelled(*args, **kwargs):
        raise KeyboardInterrupt("cancelled request")

    monkeypatch.setattr("corpus_structure.semantic.parsing_requests._products", cancelled)
    with pytest.raises(KeyboardInterrupt):
        request_parsing(
            semantic_writer_engine,
            root=root,
            text_product=text,
            demand="lexical",
            code_commit="request-test",
        )
    with semantic_writer_engine.connect() as conn:
        run = (
            conn.execute(select(table("ops.run")).where(table("ops.run").c.id != source_run))
            .mappings()
            .one()
        )
        assert run["status"] == "cancelled"
        task = (
            conn.execute(select(table("ops.task")).where(table("ops.task").c.run_id == run["id"]))
            .mappings()
            .one()
        )
        assert task["status"] == "cancelled"
        assert (
            conn.scalar(
                select(func.count())
                .select_from(table("ops.parsing_layer_product"))
                .where(table("ops.parsing_layer_product").c.task_id == task["id"])
            )
            == 0
        )


def test_native_failed_attempt_retains_failure_without_product_publication(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    _, _, root, text, _ = source_build(semantic_db_engine, semantic_writer_engine, tmp_path)

    def failed(*args, **kwargs):
        raise RuntimeError("injected producer failure")

    monkeypatch.setattr("corpus_structure.semantic.parsing_requests._products", failed)
    result = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand="lexical",
        code_commit="request-test",
    )
    assert result.status == "failed" and result.products == ()
    with semantic_writer_engine.connect() as conn:
        assert (
            conn.scalar(
                select(table("ops.task").c.status).where(table("ops.task").c.id == result.task_id)
            )
            == "failed"
        )
        assert (
            conn.scalar(
                select(func.count())
                .select_from(table("ops.parsing_layer_product"))
                .where(table("ops.parsing_layer_product").c.task_id == result.task_id)
            )
            == 0
        )


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
        request_parsing(
            semantic_writer_engine,
            root=ProductReference(task, "source", unavailable),
            text_product=ProductReference(task, "text", unavailable),
            demand="lexical",
            code_commit="request-test",
        )
    assert refused.value.reason == "rebuild_required"
    assert refused.value.rebuild_required


def test_native_request_uses_archived_fallback_after_current_configuration_changes(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, monkeypatch
):
    from corpus_structure.core.evidence import MacroDef
    from corpus_structure.methods.math.methods import MathSection

    _, _, root, text, _ = source_build(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path,
        canonical=r"\Archived",
        macros={r"\Archived": r"\mathbb{R}"},
    )
    monkeypatch.setattr(
        MathSection, "macro_table", lambda self: {r"\Archived": MacroDef(body=r"\mathbb{Z}")}
    )
    result = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand="symbolic",
        math_index=0,
        code_commit="request-test",
    )
    assert result.status == "source_ready", result.diagnostic
    with semantic_reader_engine.begin() as conn:
        product = read_layered_product(
            conn, next(p for p in result.products if p.product_key == "math")
        )
        assert product is not None
        assert (
            json.loads(product.values()["nodes"][0]["value"])["native_evidence"]["text"] == "Reals"
        )


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
            run_id = conn.scalar(
                select(table("ops.task").c.run_id).where(
                    table("ops.task").c.id == kwargs["task_id"]
                )
            )
            end_source_run(conn, run_id)
        return products

    monkeypatch.setattr(parsing_requests, "_products", cancelled_before_publication)
    result = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand="lexical",
        code_commit="request-test",
    )
    assert result.status == "cancelled" and result.products == ()
    with semantic_writer_engine.connect() as conn:
        assert (
            conn.scalar(
                select(func.count())
                .select_from(table("ops.parsing_layer_product"))
                .where(table("ops.parsing_layer_product").c.task_id == result.task_id)
            )
            == 0
        )


@pytest.mark.parametrize("demand", ["symbolic", "assessment"])
def test_native_identical_request_reuses_completed_products_without_kernel(
    semantic_db_engine,
    semantic_writer_engine,
    semantic_reader_engine,
    tmp_path,
    monkeypatch,
    demand,
):
    _, _, root, text, rendition = source_build(semantic_db_engine, semantic_writer_engine, tmp_path)
    first = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand=demand,
        question="definedness" if demand == "assessment" else None,
        math_index=0,
        code_commit="request-test",
    )
    assert first.status == "source_ready", first.diagnostic

    def forbidden(*args, **kwargs):
        raise AssertionError("identical request reran the kernel")

    monkeypatch.setattr("corpus_structure.semantic.parsing_requests._products", forbidden)
    second = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand=demand,
        question="definedness" if demand == "assessment" else None,
        math_index=0,
        code_commit="request-test",
    )
    assert second.status == "source_ready", second.diagnostic
    assert second.products == first.products
    assert second.run_id != first.run_id and second.task_id != first.task_id
    with semantic_reader_engine.begin() as conn:
        task = (
            conn.execute(select(table("ops.task")).where(table("ops.task").c.id == second.task_id))
            .mappings()
            .one()
        )
        assert task["status"] == "reused" and task["attempt"] == 0
        assert task["reused_task_id"] == first.task_id
        selected = select_layered_products(conn, run_id=second.run_id, rendition_id=rendition)
        assert (
            next(p.reference for p in selected if p.reference.product_key == "math")
            == first.products[0]
        )
        assert (
            conn.scalar(
                select(func.count())
                .select_from(table("ops.parsing_layer_product"))
                .where(table("ops.parsing_layer_product").c.task_id == second.task_id)
            )
            == 0
        )


def test_native_time_budget_changes_request_identity_and_reaches_kernel(
    semantic_db_engine, semantic_writer_engine, tmp_path, monkeypatch
):
    from corpus_structure.semantic import parsing_requests

    _, _, root, text, _ = source_build(semantic_db_engine, semantic_writer_engine, tmp_path)
    actual = parsing_requests._products
    budgets = []

    def observed(config, *args, **kwargs):
        budgets.append(config.seconds)
        return actual(config, *args, **kwargs)

    monkeypatch.setattr(parsing_requests, "_products", observed)
    first = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand="syntax",
        math_index=0,
        seconds=10.0,
        code_commit="request-test",
    )
    second = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand="syntax",
        math_index=0,
        seconds=20.0,
        code_commit="request-test",
    )
    assert first.status == second.status == "source_ready"
    assert budgets == [10.0, 20.0]
    with semantic_writer_engine.connect() as conn:
        task = (
            conn.execute(select(table("ops.task")).where(table("ops.task").c.id == second.task_id))
            .mappings()
            .one()
        )
        assert task["reused_task_id"] is None


def test_native_raw_lexical_request_never_expands_macros_or_calls_native_structure(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, monkeypatch
):
    from pylatexenc.latexwalker import LatexWalker

    _, _, root, text, rendition = source_build(
        semantic_db_engine,
        semantic_writer_engine,
        tmp_path,
        canonical=r"\Archived",
        macros={r"\Archived": r"\mathbb{R}"},
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("raw lexical request performed stronger work")

    monkeypatch.setattr("corpus_structure.core.text_structure.expand", forbidden)
    monkeypatch.setattr(LatexWalker, "parse_content", forbidden)
    result = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand="lexical",
        code_commit="request-test",
    )
    assert result.status == "source_ready", result.diagnostic
    assert [p.product_key for p in result.products] == ["text:lexical"]
    with semantic_reader_engine.begin() as conn:
        retained = read_layered_product(conn, result.products[0])
        assert retained is not None
        payload = retained.values()
        assert not any(r["kind"] == "expanded" for r in payload["representations"])
        assert not any(n["kind"] == "macro_invocation" for n in payload["nodes"])
        selected = select_layered_products(conn, run_id=result.run_id, rendition_id=rendition)
        assert {p.reference.product_key for p in selected} == {"source", "text", "text:lexical"}


@pytest.mark.parametrize("seconds", [0.0, -1.0, float("inf"), float("nan")])
def test_request_budget_is_positive_and_finite(seconds):
    from pydantic import ValidationError

    from corpus_structure.semantic.parsing_requests import ParsingRequestConfig

    with pytest.raises(ValidationError):
        ParsingRequestConfig(root={}, text_product={}, demand="syntax", seconds=seconds)


def test_native_timeout_attempts_are_not_reused_and_larger_budget_retries(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    _, _, root, text, _ = source_build(
        semantic_db_engine, semantic_writer_engine, tmp_path, canonical="+".join(["x"] * 30)
    )
    first = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand="syntax",
        math_index=0,
        seconds=0.0001,
        code_commit="request-test",
    )
    assert first.status == "failed", first.diagnostic
    second = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand="syntax",
        math_index=0,
        seconds=0.0001,
        code_commit="request-test",
    )
    assert second.status == "failed", second.diagnostic
    with semantic_reader_engine.begin() as conn:
        for result in (first, second):
            task = (
                conn.execute(
                    select(table("ops.task")).where(table("ops.task").c.id == result.task_id)
                )
                .mappings()
                .one()
            )
            assert task["status"] == "failed" and task["attempt"] == 1
            assert task["reused_task_id"] is None
            retained = read_layered_product(conn, result.products[0])
            assert retained is not None
            product = retained.values()
            assert product["lifecycle"] == "failed" and product["coverage"] == "partial"
            assert json.loads(product["nodes"][0]["value"])["failure"]["category"] == "timeout"
    retried = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand="syntax",
        math_index=0,
        seconds=10.0,
        code_commit="request-test",
    )
    assert retried.status == "source_ready", retried.diagnostic


def test_native_assessment_request_stops_at_timed_out_interpretation(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path, monkeypatch
):
    from corpus_structure.methods.math.prepared import PreparedMathInput

    _, _, root, text, _ = source_build(
        semantic_db_engine, semantic_writer_engine, tmp_path, canonical="+".join(["x"] * 30)
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("failed interpretation retried through assessment")

    monkeypatch.setattr(PreparedMathInput, "assess", forbidden)
    result = request_parsing(
        semantic_writer_engine,
        root=root,
        text_product=text,
        demand="assessment",
        question="definedness",
        math_index=0,
        seconds=0.0001,
        code_commit="request-test",
    )
    assert result.status == "failed", result.diagnostic
    assert [p.product_key for p in result.products] == ["math"]
    with semantic_reader_engine.begin() as conn:
        retained = read_layered_product(conn, result.products[0])
        assert retained is not None
        product = retained.values()
        assert product["lifecycle"] == "failed" and product["semantic_state"] == "unknown"

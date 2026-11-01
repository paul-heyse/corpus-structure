"""Database-free admission controls for exact selected or claimed candidate custody."""

from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.semantic.operations import BoundReader, OperationConflict
from corpus_structure.semantic.product_reference import ProductReference


class Result:
    def __init__(self, value):
        self.value = value

    def mappings(self):
        return self

    def one(self):
        return self.value

    def scalar_one(self):
        return self.value

    def __iter__(self):
        return iter(self.value)


def reader_fixture(monkeypatch, *, selected=False, claim_change=None, product_change=None):
    from corpus_structure.semantic import pdf_contracts, source_views

    pin = ProductReference(11, "organized", "a" * 64)
    row = dict(
        payload=None,
        contract_digest="contract",
        schema_digest="schema",
        recipe_digest="recipe",
        product_kind="native",
        original_digest="original",
    )
    row.update(product_change or {})
    claim = dict(
        params={"native_product": pin.values()}, content_hash="original", project_id="project"
    )
    claim.update(claim_change or {})
    results = [row, [claim], "project", "project"]

    def execute(statement):
        assert results, "capture performed an unexpected database operation"
        return Result(results.pop(0))

    required = []
    context = SimpleNamespace(
        contract_digest="contract",
        execution=SimpleNamespace(require_operation=required.append),
    )
    monkeypatch.setattr(pdf_contracts, "pdf_context_for_task", lambda conn, task: context)
    monkeypatch.setattr(
        pdf_contracts,
        "pdf_context_for_release",
        lambda conn, prepared: SimpleNamespace(native_schema_digest="schema"),
    )
    monkeypatch.setattr(
        source_views,
        "selected_source_views",
        lambda conn, run: (SimpleNamespace(native_product=pin),) if selected else (),
    )
    reader: Any = object.__new__(BoundReader)
    reader.conn = SimpleNamespace(execute=execute)
    reader.run_id = 22
    reader.prepared = SimpleNamespace()
    reader.source_tasks = {3: 44}
    return reader, pin, context, results, required


def test_exact_claimed_input_captures_ipc_without_selected_views_or_native_hydration(
    tmp_path, monkeypatch
):
    from corpus_structure.semantic import pdf_payloads, pdf_record_reader

    family = pdf_payloads.prepare_payload_family()
    page = dict(page_no=7, has_words=True, has_chars=False, candidates=[])
    encoded = pdf_payloads.EncodedPagePayload(
        family.encode(page), family.schema_digest, family.logical_digest(page), 7
    )
    reader, pin, context, pending, required = reader_fixture(monkeypatch)

    def payloads(*, context):
        assert context is expected_context
        yield encoded

    expected_context = context
    monkeypatch.setattr(
        pdf_record_reader,
        "published_record_reader",
        lambda conn, reference: SimpleNamespace(iter_candidate_payloads=payloads),
    )

    def prepare(actual):
        assert actual is context
        return family

    monkeypatch.setattr(pdf_payloads, "prepare_payload_family", prepare)
    source = reader.capture_pdf_candidates(pin, tmp_path / "capture")
    assert not pending
    assert required == ["publish_native_document"]
    assert source.encoded(7) == encoded
    assert source.replays[7].path.read_bytes() == encoded.content


@pytest.mark.parametrize(
    "change, product, match",
    [
        (
            {"params": {"native_product": ProductReference(11, "organized", "b" * 64).values()}},
            {},
            "exact claimed",
        ),
        ({"content_hash": "other-original"}, {}, "exact claimed"),
        ({"project_id": "other-project"}, {}, "exact claimed"),
        ({}, {"product_kind": "integrated"}, "native input role"),
        ({}, {"contract_digest": "other-contract"}, "archived contract"),
        ({}, {"schema_digest": "other-schema"}, "consumer does not admit"),
    ],
)
def test_claim_capture_refuses_wrong_pin_original_project_role_or_release(
    tmp_path, monkeypatch, change, product, match
):
    reader, pin, _, _, _ = reader_fixture(monkeypatch, claim_change=change, product_change=product)
    with pytest.raises(OperationConflict, match=match):
        reader.capture_pdf_candidates(pin, tmp_path / "capture")
    assert not (tmp_path / "capture").exists()


def test_selected_pin_keeps_existing_authority_when_no_claim_declares_it(monkeypatch):
    reader, pin, context, pending, required = reader_fixture(
        monkeypatch, selected=True, claim_change={"params": {}}
    )
    _, admitted = reader._native_product_input(pin)
    assert admitted is context and not pending
    assert required == ["publish_native_document"]

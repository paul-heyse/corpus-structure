"""Actual retained mathematical semantics under an explicit semantic source binding."""

import pytest

from corpus_structure.methods.math import grammar
from corpus_structure.methods.math.declared import declared_math_readings, selected_formula_inputs
from corpus_structure.methods.math.methods import ExtractMathConfig
from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context
from corpus_structure.semantic.data_operation_model import BoundRoleMember, SubjectContext
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.formal_products import FormalEvidenceOptions
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.source_products import source_subject
from semantic.formal_products_support import profile as profile
from semantic.formal_products_support import selected


def _standalone_context(_source_release, **values):
    # Independent kernel qualification only. A target mathematical producer must
    # supply its separately admitted profile; no legacy execution rows are added
    # to this source/formal archive to make it an analysis authority.
    return prepare_interpretation_context(None, **values)


def _source(profile, *, clipped=False):
    latex, text = "2+1", "  2+1"
    source = selected(
        profile,
        text,
        pieces=[
            dict(kind="synthetic_separator", start=0, end=2),
            dict(kind="native_text", start=2, end=5, item_ref="#/texts/0", source_field="text"),
        ],
        items=[dict(self_ref="#/texts/0", label="formula", text=latex, orig=latex)],
        recognition=[dict(pointer="#/texts/0", outcome="succeeded")],
        selectors=[dict(projection="b"*64, native_pointer="#/texts/0", start=2, end=4 if clipped else 5)],
    )
    member = BoundRoleMember(
        "product:selected-math", "kind:selected-source", source_subject(source.value["source"]),
        source.value["source"]["document"], canonical_bytes({"selectors": source.value["selectors"]}),
        b"{}", (), b"{}", member="source:formula",
    )
    return source, DeclaredNativeFrameSource.acquire(profile.prepared, source.value, member, project="nonstatistics")


def test_declared_math_uses_original_positions_semantic_source_and_retained_primary(profile, monkeypatch):
    source, frame = _source(profile)
    product = profile.run(source, FormalEvidenceOptions(), subject_context=SubjectContext("nonstatistics", frame.pin.values()["subject"], frame.original_key, canonical_bytes({"selectors": source.value["selectors"]})))

    def refuse_parse(*args, **kwargs):
        pytest.fail("mathematical consumer repeated primary recognition")

    monkeypatch.setattr(grammar, "syntax", refuse_parse)
    monkeypatch.setattr(grammar, "syntax_forest", refuse_parse)
    (reading,) = declared_math_readings(frame, (product,), ExtractMathConfig(), prepared=profile.prepared, prepare_context=_standalone_context)
    assert reading.pointer == "#/texts/0" and reading.projected_start == 2
    assert reading.result.status.value == "ok"
    assert str(reading.prepared.symbolic_value()) == "3"
    assert reading.prepared.context.source_id == frame.source_key
    assert reading.prepared.source_text == "2+1"
    assert reading.prepared._primary_input["product_id"] == product.semantic_id


def test_declared_math_clipped_formula_is_unexamined_not_inspected_empty(profile):
    source, frame = _source(profile, clipped=True)
    selected_inputs, unexamined = selected_formula_inputs(source)
    assert selected_inputs == frozenset()
    assert unexamined == frozenset({"#/texts/0"})
    assert declared_math_readings(frame, (), ExtractMathConfig(), prepared=profile.prepared, prepare_context=_standalone_context) == ()

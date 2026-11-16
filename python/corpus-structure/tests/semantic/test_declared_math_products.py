"""Current math producer/consumer semantics without legacy execution admission."""

from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import JsonValue

from corpus_structure.methods.math.declared import (
    DeclaredMathNormalization,
    DeclaredMathOccurrences,
)
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.data_operation_model import (
    BoundRoleMember,
    ResolvedRoleBinding,
    SubjectContext,
)
from corpus_structure.semantic.declared_math_products import (
    DeclaredMathOptions,
    DeclaredMathProduct,
    PreparedMathInputs,
    acquire_analysis_context_profile,
    math_operation_declarations,
    math_operation_sources,
)
from corpus_structure.semantic.formal_products import (
    FormalEvidenceOptions,
    formal_operation_sources,
    prepare_formal_evidence,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.source_products import source_subject
from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies
from semantic.formal_products_support import selected


@pytest.fixture(scope="module")
def math_profile():
    from corpus_structure.semantic.formal_evidence import grammar_identity

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    from corpus_structure.semantic.characterization_ports import characterization_operation_sources
    from corpus_structure.semantic.construction_products import construction_product_inputs

    bundle = construction_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    captured = combine_primary_sources(
        formal_operation_sources(), math_operation_sources(), characterization_operation_sources()
    )
    dependencies = data_operation_dependencies(
        ResolvedDependencies(), (math_operation_declarations(),), captured
    )
    prepared = prepare_release(bundle, dependencies, PreparationProfile(version="semantic-2"))
    model = bound_data_operation_model(prepared)
    return prepare_formal_evidence(prepared, model, grammar=grammar_identity())


def _inputs(profile):
    source = selected(
        profile,
        "  2+1",
        pieces=[
            dict(kind="synthetic_separator", start=0, end=2),
            dict(kind="native_text", start=2, end=5, item_ref="#/texts/0", source_field="text"),
        ],
        items=[dict(self_ref="#/texts/0", label="formula", text="2+1", orig="2+1")],
        recognition=[dict(pointer="#/texts/0", outcome="succeeded")],
        selectors=[dict(projection="b" * 64, native_pointer="#/texts/0", start=2, end=5)],
    )
    context = SubjectContext(
        "outside-statistics",
        source_subject(source.value["source"]),
        source.value["source"]["document"],
        canonical_bytes({"selectors": source.value["selectors"]}),
        subject_definition="original-source-view",
    )
    formal = profile.run(source, FormalEvidenceOptions(), subject_context=context)
    source_member = BoundRoleMember(
        "product:source",
        "kind:source",
        context.subject,
        context.original_source,
        context.analyzed_scope,
        b"{}",
        (),
        b"{}",
        member="selected",
        subject_definition="original-source-view",
        support_references=(),
    )
    formal_member = replace(
        source_member, product=formal.semantic_id, member=None, kind_contract="kind:formal"
    )
    return source, formal, source_member, formal_member


def _role(name, members):
    return ResolvedRoleBinding(name, "present" if members else "known-absent", tuple(members))


def test_math_profiles_compile_without_a_legacy_execution_binding(math_profile):
    prepared = math_profile.prepared
    model = bound_data_operation_model(prepared)
    assert {"extract.math/declared", "normalize.formula/declared"} <= {
        op.semantic_id for op in model.operations
    }
    assert (
        model.operation("normalize.formula/declared").roles[1].kind
        == "urn:corpus:math:DeclaredMathOccurrenceProduct"
    )


def test_occurrence_and_normalization_consume_exact_retained_syntax(math_profile, monkeypatch):
    from corpus_structure.methods.math import grammar

    source, formal, source_member, formal_member = _inputs(math_profile)
    roles = (
        _role("source", (source_member,)),
        _role("formal", (formal_member,)),
        _role("inherited", ()),
        _role("ancestor_sources", ()),
    )
    profile = PreparedMathInputs(
        math_profile.prepared,
        roles,
        "outside-statistics",
        DeclaredMathOptions(),
        acquire_analysis_context_profile(),
        lambda: None,
    )

    def refuse_parse(*args, **kwargs):
        pytest.fail("a mathematical consumer reparsed retained primary syntax")

    monkeypatch.setattr(grammar, "syntax", refuse_parse)
    monkeypatch.setattr(grammar, "syntax_forest", refuse_parse)
    actual = DeclaredMathOccurrences(profile).run(
        source.value, formal.value.model_dump(mode="json", exclude_unset=True)
    )
    product = DeclaredMathProduct.model_validate(actual)
    assert product.phase == "occurrences" and product.outcome == "complete"
    assert product.source.source_product == "product:source"
    assert product.items[0]["pointer"] == "#/texts/0"
    assert product.items[0]["recognized_latex"] == "2+1"
    primary = product.items[0]["primary_input"]
    assert isinstance(primary, dict) and primary["product_id"] == formal.semantic_id
    occurrence_member = replace(
        formal_member, product="product:occurrences", kind_contract="kind:math"
    )
    normalizer = replace(
        profile,
        roles=(_role("source", (source_member,)), _role("occurrences", (occurrence_member,))),
    )
    result = DeclaredMathProduct.model_validate(
        DeclaredMathNormalization(normalizer).run(source.value, actual)
    )
    assert result.phase == "symbolic"
    assert result.occurrence_input is not None
    assert result.occurrence_input is not None
    assert result.occurrence_input.product_id == "product:occurrences"
    assert result.items[0]["symbolic"] == {"format": "sympy-srepr-1", "expression": "Integer(3)"}
    changed = {**actual, "source": {**actual["source"], "membership": "direct"}}
    with pytest.raises(ValueError, match="exact selected source"):
        DeclaredMathNormalization(normalizer).run(source.value, changed)
    changed = {**actual, "items": [{**actual["items"][0], "occurrence_basis": "wrong"}]}
    with pytest.raises(ValueError, match="normalization context"):
        DeclaredMathNormalization(normalizer).run(source.value, changed)


def test_symbol_scope_retains_unavailable_binder_coverage_and_exact_math_inputs(
    math_profile, monkeypatch
):
    from corpus_structure.methods.math.declared import DeclaredMathScope
    from corpus_structure.semantic.construction_products import (
        ConstructionOptions,
        PreparedConstructionProfile,
    )
    from corpus_structure.semantic.constructions.math_scope import Binders

    source, formal, source_member, formal_member = _inputs(math_profile)
    binders = Binders(sentence_initial=("suppose",))
    context = SubjectContext(
        "outside-statistics",
        source_member.subject,
        source_member.original_source,
        source_member.analyzed_scope,
        subject_definition=source_member.subject_definition,
    )
    model = bound_data_operation_model(math_profile.prepared)
    construction = PreparedConstructionProfile(math_profile.prepared, model).run(
        source, (formal,), ConstructionOptions(math_scope_binders=binders), subject_context=context
    )
    profile = PreparedMathInputs(
        math_profile.prepared,
        (
            _role("source", (source_member,)),
            _role("formal", (formal_member,)),
            _role("inherited", ()),
            _role("ancestor_sources", ()),
        ),
        "outside-statistics",
        DeclaredMathOptions(math_scope_binders=binders),
        acquire_analysis_context_profile(),
        lambda: None,
    )
    original = DeclaredMathOccurrences(profile).run(
        source.value, formal.value.model_dump(mode="json", exclude_unset=True)
    )
    occurrence_member = replace(
        formal_member, product="product:occurrences", kind_contract="kind:math"
    )
    normalizer = replace(
        profile,
        roles=(_role("source", (source_member,)), _role("occurrences", (occurrence_member,))),
    )
    symbolic = DeclaredMathNormalization(normalizer).run(source.value, original)
    scope_profile = replace(
        profile,
        roles=(
            _role("source", (source_member,)),
            _role("occurrences", (occurrence_member,)),
            _role("symbolic", (replace(occurrence_member, product="product:symbolic"),)),
            _role("constructions", (replace(formal_member, product=construction.semantic_id),)),
            _role("inherited", ()),
            _role("ancestor_sources", ()),
        ),
    )
    from corpus_structure.methods.math import grammar

    monkeypatch.setattr(
        grammar, "syntax", lambda *_a, **_kw: pytest.fail("scope reparsed primary syntax")
    )
    result = DeclaredMathProduct.model_validate(
        DeclaredMathScope(scope_profile).run(
            source.value,
            original,
            symbolic,
            construction.value.model_dump(mode="json", exclude_unset=True),
        )
    )
    assert result.phase == "scope" and result.outcome == "partial"
    assert "retained source binder coverage unavailable or incomplete" in result.issues
    assert result.items == ()
    assert result.occurrence_input is not None
    assert result.occurrence_input.product_id == "product:occurrences"
    assert result.symbolic_input is not None
    assert result.symbolic_input.product_id == "product:symbolic"
    substituted = {
        **symbolic,
        "occurrence_input": {**symbolic["occurrence_input"], "product_id": "product:other"},
    }
    with pytest.raises(ValueError, match="correspondence"):
        DeclaredMathScope(scope_profile).run(
            source.value,
            original,
            substituted,
            construction.value.model_dump(mode="json", exclude_unset=True),
        )


def test_symbol_scope_uses_retained_cues_forward_and_preserves_original_formula_offsets(
    math_profile, monkeypatch
):
    """Independent retained-cue fixture; this is pure scope evidence, not NLP inference."""
    from corpus_structure.methods.math.declared import DeclaredMathScope
    from corpus_structure.semantic.constructions.math_scope import FAMILY, Binders, policy_identity
    from corpus_structure.semantic.constructions.nodes import identity

    parts = (
        ("formula", "x+1"),
        ("text", ". Suppose "),
        ("formula", "x=2"),
        ("text", ". "),
        ("formula", "x+1"),
        ("text", "."),
    )
    text = "".join(value for _, value in parts)
    items, pieces, recognition = [], [], []
    offset = 0
    for index, (label, value) in enumerate(parts):
        pointer = "#/texts/" + str(index)
        items.append(dict(self_ref=pointer, label=label, text=value, orig=value))
        pieces.append(
            dict(
                kind="native_text",
                start=offset,
                end=offset + len(value),
                item_ref=pointer,
                source_field="text",
            )
        )
        offset += len(value)
        if label == "formula":
            recognition.append(dict(pointer=pointer, outcome="succeeded"))
    source = selected(
        math_profile,
        text,
        items=items,
        pieces=pieces,
        recognition=recognition,
        selectors=[dict(projection="b" * 64, start=0, end=len(text))],
    )
    context = SubjectContext(
        "outside-statistics",
        source_subject(source.value["source"]),
        source.value["source"]["document"],
        canonical_bytes({"selectors": source.value["selectors"]}),
        subject_definition="original-source-view",
    )
    formal = math_profile.run(source, FormalEvidenceOptions(), subject_context=context)
    pin = BoundRoleMember(
        "product:source",
        "kind:source",
        context.subject,
        context.original_source,
        context.analyzed_scope,
        b"{}",
        (),
        b"{}",
        member="selected",
        subject_definition="original-source-view",
        support_references=(),
    )
    formal_pin = replace(pin, product=formal.semantic_id, member=None, kind_contract="kind:formal")
    binders = Binders(sentence_initial=("suppose",))
    profile = PreparedMathInputs(
        math_profile.prepared,
        (
            _role("source", (pin,)),
            _role("formal", (formal_pin,)),
            _role("inherited", ()),
            _role("ancestor_sources", ()),
        ),
        context.project_id,
        DeclaredMathOptions(math_scope_binders=binders),
        acquire_analysis_context_profile(),
        lambda: None,
    )
    original = DeclaredMathOccurrences(profile).run(
        source.value, formal.value.model_dump(mode="json", exclude_unset=True)
    )
    occurrence_pin = replace(formal_pin, product="product:occurrences", kind_contract="kind:math")
    symbolic = DeclaredMathNormalization(
        replace(profile, roles=(_role("source", (pin,)), _role("occurrences", (occurrence_pin,))))
    ).run(source.value, original)
    projection = source.value["source"]["projection"]
    policy = policy_identity(binders, ())
    # Every cue has exact literal support; the independent fixture declares only
    # the middle sentence as a binder and supplies complete examined coverage.
    extents = {"all": (0, len(text)), "sentence": (5, 17), "initial": (5, 12)}
    members: list[dict[str, JsonValue]] = []
    for name, (start, end) in extents.items():
        members.append(
            {
                "body": {
                    "record_type": "occurrence",
                    "local_id": name,
                    "extents": [
                        {
                            "projection": projection,
                            "native_pointer": piece["item_ref"],
                            "start": max(start, piece["start"]),
                            "end": min(end, piece["end"]),
                            "text": text[max(start, piece["start"]) : min(end, piece["end"])],
                        }
                        for piece in pieces
                        if piece["start"] < end and start < piece["end"]
                    ],
                }
            }
        )
    for name, kind, occurrence in (
        ("policy", "scope_policy", "all"),
        ("sentence", "scope_sentence", "sentence"),
        ("initial", "scope_initial", "initial"),
    ):
        members.append(
            {
                "body": {
                    "record_type": "annotation",
                    "local_id": "a:" + name,
                    "kind": "math." + kind,
                    "family": FAMILY,
                    "rule_id": identity("math-source-sentences", [])
                    if name == "sentence"
                    else policy,
                    "occurrences": [occurrence],
                }
            }
        )
    members.append(
        {
            "body": {
                "record_type": "membership",
                "local_id": "m:sentence",
                "group": "a:initial",
                "role": "sentence",
                "member": "a:sentence",
            }
        }
    )
    cues = {
        "source": source.value["source"],
        "selectors": source.value["selectors"],
        "members": members,
        "coverage": [
            {
                "family": FAMILY,
                "availability": "available",
                "outcome": "complete",
                "examined": [{"projection": projection, "start": 0, "end": len(text)}],
                "unexamined": [],
            }
        ],
    }
    scope_profile = replace(
        profile,
        roles=(
            _role("source", (pin,)),
            _role("occurrences", (occurrence_pin,)),
            _role("symbolic", (replace(occurrence_pin, product="product:symbolic"),)),
            _role("constructions", (replace(formal_pin, product="product:cues"),)),
            _role("inherited", ()),
            _role("ancestor_sources", ()),
        ),
    )
    from corpus_structure.methods.math import grammar

    monkeypatch.setattr(
        grammar, "syntax", lambda *_a, **_kw: pytest.fail("scope reparsed primary syntax")
    )
    actual = DeclaredMathScope(scope_profile).run(source.value, original, symbolic, cues)
    assert [
        (row["pointer"], row["recognized_start"], row["recognized_end"], row["outcome"])
        for row in actual["items"]
    ] == [
        ("#/texts/0", 0, 1, "unresolved"),
        ("#/texts/2", 0, 1, "resolved"),
        ("#/texts/4", 0, 1, "resolved"),
    ]
    for row in actual["items"][1:]:
        assert row["binding_pointer"] == "#/texts/2" and row["binding_start"] == 0
        assert row["binding_input"]["product_id"] == "product:occurrences"
        assert row["binding_source"]["source_product"] == "product:source"
    assert actual["outcome"] == "partial"
    assert "task_id" not in canonical_bytes(actual).decode()


def test_selected_math_checks_the_complete_source_address(math_profile):
    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.declared_record_sources import DeclaredRecordSource
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.serve.selected_math import _source_for_interpretation

    source, _, member, _ = _inputs(math_profile)
    pin = DeclaredStructuralSource.model_validate(
        DeclaredRecordSource.from_bound(
            source,
            member,
            project="outside-statistics",
        ).pin()
    )
    row = dict(
        kind_contract=member.kind_contract,
        subject=member.subject,
        subject_definition=member.subject_definition,
        original_source=member.original_source,
        analyzed_scope={"selectors": source.value["selectors"]},
        body=semantic_value(source.value),
    )
    products = {member.product: {"project_id": "outside-statistics"}}
    members = {(member.product, member.member): row}
    actual = _source_for_interpretation(math_profile.prepared, pin, products, members)
    assert actual.value["source"]["document"] == "document:original-content"
    assert actual.value["source"]["section_pointer"] == "#/groups/0"
    # Equal projected atoms do not establish document, subject or coordinate identity.
    for changes in (
        {"project_id": "another-project"},
        {"subject": "another-subject"},
        {"subject_definition": "another-definition"},
        {"kind_contract": "another-kind"},
        {"section_pointer": "#/groups/99"},
        {"membership": "direct"},
        {"analyzed_scope_meaning": "another-scope"},
        {"document": "another-document", "original_source": "another-document"},
    ):
        changed = pin.model_copy(update=changes)
        with pytest.raises(ValueError, match="admitted context or coordinate"):
            _source_for_interpretation(math_profile.prepared, changed, products, members)
    with pytest.raises(ValueError, match="outside its admitted closure"):
        _source_for_interpretation(math_profile.prepared, pin, products, {})

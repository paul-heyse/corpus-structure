"""Independent positions and domain outcomes for retained positioned formal syntax."""

from hashlib import sha256
from typing import Any, cast

import pytest
from lark.exceptions import VisitError

from corpus_structure.core.vocab import ParseOutcome
from corpus_structure.methods.math import grammar as math_grammar
from corpus_structure.semantic.characterization import (
    decode_layer,
    encode_layer,
)
from corpus_structure.semantic.formal_evidence import (
    build_formal_layer,
    decimal_value,
    nominate_fields,
)
from corpus_structure.semantic.structural_parsing import parse_comparison_literal, parse_threshold
from semantic.primary_formal_fixture import (
    operation as operation,
)
from semantic.primary_formal_fixture import (
    prepared as prepared,
)
from semantic.primary_formal_fixture import (
    source as source,
)


@pytest.mark.parametrize("health", ["succeeded", "failed"])
def test_unprojected_native_formula_retains_recognition_without_literal_claim(prepared, health):
    view = source(("", "formula", "x+1", health))
    layer = build_formal_layer(view, prepared, operation())
    (recognized,) = [
        row
        for row in layer.payload["annotations"]
        if row.get("formal_input", {}).get("representation") == "recognized_latex"
    ]
    assert recognized["formal_input"]["text"] == "x+1"
    assert recognized["formal_input"]["syntax_outcome"] == (
        "complete" if health == "succeeded" else "failed"
    )
    assert recognized["formal_input"]["correspondence"][0]["relation"] == "contained_in_atom"
    assert all(
        extent["native_pointer"] == "#/texts/0" and "start" not in extent and "text" not in extent
        for row in layer.payload["occurrences"]
        for extent in row["extents"]
    )
    coverage = {row["family"]: row for row in layer.payload["coverage"]}
    assert coverage["formal.math"]["outcome"] == "partial"
    assert "source-character correspondence" in coverage["formal.math"]["reason"]
    assert all(
        row["outcome"] == "empty" for family, row in coverage.items() if family != "formal.math"
    )
    assert any(row["kind"] == "formal.symbol" for row in layer.payload["annotations"]) == (
        health == "succeeded"
    )


def report(prepared, text):
    return build_formal_layer(source((text, "text", "", "")), prepared, operation())


def roots(layer, family, representation=None):
    return [
        annotation
        for annotation in layer.payload["annotations"]
        if annotation["family"] == family
        and "formal_input" in annotation
        and (
            representation is None or annotation["formal_input"]["representation"] == representation
        )
    ]


def normalized(layer, family):
    return [
        annotation["formal"]["normalized"]
        for annotation in layer.payload["annotations"]
        if annotation["family"] == family and "normalized" in annotation.get("formal", {})
    ]


def extents(layer, annotation):
    values = {item["local_id"]: item["extents"] for item in layer.payload["occurrences"]}
    return [extent for occurrence in annotation["occurrences"] for extent in values[occurrence]]


def test_examined_nomination_is_independent_of_zero_recognized_fields(prepared):
    nomination = nominate_fields("α\t prose\n")  # noqa: RUF001 - deliberate Greek source text
    assert (nomination.examined_start, nomination.examined_end) == (0, 9)
    assert nomination.candidates == ()
    layer = report(prepared, "α\t prose\n")  # noqa: RUF001 - deliberate Greek source text
    for coverage in layer.payload["coverage"]:
        assert (
            coverage["eligible"]
            == coverage["examined"]
            == [dict(projection="b" * 64, native_pointer="#/texts/0", start=0, end=9)]
        )
        if coverage["family"] != "formal.lexical":
            assert coverage["outcome"] == "empty"


def test_repeated_equal_fields_and_subtoken_members_are_exact(prepared):
    layer = report(prepared, "x≥2\nx≥2\nlimit≥2kg")
    thresholds = roots(layer, "formal.threshold")
    assert [root["formal_input"]["text"] for root in thresholds] == ["x≥2", "x≥2", "limit≥2kg"]
    assert len({root["local_id"] for root in thresholds}) == 3
    numbers = [
        annotation
        for annotation in layer.payload["annotations"]
        if annotation["family"] == "formal.threshold"
        and annotation.get("formal", {}).get("rule") == "NUMBER"
    ]
    assert [
        (value[0]["start"], value[0]["end"], value[0]["text"])
        for value in (extents(layer, annotation) for annotation in numbers)
    ] == [(2, 3, "2"), (6, 7, "2"), (14, 15, "2")]
    assert [root["formal_input"]["correspondence"][0]["relation"] for root in thresholds] == [
        "exact"
    ] * 3


def test_decimal_comparators_units_and_domain_invalid_fields_survive(prepared):
    layer = report(
        prepared,
        (
            "x ≤ -2.50e-3 kg\nDate: 2026-02-30\nQuantity: +1.20e-3 quux\n"
            "Range: (2,2] kg\nIdentifier: A-1"
        ),
    )
    assert {"kind": "comparator", "value": "<=", "domain_status": "not_requested"} in normalized(
        layer, "formal.threshold"
    )
    assert {"kind": "decimal", "value": "-0.0025", "domain_status": "valid"} in normalized(
        layer, "formal.threshold"
    )
    assert any(
        value["value"] == "2026-02-30" and value["domain_status"] == "invalid"
        for value in normalized(layer, "formal.date")
    )
    assert any(
        value.get("unit") == "quux"
        and value["value"] == "0.0012"
        and value["domain_status"] == "unresolved"
        for value in normalized(layer, "formal.quantity")
    )
    assert any(
        value["kind"] == "interval"
        and value["domain_status"] == "invalid"
        and value["lower_closed"] is False
        and value["upper_closed"] is True
        for value in normalized(layer, "formal.interval")
    )
    assert any(value["value"] == "A-1" for value in normalized(layer, "formal.identifier"))
    assert roots(layer, "formal.date")[0]["formal_input"]["syntax_outcome"] == "complete"
    assert roots(layer, "formal.date")[0]["formal_input"]["interpretation_outcome"] == "invalid"
    assert layer.payload["outcome"] == "complete"
    # Existing domain adapters keep their stronger validation promise.
    assert parse_comparison_literal("Date: 2026-02-30") is None
    assert parse_comparison_literal("Range: (2,2] kg") is None
    threshold = parse_threshold("x ≤ -2.50e-3 kg")
    assert threshold is not None and threshold["value"] == "-0.0025"


def test_interval_endpoints_and_filtered_label_metadata(prepared):
    layer = report(prepared, "Range: [1,2)\nRange: (1,2]\nRange: [1,1]")
    values = [
        value for value in normalized(layer, "formal.interval") if value["kind"] == "interval"
    ]
    assert [
        (value["lower_closed"], value["upper_closed"], value["domain_status"]) for value in values
    ] == [(True, False, "valid"), (False, True, "valid"), (True, True, "valid")]
    first = roots(layer, "formal.interval")[0]
    nodes = [
        annotation["formal"]
        for annotation in layer.payload["annotations"]
        if annotation.get("formal", {}).get("input_id") == first["local_id"]
    ]
    assert any(
        node["rule"] == "NUMBER" and node["start"] == 8 and node["end"] == 9 and node["column"] == 9
        for node in nodes
    )
    root_node = next(node for node in nodes if node["node_kind"] == "rule")
    assert root_node["start"] == root_node["container_start"] == 0
    assert root_node["end"] == root_node["container_end"] == 12


def test_whole_input_failure_stays_distinct_from_nominated_complete_prefix(prepared):
    layer = report(prepared, "Date: 2026-02-28 trailing")
    field = next(
        root["formal_input"]
        for root in roots(layer, "formal.date")
        if root["formal_input"]["text"] == "Date: 2026-02-28 trailing"
    )
    assert field["syntax_outcome"] == "failed"
    assert field["text"] == "Date: 2026-02-28 trailing"
    assert field["diagnostic"]["category"] in {"UnexpectedCharacters", "UnexpectedToken"}
    assert (
        next(item for item in layer.payload["coverage"] if item["family"] == "formal.date")[
            "outcome"
        ]
        == "partial"
    )
    assert roots(layer, "formal.lexical")
    prefix = next(
        root["formal_input"]
        for root in roots(layer, "formal.date")
        if root["formal_input"]["text"] == "Date: 2026-02-28"
    )
    assert prefix["syntax_outcome"] == "complete"
    assert prefix["parent_occurrence"] != field["parent_occurrence"]


def test_recognized_formula_interior_never_claims_original_pdf_characters(prepared, monkeypatch):
    monkeypatch.setattr(
        math_grammar,
        "to_sympy",
        lambda *args, **kwargs: pytest.fail("syntax requested native algebra"),
    )
    view = source(
        ("x plus x", "formula", "x+x", "succeeded"), ("x plus x", "formula", "x+x", "succeeded")
    )
    layer = build_formal_layer(view, prepared, operation())
    formulas = roots(layer, "formal.math", "recognized_latex")
    assert len({item["local_id"] for item in formulas}) == 2
    for index, root in enumerate(formulas):
        formal_input = root["formal_input"]
        assert formal_input["text"] == "x+x"
        assert formal_input["original_text"] == "x plus x"
        assert formal_input["interpretation_outcome"] in {"resolved", "unresolved"}
        assert formal_input["correspondence"] == [
            dict(
                input_start=0,
                input_end=3,
                relation="contained_in_atom",
                source_occurrences=[formal_input["parent_occurrence"]],
            )
        ]
        symbols = [
            item
            for item in layer.payload["annotations"]
            if item.get("formal", {}).get("input_id") == root["local_id"]
            and item["formal"]["rule"] == "SYMBOL"
        ]
        assert [(item["formal"]["start"], item["formal"]["end"]) for item in symbols] == [
            (0, 1),
            (2, 3),
        ]
        assert all(
            [
                (extent["native_pointer"], extent["start"], extent["end"])
                for extent in extents(layer, item)
            ]
            == [(f"#/texts/{index}", index * 9, index * 9 + 8)]
            for item in symbols
        )
    replay = decode_layer(prepared, encode_layer(layer))
    assert (
        roots(replay, "formal.math", "recognized_latex")[1]["formal_input"]["original_text"]
        == "x plus x"
    )
    assert replay.payload == layer.payload


def test_ordinary_retained_annotation_read_preserves_formal_fields_without_parsing(
    prepared, monkeypatch
):
    from corpus_structure.semantic import formal_evidence
    from corpus_structure.semantic.characterization import validate_view
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.serve.characterization import (
        CharacterizationRequest,
        inspect_captured_characterization,
    )

    layer = report(prepared, "Date: 2026-02-30")
    pin = layer.reference(12)
    payload = layer.payload
    composed = validate_view(
        prepared,
        dict(
            format="enriched-document-view-v1",
            base_document=payload["base_document"],
            release_id=prepared.release_id,
            source_scope=payload["source_scope"],
            layers=[pin.values()],
            profile="selected_layers",
            coverage=payload["coverage"],
        ),
        {pin: layer},
    ).payload
    monkeypatch.setattr(
        formal_evidence,
        "nominate_fields",
        lambda *args: pytest.fail("retained read reran nomination"),
    )
    monkeypatch.setattr(
        math_grammar, "syntax", lambda *args: pytest.fail("retained read reran parsing")
    )
    response = inspect_captured_characterization(
        composed,
        {(pin.task_id, pin.product_key, pin.content_digest): payload},
        CharacterizationRequest(
            run_id=1,
            task_id=13,
            product_key="view",
            content_digest=sha256(canonical_bytes(composed)).hexdigest(),
            view="annotations",
            family="formal.date",
            kind="formal.input",
        ),
    )
    row = response.items[0]
    assert isinstance(row, dict)
    row = cast(dict[str, Any], row)
    field = row["annotation"]["formal_input"]
    assert field["text"] == "Date: 2026-02-30"
    assert field["syntax_outcome"] == "complete"
    assert field["interpretation_outcome"] == "invalid"
    assert row["occurrences"][0]["extents"][0]["text"] == "Date: 2026-02-30"


def test_failed_recognition_and_deadline_preserve_input_and_lexical_siblings(prepared, monkeypatch):
    unavailable = build_formal_layer(
        source(("bad source", "formula", "", "failed")), prepared, operation()
    )
    assert (
        roots(unavailable, "formal.math", "recognized_latex")[0]["formal_input"]["diagnostic"][
            "category"
        ]
        == "recognition_unavailable"
    )
    monkeypatch.setattr(
        math_grammar,
        "syntax_forest",
        lambda latex, start, **kwargs: math_grammar.MathForestResult(
            latex, start, ParseOutcome.FAILED, failure=math_grammar.Failure("timeout", "Timeout")
        ),
    )
    timed_out = build_formal_layer(
        source(("original", "formula", "x+x", "succeeded")), prepared, operation()
    )
    formal = roots(timed_out, "formal.math", "recognized_latex")[0]["formal_input"]
    assert formal["text"] == "x+x" and formal["original_text"] == "original"
    assert formal["syntax_outcome"] == "failed" and formal["diagnostic"]["category"] == "timeout"
    assert roots(timed_out, "formal.lexical")


def test_semantic_callback_failure_does_not_erase_positioned_syntax(prepared, monkeypatch):
    from corpus_structure.semantic import formal_evidence

    def failed(tree):
        raise VisitError(str(tree.data), tree, ValueError("test interpretation failure"))

    monkeypatch.setattr(formal_evidence, "normalized_field", failed)
    layer = report(prepared, "Date: 2026-02-28")
    field = roots(layer, "formal.date")[0]["formal_input"]
    assert field["syntax_outcome"] == "complete"
    assert field["interpretation_outcome"] == "failed"
    assert field["diagnostic"] == dict(
        category="semantic_callback", message="ValueError: test interpretation failure", rule="date"
    )
    assert any(
        item.get("formal", {}).get("rule") == "DATE" for item in layer.payload["annotations"]
    )


def test_formal_ambiguity_uses_direct_shared_dag_and_bounded_callbacks(prepared, monkeypatch):
    monkeypatch.setattr(
        math_grammar,
        "syntax",
        lambda *args, **kwargs: pytest.fail("packed recognition expanded conventional trees"),
    )
    monkeypatch.setattr(
        math_grammar,
        "to_sympy",
        lambda *args, **kwargs: pytest.fail("packed syntax constructed native algebra"),
    )
    view = source(("original", "formula", "f(x)", "succeeded"))
    layer = build_formal_layer(view, prepared, operation())
    assert layer.payload["choices"]
    assert {"application", "multiply"} <= {term["value"] for term in layer.payload["terms"]}
    assert any(
        "choice_group" in edge
        for term in layer.payload["terms"]
        for edge in term.get("children", ())
    )
    bounded = build_formal_layer(view, prepared, operation(), max_forest_nodes=1)
    assert (
        roots(bounded, "formal.math", "recognized_latex")[0]["formal_input"]["diagnostic"][
            "category"
        ]
        == "semantic_callback"
    )
    assert (
        roots(bounded, "formal.math", "recognized_latex")[0]["formal_input"]["syntax_outcome"]
        == "complete"
    )
    assert bounded.payload["outcome"] == "partial"


def test_unsupported_formal_callback_retains_native_syntax_as_unknown(prepared):
    layer = build_formal_layer(
        source(("original", "formula", r"\sqrt{x}", "succeeded")), prepared, operation()
    )
    formal = roots(layer, "formal.math", "recognized_latex")[0]["formal_input"]
    assert formal["syntax_outcome"] == "complete"
    assert formal["interpretation_outcome"] == "unresolved"
    assert formal["diagnostic"]["category"] == "unsupported_formal_semantics"
    unsupported = [
        term for term in layer.payload["terms"] if term["value"] == "uninterpreted:square_root"
    ]
    assert unsupported and all(term["status"] == "unknown" for term in unsupported)
    assert any(
        annotation["native_label"] == "square_root" for annotation in layer.payload["annotations"]
    )


def test_canonical_symbols_retain_qualified_subscript_parent_and_derivation(prepared):
    layer = build_formal_layer(
        source(("original", "formula", r"\sigma_{X_1} + \mu_i", "succeeded")),
        prepared,
        operation(),
        math_start="formula",
    )
    recognized_root = roots(layer, "formal.math", "recognized_latex")[0]["local_id"]
    symbols = {
        annotation["local_id"]: annotation
        for annotation in layer.payload["annotations"]
        if annotation["kind"] == "formal.symbol"
        and annotation["formal"]["input_id"] == recognized_root
    }
    actual = []
    for symbol in symbols.values():
        formal = symbol["formal"]
        parent = symbols.get(formal.get("symbol_parent"))
        actual.append(
            (
                formal["normalized"]["value"],
                formal["start"],
                formal["end"],
                None if parent is None else parent["formal"]["normalized"]["value"],
            )
        )
        assert symbol["premises"]
    assert sorted(actual, key=lambda value: value[1]) == [
        (r"\sigma_{X_1}", 0, 12, None),
        ("X_1", 8, 11, r"\sigma_{X_1}"),
        (r"\mu_i", 15, 20, None),
        ("i", 19, 20, r"\mu_i"),
    ]
    assert (
        decode_layer(prepared, encode_layer(layer)).payload["annotations"]
        == layer.payload["annotations"]
    )


@pytest.mark.parametrize(
    ("surface", "expected"),
    [
        ("-2.50e-3", "-0.0025"),
        ("1e1000000", "1e1000000"),
        ("-0.000", "0"),
        ("123456789012345678901234567890.125", "123456789012345678901234567890.125"),
    ],
)
def test_decimal_normalization_is_exact_and_does_not_expand_large_exponents(surface, expected):
    assert decimal_value(surface) == expected


def test_native_math_working_syntax_uses_retained_callbacks_without_parse(prepared, monkeypatch):
    from corpus_structure.methods.math.prepared import PreparedMathInput
    from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context
    from corpus_structure.semantic.formal_forest import retained_math_syntax

    view = source(("x+1", "formula", "x+1", "succeeded"))
    layer = build_formal_layer(view, prepared, operation())
    layers = {layer.reference(42): layer}
    monkeypatch.setattr(
        math_grammar, "syntax", lambda *a, **k: pytest.fail("consumer reran parser")
    )
    result = retained_math_syntax(layers, view, "#/texts/0", "x+1")
    assert result.status is ParseOutcome.OK, result.failure
    assert result.tree is not None
    assert any(node.data == "add" for node in result.tree.iter_subtrees())
    operand = PreparedMathInput(prepare_interpretation_context(macros={}), "x+1")
    operand.retain_primary_syntax(result)
    assert operand.syntax() is result


def test_native_math_working_syntax_retains_local_rivals_and_refuses_macro_drift(prepared):
    from corpus_structure.core.evidence import MacroDef
    from corpus_structure.semantic.formal_forest import retained_math_syntax

    view = source(("f(x)", "formula", "f(x)", "succeeded"))
    layer = build_formal_layer(view, prepared, operation())
    result = retained_math_syntax({layer.reference(42): layer}, view, "#/texts/0", "f(x)")
    assert result.status is ParseOutcome.AMBIGUOUS and result.tree is not None
    assert any(node.data == "_ambig" for node in result.tree.iter_subtrees())
    assert result.failure is None
    result = retained_math_syntax(
        {layer.reference(42): layer},
        view,
        "#/texts/0",
        "f(x)",
        macros={"\\RR": MacroDef(body="\\mathbb{R}")},
    )
    assert (
        result.status is ParseOutcome.FAILED
        and result.failure is not None
        and result.failure.category == "primary_grammar_drift"
    )


def test_native_formal_macros_are_frozen_in_input_and_grammar(prepared):
    from corpus_structure.core.evidence import MacroDef
    from corpus_structure.semantic.formal_evidence import macro_identity, math_grammar_identity

    view = source(("R", "formula", "\\RR", "succeeded"))
    macros = {"\\RR": MacroDef(body="\\mathbb{R}")}
    layer = build_formal_layer(view, prepared, operation(), macros=macros)
    inp = roots(layer, "formal.math", "recognized_latex")[0]["formal_input"]
    assert inp["macro_identity"] == macro_identity(macros) != "none"
    assert inp["grammar"] == math_grammar_identity(macros)
    assert inp["syntax_outcome"] == "complete"


def test_native_request_consumes_primary_math_for_syntax_lexical_and_structure(
    prepared, monkeypatch
):
    from corpus_structure.methods.math.native import native_request_analysis

    view = source(("x+1", "formula", "x+1", "succeeded"))
    layer = build_formal_layer(view, prepared, operation())
    layers = {layer.reference(42): layer}
    monkeypatch.setattr(
        math_grammar, "syntax", lambda *_a, **_k: pytest.fail("request reparsed syntax")
    )
    syntax = native_request_analysis(view, None, "syntax", primary_layers=layers)
    assert syntax.items[0]["outcome"] == "ok"
    assert syntax.items[0]["primary_input"]["layer"] == layer.reference(42).values()
    lexical = native_request_analysis(view, None, "lexical", primary_layers=layers)
    assert {(t["text"], t["start"], t["end"]) for t in lexical.items[0]["lexical"]} == {
        ("x", 0, 1),
        ("+", 1, 2),
        ("1", 2, 3),
    }
    structure = native_request_analysis(view, None, "structure", primary_layers=layers)
    assert structure.items[0]["structure"]["outcome"] == "complete"
    assert all("primary_node" in row for row in structure.items[0]["structure"]["nodes"])
    missing = native_request_analysis(view, None, "syntax", primary_layers={})
    assert missing.items[0]["outcome"] == "failed"
    assert missing.items[0]["failure"]["category"] == "missing_primary_input"


def test_native_method_readings_seed_primary_syntax_once_before_domain_interpretation(
    prepared, monkeypatch
):
    from types import SimpleNamespace

    from corpus_structure.methods.math.methods import ExtractMathConfig
    from corpus_structure.methods.math.native import readings

    view = source(("x+1", "formula", "x+1", "succeeded"))
    layer = build_formal_layer(view, prepared, operation())
    layers = {layer.reference(42): layer}
    reader = SimpleNamespace(
        prepared=None,
        primary_characterization=lambda _id, **_kw: layers,
        ancestor_source_views=lambda _id: (),
    )
    cfg = ExtractMathConfig(characterization_layers=(layer.reference(42).values(),))
    monkeypatch.setattr(
        math_grammar, "syntax", lambda *_a, **_k: pytest.fail("method reparsed formula")
    )
    monkeypatch.setattr(
        math_grammar, "syntax_forest", lambda *_a, **_k: pytest.fail("method rebuilt forest")
    )
    result = readings(view, cfg, reader)
    assert len(result) == 1 and result[0].result.status is ParseOutcome.OK
    assert [(o.name, o.start, o.end) for o in result[0].result.occurrences] == [("x", 0, 1)]
    assert result[0].prepared._primary_input["layer"] == layer.reference(42).values()
    assert readings(view, cfg, reader)[0] is result[0]


def test_native_math_reading_caches_are_private_to_their_reader_with_shared_primary_input(
    prepared, monkeypatch
):
    from types import SimpleNamespace

    from corpus_structure.methods.math.methods import ExtractMathConfig
    from corpus_structure.methods.math.native import readings
    from corpus_structure.methods.math.prepared import StageState

    view = source(("x+1", "formula", "x+1", "succeeded"))
    layer = build_formal_layer(view, prepared, operation())
    layers = {layer.reference(42): layer}

    def reader():
        return SimpleNamespace(
            prepared=None,
            primary_characterization=lambda _id, **_kw: layers,
            ancestor_source_views=lambda _id: (),
        )

    left, right = reader(), reader()
    cfg = ExtractMathConfig(characterization_layers=(layer.reference(42).values(),))
    monkeypatch.setattr(
        math_grammar, "syntax", lambda *_a, **_k: pytest.fail("reader reparsed retained syntax")
    )
    monkeypatch.setattr(
        math_grammar,
        "syntax_forest",
        lambda *_a, **_k: pytest.fail("reader rebuilt retained forest"),
    )
    (first,) = readings(view, cfg, left)
    (second,) = readings(view, cfg, right)
    assert first is not second and first.prepared is not second.prepared
    assert first.result.status is second.result.status is ParseOutcome.OK
    assert [(o.name, o.start, o.end) for o in first.result.occurrences] == [("x", 0, 1)]
    assert [(o.name, o.start, o.end) for o in second.result.occurrences] == [("x", 0, 1)]
    assert left.math_readings_batch is not right.math_readings_batch
    assert readings(view, cfg, left)[0] is first
    assert readings(view, cfg, right)[0] is second
    first.prepared._states["private-control"] = StageState("failed", "partial", "controlled")
    left.math_readings_batch.native.clear()
    assert "private-control" not in second.prepared._states
    assert readings(view, cfg, right)[0] is second
    with pytest.raises(ValueError, match="another source reader"):
        left.math_readings_batch.bind(right)


def test_private_native_choice_factoring_preserves_correlated_pairs_and_shared_children():
    from lark import Token, Tree

    from corpus_structure.semantic.formal_forest import _factored_native_alternatives

    symbol = Token("SYMBOL", "x", start_pos=0, end_pos=1)
    shared = Tree("symbol", [symbol])
    applied, multiplied = Tree("application", [shared]), Tree("product", [shared])
    first = Tree("_expression", [applied])
    second = Tree("_expression", [multiplied])
    factored = _factored_native_alternatives([first, second], inline=True)
    assert factored is not None and factored.data == "_expression"
    (choice,) = factored.children
    assert choice.data == "_ambig" and choice.children == [applied, multiplied]
    assert choice.children[0].children[0] is choice.children[1].children[0] is shared
    # Two correlated positions cannot become independent choices permitting
    # the unwitnessed application/application and product/product cross-pairs.
    assert (
        _factored_native_alternatives(
            [Tree("_pair", [applied, multiplied]), Tree("_pair", [multiplied, applied])],
            inline=True,
        )
        is None
    )
    assert first.children == [applied] and second.children == [multiplied]


def test_shared_native_working_dag_resolution_occurrences_and_delivery_stay_factored():
    from lark import Token, Tree

    from corpus_structure.methods.math import grammar
    from corpus_structure.methods.math.native import _restore_reading, _tree_value

    token = Token("SYMBOL", "x", start_pos=0, end_pos=1)
    node = token
    for _ in range(24):
        node = Tree("shared", [node, node])
    resolver = grammar._Resolver("x", {}, grammar.classify({}), grammar.MathContext())
    resolved = resolver.resolve(node)
    assert resolved is node and len(resolver._resolved) == 24
    (occurrence,) = grammar.occurrences(resolved, "x", {}, frozenset())
    assert (occurrence.name, occurrence.start, occurrence.end) == ("x", 0, 1)
    delivered = _tree_value(resolved)
    assert delivered["format"] == "lark-working-dag-1" and len(delivered["nodes"]) == 25
    assert all(
        row["children"][0] == row["children"][1] for row in delivered["nodes"] if "children" in row
    )

    from types import SimpleNamespace

    context = SimpleNamespace(grammar_context=grammar.MathContext(), macros={})
    recovered = _restore_reading(dict(syntax=delivered, outcome="ok"), "x", context)
    assert recovered.tree is not None
    assert len(list(recovered.tree.iter_subtrees())) == 24
    assert recovered.tree.children[0] is recovered.tree.children[1]
    cyclic = dict(
        format="lark-working-dag-1", root=0, nodes=[dict(rule="cycle", extent=[0, 1], children=[0])]
    )
    with pytest.raises(ValueError, match="cycle"):
        _restore_reading(dict(syntax=cyclic, outcome="ok"), "x", context)

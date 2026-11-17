"""Independent positions/domain outcomes through current nominal formal products."""

import pytest
from lark.exceptions import VisitError

from corpus_structure.core.vocab import ParseOutcome
from corpus_structure.methods.math import grammar as math_grammar
from corpus_structure.semantic.formal_evidence import (
    decimal_value,
    nominate_fields,
)
from corpus_structure.semantic.formal_products import FormalEvidenceOptions, FormalEvidenceProduct
from corpus_structure.semantic.structural_parsing import parse_comparison_literal, parse_threshold
from semantic.formal_products_support import profile as profile
from semantic.formal_products_support import selected_rows


@pytest.mark.parametrize("health", ["succeeded", "failed"])
def test_unprojected_native_formula_retains_recognition_without_literal_claim(profile, health):
    view = selected_rows(profile, ("", "formula", "x+1", health))
    layer = profile.run(view, FormalEvidenceOptions())
    (recognized,) = [
        row
        for row in layer.inventory()["annotations"]
        if row.get("formal_input", {}).get("representation") == "recognized_latex"
    ]
    assert recognized["formal_input"]["text"] == "x+1"
    assert recognized["formal_input"]["syntax_outcome"] == (
        "complete" if health == "succeeded" else "failed"
    )
    assert recognized["formal_input"]["correspondence"][0]["relation"] == "contained_in_atom"
    assert all(
        extent["native_pointer"] == "#/texts/0" and "start" not in extent and "text" not in extent
        for row in layer.inventory()["occurrences"]
        for extent in row["extents"]
    )
    coverage = {row["family"]: row for row in layer.inventory()["coverage"]}
    assert coverage["formal.math"]["outcome"] == "partial"
    assert "source-character correspondence" in coverage["formal.math"]["reason"]
    assert all(
        row["outcome"] == "empty" for family, row in coverage.items() if family != "formal.math"
    )
    assert any(row["kind"] == "formal.symbol" for row in layer.inventory()["annotations"]) == (
        health == "succeeded"
    )


def report(profile, text):
    return profile.run(selected_rows(profile, (text, "text", "", "")), FormalEvidenceOptions())


def roots(layer, family, representation=None):
    return [
        annotation
        for annotation in layer.inventory()["annotations"]
        if annotation["family"] == family
        and "formal_input" in annotation
        and (
            representation is None or annotation["formal_input"]["representation"] == representation
        )
    ]


def normalized(layer, family):
    return [
        annotation["formal"]["normalized"]
        for annotation in layer.inventory()["annotations"]
        if annotation["family"] == family and "normalized" in annotation.get("formal", {})
    ]


def extents(layer, annotation):
    values = {item["local_id"]: item["extents"] for item in layer.inventory()["occurrences"]}
    return [extent for occurrence in annotation["occurrences"] for extent in values[occurrence]]


def test_examined_nomination_is_independent_of_zero_recognized_fields(profile):
    nomination = nominate_fields("α\t prose\n")  # noqa: RUF001 - deliberate Greek source text
    assert (nomination.examined_start, nomination.examined_end) == (0, 9)
    assert nomination.candidates == ()
    layer = report(profile, "α\t prose\n")  # noqa: RUF001 - deliberate Greek source text
    for coverage in layer.inventory()["coverage"]:
        assert (
            coverage["eligible"]
            == coverage["examined"]
            == [
                dict(
                    projection=layer.value.source.projection,
                    native_pointer="#/texts/0",
                    start=0,
                    end=9,
                )
            ]
        )
        if coverage["family"] != "formal.lexical":
            assert coverage["outcome"] == "empty"


def test_repeated_equal_fields_and_subtoken_members_are_exact(profile):
    layer = report(profile, "x≥2\nx≥2\nlimit≥2kg")
    thresholds = roots(layer, "formal.threshold")
    assert [root["formal_input"]["text"] for root in thresholds] == ["x≥2", "x≥2", "limit≥2kg"]
    assert len({root["local_id"] for root in thresholds}) == 3
    numbers = [
        annotation
        for annotation in layer.inventory()["annotations"]
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


def test_decimal_comparators_units_and_domain_invalid_fields_survive(profile):
    layer = report(
        profile,
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
    assert layer.value.outcome == "complete"
    # Existing domain adapters keep their stronger validation promise.
    assert parse_comparison_literal("Date: 2026-02-30") is None
    assert parse_comparison_literal("Range: (2,2] kg") is None
    threshold = parse_threshold("x ≤ -2.50e-3 kg")
    assert threshold is not None and threshold["value"] == "-0.0025"


def test_interval_endpoints_and_filtered_label_metadata(profile):
    layer = report(profile, "Range: [1,2)\nRange: (1,2]\nRange: [1,1]")
    values = [
        value for value in normalized(layer, "formal.interval") if value["kind"] == "interval"
    ]
    assert [
        (value["lower_closed"], value["upper_closed"], value["domain_status"]) for value in values
    ] == [(True, False, "valid"), (False, True, "valid"), (True, True, "valid")]
    first = roots(layer, "formal.interval")[0]
    nodes = [
        annotation["formal"]
        for annotation in layer.inventory()["annotations"]
        if annotation.get("formal", {}).get("input_id") == first["local_id"]
    ]
    assert any(
        node["rule"] == "NUMBER" and node["start"] == 8 and node["end"] == 9 and node["column"] == 9
        for node in nodes
    )
    root_node = next(node for node in nodes if node["node_kind"] == "rule")
    assert root_node["start"] == root_node["container_start"] == 0
    assert root_node["end"] == root_node["container_end"] == 12


def test_whole_input_failure_stays_distinct_from_nominated_complete_prefix(profile):
    layer = report(profile, "Date: 2026-02-28 trailing")
    field = next(
        root["formal_input"]
        for root in roots(layer, "formal.date")
        if root["formal_input"]["text"] == "Date: 2026-02-28 trailing"
    )
    assert field["syntax_outcome"] == "failed"
    assert field["text"] == "Date: 2026-02-28 trailing"
    assert field["diagnostic"]["category"] in {"UnexpectedCharacters", "UnexpectedToken"}
    assert (
        next(item for item in layer.inventory()["coverage"] if item["family"] == "formal.date")[
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


def test_recognized_formula_interior_never_claims_original_pdf_characters(profile, monkeypatch):
    monkeypatch.setattr(
        math_grammar,
        "to_sympy",
        lambda *args, **kwargs: pytest.fail("syntax requested native algebra"),
    )
    view = selected_rows(
        profile,
        ("x plus x", "formula", "x+x", "succeeded"),
        ("x plus x", "formula", "x+x", "succeeded"),
    )
    layer = profile.run(view, FormalEvidenceOptions())
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
            for item in layer.inventory()["annotations"]
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
    replay = FormalEvidenceProduct(layer.content, profile.prepared, profile.model)
    assert (
        roots(replay, "formal.math", "recognized_latex")[1]["formal_input"]["original_text"]
        == "x plus x"
    )
    assert replay.inventory() == layer.inventory()


def test_ordinary_retained_annotation_read_preserves_formal_fields_without_parsing(
    profile, monkeypatch
):
    from corpus_structure.semantic import formal_evidence

    layer = report(profile, "Date: 2026-02-30")
    monkeypatch.setattr(
        formal_evidence,
        "nominate_fields",
        lambda *args: pytest.fail("retained read reran nomination"),
    )
    monkeypatch.setattr(
        math_grammar, "syntax", lambda *args: pytest.fail("retained read reran parsing")
    )
    retained = FormalEvidenceProduct(layer.content, profile.prepared, profile.model).inventory()
    row = next(
        annotation
        for annotation in retained["annotations"]
        if annotation["family"] == "formal.date" and annotation["kind"] == "formal.input"
    )
    field = row["formal_input"]
    assert field["text"] == "Date: 2026-02-30"
    assert field["syntax_outcome"] == "complete"
    assert field["interpretation_outcome"] == "invalid"
    occurrence = next(
        value for value in retained["occurrences"] if value["local_id"] == row["occurrences"][0]
    )
    assert occurrence["extents"][0]["text"] == "Date: 2026-02-30"


def test_failed_recognition_and_deadline_preserve_input_and_lexical_siblings(profile, monkeypatch):
    unavailable = profile.run(
        selected_rows(profile, ("bad source", "formula", "", "failed")), FormalEvidenceOptions()
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
    timed_out = profile.run(
        selected_rows(profile, ("original", "formula", "x+x", "succeeded")), FormalEvidenceOptions()
    )
    formal = roots(timed_out, "formal.math", "recognized_latex")[0]["formal_input"]
    assert formal["text"] == "x+x" and formal["original_text"] == "original"
    assert formal["syntax_outcome"] == "failed" and formal["diagnostic"]["category"] == "timeout"
    assert roots(timed_out, "formal.lexical")


def test_semantic_callback_failure_does_not_erase_positioned_syntax(profile, monkeypatch):
    from corpus_structure.semantic import formal_evidence

    def failed(tree):
        raise VisitError(str(tree.data), tree, ValueError("test interpretation failure"))

    monkeypatch.setattr(formal_evidence, "normalized_field", failed)
    layer = report(profile, "Date: 2026-02-28")
    field = roots(layer, "formal.date")[0]["formal_input"]
    assert field["syntax_outcome"] == "complete"
    assert field["interpretation_outcome"] == "failed"
    assert field["diagnostic"] == dict(
        category="semantic_callback", message="ValueError: test interpretation failure", rule="date"
    )
    assert any(
        item.get("formal", {}).get("rule") == "DATE" for item in layer.inventory()["annotations"]
    )


def test_formal_ambiguity_uses_direct_shared_dag_and_bounded_callbacks(profile, monkeypatch):
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
    view = selected_rows(profile, ("original", "formula", "f(x)", "succeeded"))
    layer = profile.run(view, FormalEvidenceOptions())
    assert layer.inventory()["choices"]
    assert {"application", "multiply"} <= {term["value"] for term in layer.inventory()["terms"]}
    assert any(
        "choice_group" in edge
        for term in layer.inventory()["terms"]
        for edge in term.get("children", ())
    )
    bounded = profile.run(view, FormalEvidenceOptions(max_forest_nodes=1))
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
    assert bounded.value.outcome == "partial"


def test_unsupported_formal_callback_retains_native_syntax_as_unknown(profile):
    layer = profile.run(
        selected_rows(profile, ("original", "formula", r"\sqrt{x}", "succeeded")),
        FormalEvidenceOptions(),
    )
    formal = roots(layer, "formal.math", "recognized_latex")[0]["formal_input"]
    assert formal["syntax_outcome"] == "complete"
    assert formal["interpretation_outcome"] == "unresolved"
    assert formal["diagnostic"]["category"] == "unsupported_formal_semantics"
    unsupported = [
        term for term in layer.inventory()["terms"] if term["value"] == "uninterpreted:square_root"
    ]
    assert unsupported and all(term["status"] == "unknown" for term in unsupported)
    assert any(
        annotation["native_label"] == "square_root"
        for annotation in layer.inventory()["annotations"]
    )


def test_canonical_symbols_retain_qualified_subscript_parent_and_derivation(profile):
    layer = profile.run(
        selected_rows(profile, ("original", "formula", r"\sigma_{X_1} + \mu_i", "succeeded")),
        FormalEvidenceOptions(math_start="formula"),
    )
    recognized_root = roots(layer, "formal.math", "recognized_latex")[0]["local_id"]
    symbols = {
        annotation["local_id"]: annotation
        for annotation in layer.inventory()["annotations"]
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
        FormalEvidenceProduct(layer.content, profile.prepared, profile.model).inventory()[
            "annotations"
        ]
        == layer.inventory()["annotations"]
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


def test_current_formal_macros_are_explicit_inputs_under_the_acquired_grammar(profile):
    from corpus_structure.core.evidence import MacroDef
    from corpus_structure.semantic.formal_evidence import grammar_identity, macro_identity

    view = selected_rows(profile, ("R", "formula", "\\RR", "succeeded"))
    macros = {"\\RR": MacroDef(body="\\mathbb{R}")}
    layer = profile.run(view, FormalEvidenceOptions(macros=macros))
    inp = roots(layer, "formal.math", "recognized_latex")[0]["formal_input"]
    assert inp["macro_identity"] == macro_identity(macros) != "none"
    assert inp["grammar"] == "formal-math"
    assert profile.grammar == grammar_identity()
    changed = profile.run(
        view, FormalEvidenceOptions(macros={"\\RR": MacroDef(body="\\mathbb{Z}")})
    )
    other = roots(changed, "formal.math", "recognized_latex")[0]["formal_input"]
    assert other["macro_identity"] != inp["macro_identity"]
    assert other["grammar"] == inp["grammar"]
    assert inp["syntax_outcome"] == "complete"


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


def test_formal_descendant_selection_walks_frozen_native_parent_links():
    from types import SimpleNamespace

    from corpus_structure.semantic.formal_evidence import (
        FormalIdentity,
        _LayerBuilder,
        extract_formal_facts,
    )
    from corpus_structure.semantic.native_source_view import freeze_native

    text = "ordinary prose"
    view = SimpleNamespace(
        text=text,
        pieces=freeze_native(
            [
                dict(kind="native_text", start=0, end=len(text), item_ref="#/texts/1"),
            ]
        ),
        items=freeze_native(
            [
                dict(self_ref="#/groups/0", label="section"),
                dict(self_ref="#/groups/1", label="section", parent={"$ref": "#/groups/0"}),
                dict(self_ref="#/texts/1", label="text", parent={"$ref": "#/groups/1"}),
            ]
        ),
        health={},
    )
    builder = _LayerBuilder(view, {}, FormalIdentity(b"{}", "projection:fixture", "view", True))
    actual = extract_formal_facts(
        builder,
        [dict(native_pointer="#/groups/0")],
        math_start="any_value",
        parse_seconds=1,
        max_forest_nodes=1024,
        max_inline_chars=512,
        check_active=lambda: None,
    )
    assert actual == [
        dict(
            projection="projection:fixture",
            native_pointer="#/texts/1",
            start=0,
            end=14,
        )
    ]
    assert builder.annotations

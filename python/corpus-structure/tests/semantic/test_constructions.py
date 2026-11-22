"""Independent positioned and symbolic expectations for shared constructions."""

import pytest
from lark import Lark
from methods.declared_primary_fixture import profiles, selected_source
from spacy.lang.en import English
from spacy.tokens import Doc

from corpus_structure.semantic.constructions import (
    FAMILIES,
    PackedReducer,
    ProtectedAtom,
    recognize,
)
from corpus_structure.semantic.constructions.forest import terminal_guard
from corpus_structure.semantic.constructions.layers import ConstructionLayer, ConstructionSource
from corpus_structure.semantic.constructions.matching import RAW_GROUP, PreparedConstructions


def source(text):
    selected, _frame, _context = selected_source(text)
    builder = ConstructionLayer(
        selected.value["source"],
        {"selectors": selected.value["selectors"]},
        {"key": "text.constructions/source-native"},
    )
    return builder, ConstructionSource.from_native(selected)


def nominal_product(builder, view, *, value=None):
    """Validate the actual current product, including grammar witness endpoints."""
    from corpus_structure.semantic.construction_products import (
        interpreted_member_contracts,
        interpreted_product_value,
        validate_interpreted_product,
    )
    from corpus_structure.semantic.source_products import FrozenNativeSource

    _formal, profile = profiles()
    selected = FrozenNativeSource.acquire(profile.prepared, view.value)
    _source, _frame, context = selected_source(view.text)
    if value is None:
        value = interpreted_product_value(
            selected,
            builder.facts(),
            interpreted_member_contracts(profile.prepared, profile.model),
        ) | {"annotation_support": [], "formal_support": []}
    return validate_interpreted_product(
        profile.prepared, profile.model, value, selected, (), subject_context=context
    )


def native_columns(doc):
    """Detach independent literal columns through current annotation ownership."""
    from dataclasses import replace
    from hashlib import sha256
    from unittest.mock import patch

    from annotation_support import ControlledPipeline, selected_item
    from methods.declared_primary_fixture import retained_source_annotations

    from corpus_structure.ingest import annotations
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.ingest.sentences import TextLayout, TextToken

    controlled = ControlledPipeline()
    request, selected, frame, context = selected_item(
        controlled, doc.text, start=0, block_id="#/texts/1"
    )
    request = replace(
        request,
        layout=TextLayout(
            0,
            len(doc.text),
            sha256(doc.text.encode()).hexdigest(),
            tuple(
                TextToken(token.idx, token.idx + len(token), bool(token.whitespace_))
                for token in doc
            ),
            (),
        ),
    )
    profile = AnnotationProfile(execution_profile=controlled.selection().native.fingerprint)
    with patch.object(annotations, "pipeline", return_value=controlled):
        (product,) = annotations.annotate(
            (request,), profile, processed_docs=(doc,), require_complete=False
        )
    native = retained_source_annotations(selected, frame, context, (product,), profile)
    return selected, native


def test_raw_source_negation_quantification_and_conditional_are_nested():
    result = recognize("Not every trial succeeds.")
    assert result.outcome == "complete"
    assert result.reducer is not None
    terms = result.reducer.terms
    negative = [t for t in terms.values() if t["value"] == "negation"]
    assert negative
    assert any(
        t["kind"] == "binder"
        and {e["role"] for e in t["children"]} >= {"variable", "restrictor", "body"}
        for t in terms.values()
    )
    assert any(e["role"] == "target" for t in negative for e in t["children"])
    condition = recognize("If rain falls, then grass grows.")
    assert condition.reducer is not None
    assert any(
        t["value"] == "conditional" and t["kind"] == "clause_relation"
        for t in condition.reducer.terms.values()
    )


def test_direct_forest_reuses_shared_child_at_every_parent_without_enumeration():
    forest = Lark(
        'start: left | right\nleft: shared "x"\nright: shared "x"\nshared: "a"',
        parser="earley",
        lexer="dynamic",
        ambiguity="forest",
        priority=None,
        ordered_sets=True,
    ).parse("ax")
    reducer = PackedReducer("ax", ())
    root = reducer.transform(forest)
    assert root is not None
    assert root.choice_group
    assert reducer.reuses > 0
    shared = [t["local_id"] for t in reducer.terms.values() if t["value"] == "shared"]
    assert len(shared) == 1
    parents = [t for t in reducer.terms.values() if t["value"] in {"left", "right"}]
    assert len(parents) == 2
    assert all(any(e.get("target") == shared[0] for e in p["children"]) for p in parents)


def test_whole_repeated_atoms_touching_punctuation_keep_independent_positions():
    text = "x + y uses x + y."
    result = recognize(text, (ProtectedAtom(0, 5, "first"), ProtectedAtom(11, 16, "second")))
    assert result.outcome == "complete"
    assert result.reducer is not None
    terminals = [
        s
        for s in result.reducer.syntax.values()
        if s["kind"] == "grammar.terminal" and s["native_label"] == "ATOM"
    ]
    assert {(t["start"], t["end"]) for t in terminals} == {(0, 5), (11, 16)}
    assert len({t["local_id"] for t in terminals}) == 2
    for t in result.reducer.syntax.values():
        if t["kind"] == "grammar.terminal" and t["native_label"] != "ATOM":
            assert not (t["start"] < 5 and t["end"] > 0)


def test_ignore_cannot_swallow_protected_whitespace_atom():
    text = "A uses  ."
    result = recognize(text, (ProtectedAtom(7, 8, "blank-formula"),))
    assert result.outcome == "complete"
    assert result.reducer is not None
    assert any(
        t["native_label"] == "ATOM" and (t["start"], t["end"]) == (7, 8)
        for t in result.reducer.syntax.values()
        if t["kind"] == "grammar.terminal"
    )


@pytest.mark.parametrize("separator", ["\n", "\r\n", "\t", "\f", "\v"])
def test_source_line_breaks_remain_lexical_separators(separator):
    result = recognize("Not every" + separator + "trial succeeds.")
    assert result.outcome == "complete"
    assert result.reducer is not None
    assert any(term["value"] == "negation" for term in result.reducer.terms.values())
    assert any(term["kind"] == "binder" for term in result.reducer.terms.values())


@pytest.mark.parametrize(
    "spelling,label",
    [
        ("x\n+\ny", "x + y"),
        ("x\r\n+\\y", "x +\\y"),
        (r"x\n+y", r"x\n+y"),
        ("x/\n y", "x/ y"),
        (" \n ", " "),
    ],
)
def test_grammar_atoms_keep_exact_multiline_and_literal_escape_spelling(spelling, label):
    builder, view = source(spelling + " varies.")
    result = builder.region(view, 0, len(view.text), [ProtectedAtom(0, len(spelling), "atom")])
    assert result.outcome == "complete"
    terminal = next(
        row
        for row in builder.annotations.values()
        if row["kind"] == "grammar.terminal" and row["native_label"] == "ATOM"
    )
    occurrence = builder.occurrences[terminal["occurrences"][0]]
    assert [(e["start"], e["end"], e["text"]) for e in occurrence["extents"]] == [
        (0, len(spelling), spelling)
    ]
    term = next(t for t in builder.terms.values() if t["premises"] == [terminal["local_id"]])
    assert term["value"] == label
    assert "\n" not in term["value"] and "\r" not in term["value"]
    assert term.get("provenance", []) == (
        ["lexical-normalization:whitespace-folding-1"] if spelling != label else []
    )


@pytest.mark.parametrize(
    "start,end,atom", [(1, 3, False), (0, 6, False), (0, 4, True), (2, 5, True)]
)
def test_semantic_atom_guard_rejects_incompatible_derivations(start, end, atom):
    with pytest.raises(ValueError, match=r"protected|whole"):
        terminal_guard(start, end, (ProtectedAtom(0, 5, "atom"),), atom=atom)


def test_epsilon_has_synthetic_insertion_boundary_and_cycle_is_explicit():
    forest = Lark(
        'start: empty "a"\nempty:', parser="earley", lexer="dynamic", ambiguity="forest"
    ).parse("a")
    reducer = PackedReducer("a", (), offset=20)
    reducer.transform(forest)
    empty = next(t for t in reducer.terms.values() if t["value"] == "empty")
    assert reducer.positions[empty["local_id"]] == (20, 20)
    forest = Lark('start: loop\nloop: loop | "a"', parser="earley", ambiguity="forest").parse("a")
    with pytest.raises(ValueError, match="grammar cycle"):
        PackedReducer("a", ()).transform(forest)


@pytest.mark.parametrize(
    "text,value,family",
    [
        ("Rain falls.", "verbal_predication", 0),
        ("Sky is blue.", "copular_predication", 0),
        ("Rain falls that grass grows.", "complement", 1),
        ("Rain has fallen.", "auxiliary_predication", 2),
        ("Rain falls and grass grows.", "coordination", 3),
        ("May rain fall.", "modality", 4),
        ("Rain falls because grass grows.", "clause_relation", 5),
        ("Ada says rain falls.", "reporting", 6),
        ("Assume rain falls.", "passage_function", 7),
    ],
)
def test_selected_family_semantics_are_retained(text, value, family):
    result = recognize(text)
    assert result.root
    assert result.reducer is not None
    assert any(
        t["value"] == value and t["family"] == FAMILIES[family]
        for t in result.reducer.terms.values()
    )


def test_native_named_matches_keep_discontinuous_members_repetitions_and_overlap():
    vocab = English().vocab
    matcher = PreparedConstructions(vocab)
    doc = Doc(
        vocab,
        words=["Assume", "rain", "and", "snow", "fall"],
        spaces=[True, True, True, True, False],
        heads=[0, 4, 1, 1, 0],
        deps=["ROOT", "nsubj", "cc", "conj", "ccomp"],
        pos=["VERB", "NOUN", "CCONJ", "NOUN", "VERB"],
        lemmas=["assume", "rain", "and", "snow", "fall"],
    )
    matches, unavailable = matcher.match(doc)
    assert not unavailable
    assert any(
        m.rule_id == "tc.function_cue.v1" and m.alignments == (0, 1, 1, 1, 1) for m in matches
    )
    assert any(
        m.rule_id == "tc.native.active.v1" and m.bindings[0] == ("governor", (4,)) for m in matches
    )
    spans = list(doc.spans[RAW_GROUP])
    assert any(a.start <= b.start < a.end < b.end for a in spans for b in spans)


def test_missing_dependency_columns_preserve_lexical_results():
    vocab = English().vocab
    matches, unavailable = PreparedConstructions(vocab).match(
        Doc(vocab, words=["not", "every", "trial"])
    )
    assert unavailable
    assert {m.rule_id for m in matches} >= {"tc.negation.v1", "tc.quantification.v1"}


def test_named_native_anchor_is_distinct_from_discontinuous_members():
    vocab = English().vocab
    doc = Doc(
        vocab,
        words=["rain", "falls", "snow"],
        heads=[1, 1, 0],
        deps=["nsubj", "ROOT", "appos"],
        pos=["NOUN", "VERB", "NOUN"],
    )
    matches, _ = PreparedConstructions(vocab).match(doc)
    active = next(m for m in matches if m.rule_id == "tc.native.active.v1")
    assert active.anchors == (("governor", 1), ("subject", 0))
    assert dict(active.bindings)["subject"] == (0, 2)


def native_case(words, heads, deps, pos, morphs=None):
    from corpus_structure.semantic.constructions.matching import (
        retained_native_documents,
        retained_native_vocab,
    )

    vocab = English().vocab
    doc = Doc(
        vocab,
        words=words,
        spaces=[True] * (len(words) - 1) + [False],
        heads=heads,
        deps=deps,
        pos=pos,
        lemmas=[word.lower() for word in words],
        **({"morphs": morphs} if morphs else {}),
    )
    selected, native = native_columns(doc)
    view = ConstructionSource.from_native(selected)
    builder = ConstructionLayer(
        selected.value["source"],
        {"selectors": selected.value["selectors"]},
        {"key": "text.constructions/source-native"},
    )
    vocab = retained_native_vocab(selected, native)
    ((block, retained, annotations, start, _end),) = retained_native_documents(
        selected, native, vocab
    )
    builder.native(
        view,
        block,
        retained,
        annotations,
        start,
        PreparedConstructions(vocab),
    )
    return builder, native


@pytest.mark.parametrize("separator", ["\n", "\t", "\n\n", "  "])
def test_native_layout_tokens_are_not_semantic_participants(separator):
    builder, _ = native_case(
        ["Rain", separator, "falls"],
        [2, 2, 2],
        ["nsubj", "dep", "ROOT"],
        ["NOUN", "SPACE", "VERB"],
    )
    participants = [
        term
        for term in builder.terms.values()
        if term["kind"] == "participant" and term.get("external_premises")
    ]
    assert {term["value"] for term in participants} == {"rain", "falls"}
    assert all(
        premise["item_key"]
        != [{"kind": "text", "text": "token"}, {"kind": "integer", "integer": 1}]
        for term in participants
        for premise in term["external_premises"]
    )
    predicate = next(
        term
        for term in builder.terms.values()
        if term["kind"] == "predicate"
        and any(
            edge["role"] == "predicate" and builder.terms[edge["target"]]["value"] == "falls"
            for edge in term["children"]
        )
    )
    subject = next(edge for edge in predicate["children"] if edge["role"] == "grammatical_subject")
    assert builder.terms[subject["target"]]["value"] == "rain"


@pytest.mark.parametrize("spelling", ["X\n+\nY", "X\r\n+\tY"])
def test_multiline_native_atom_keeps_spelling_beside_interpreted_lexical_label(spelling):
    builder, _ = native_case([spelling, "varies"], [1, 1], ["nsubj", "ROOT"], ["NOUN", "VERB"])
    participant = next(term for term in builder.terms.values() if term["value"] == "x + y")
    assert participant["provenance"] == ["lexical-normalization:whitespace-folding-1"]
    assert participant["external_premises"][0] == {
        "variant": "partition-item",
        "role": "sentences",
        "collection": "rows",
        "partition_key": "#/texts/1",
        "item_key": [{"kind": "text", "text": "token"}, {"kind": "integer", "integer": 0}],
    }
    assert [
        extent["text"]
        for oid in participant["occurrences"]
        for extent in builder.occurrences[oid]["extents"]
    ] == [spelling]


def test_native_inflection_and_modal_force_are_explicit_supported_proposals():
    builder, _native = native_case(
        ["Rain", "may", "fall"],
        [2, 2, 2],
        ["nsubj", "aux", "ROOT"],
        ["NOUN", "AUX", "VERB"],
        ["Number=Sing", "VerbForm=Fin", "Tense=Pres|VerbForm=Inf"],
    )
    assert any(
        a["native_label"] == "Tense=Pres"
        for a in builder.annotations.values()
        if a["kind"] == "construction.inflection"
    )
    assert any(t["value"] == "tense:present" for t in builder.terms.values())
    forces = [t for t in builder.terms.values() if t["value"].startswith("modality:")]
    assert {t["value"] for t in forces} == {"modality:permission", "modality:possibility"}
    assert all(t["status"] == "private_proposal" for t in forces)
    group = next(
        g for g in builder.choices.values() if g["local_id"].startswith("modal-force-choice:")
    )
    assert group["compatibility"] == "exclusive"


def test_coordination_inherits_only_witnessed_missing_subject():
    inherited, _native = native_case(
        ["Rain", "falls", "and", "melts"],
        [1, 1, 3, 1],
        ["nsubj", "ROOT", "cc", "conj"],
        ["NOUN", "VERB", "CCONJ", "VERB"],
    )
    assert any(
        t["value"] == "inherited-grammatical-subject" and t["premises"]
        for t in inherited.terms.values()
    )
    local, _native = native_case(
        ["Rain", "falls", "and", "snow", "melts"],
        [1, 1, 4, 4, 1],
        ["nsubj", "ROOT", "cc", "nsubj", "conj"],
        ["NOUN", "VERB", "CCONJ", "NOUN", "VERB"],
    )
    assert not any(t["value"] == "inherited-grammatical-subject" for t in local.terms.values())


def test_native_quantification_has_distinct_variable_restrictor_body():
    builder, _native = native_case(
        ["Every", "trial", "succeeds"], [1, 2, 2], ["det", "nsubj", "ROOT"], ["DET", "NOUN", "VERB"]
    )
    binder = next(t for t in builder.terms.values() if t["kind"] == "binder")
    edges = {e["role"]: e["target"] for e in binder["children"]}
    assert {"variable", "restrictor", "body"} <= edges.keys()
    body = builder.terms[edges["body"]]
    assert (
        next(e["target"] for e in body["children"] if e["role"] == "grammatical_subject")
        == edges["variable"]
    )


def test_quantifier_and_negative_scope_remain_two_correlated_alternatives():
    result = recognize("Every trial does not succeed.")
    assert result.reducer is not None
    values = {t["value"]: t for t in result.reducer.terms.values()}
    assert values["quantified_negative_predication"]["kind"] == "binder"
    assert values["negative_quantified_predication"]["kind"] == "operator"
    assert result.reducer.choices


def test_layer_keeps_finite_witness_bindings_and_exact_source_positions():
    builder, view = source("Rain falls.")
    builder.region(view, 0, len(view.text))
    product = nominal_product(builder, view)
    payload = product.inventory()
    assert payload["roles"]
    annotations = {a["local_id"]: a for a in payload["annotations"]}
    memberships = {m["local_id"]: m for m in payload["memberships"]}
    for role in payload["roles"]:
        basis = role["basis"]
        assert role["owner"] == basis["construction"]
        assert memberships[basis["binding"]]["member"] == role["member"]
        assert role["member"] in annotations[basis["production"]]["premises"]
    assert {e["text"] for o in payload["occurrences"] for e in o["extents"]} >= {"Rain", "falls"}


def test_no_match_and_limit_have_distinct_outcomes():
    assert recognize("@@@").outcome == "empty"
    assert recognize("Rain falls.", max_chars=2).outcome == "unsupported"


def test_current_product_and_wrong_host_control():
    import json

    builder, view = source("Rain falls.")
    builder.region(view, 0, len(view.text))
    product = nominal_product(builder, view)
    assert product.inventory()["roles"]
    invalid = json.loads(product.content)
    role = next(
        packet["body"] for packet in invalid["members"] if packet["body"]["record_type"] == "role"
    )
    role["owner"] = next(
        packet["member_id"]
        for packet in invalid["members"]
        if packet["body"]["record_type"] == "term"
    )
    with pytest.raises(ValueError, match=r"witness|endpoint"):
        nominal_product(builder, view, value=invalid)


@pytest.mark.parametrize("gap", [" ", "\t", "\n  "])
def test_retained_working_doc_preserves_whitespace_and_native_named_dependencies(gap):
    from corpus_structure.semantic.constructions.matching import (
        retained_native_documents,
        retained_native_vocab,
    )

    # Arbitrary retained whitespace has its own source token; a single ordinary
    # space is represented by the preceding token's native space column.
    words = ["Rain", "falls"] if gap == " " else ["Rain", gap, "falls"]
    index = len(words) - 1
    doc = Doc(
        English().vocab,
        words=words,
        spaces=[True, False] if gap == " " else [False] * 3,
        heads=[index] * len(words),
        deps=["nsubj", "ROOT"] if gap == " " else ["nsubj", "dep", "ROOT"],
        pos=["NOUN", "VERB"] if gap == " " else ["NOUN", "SPACE", "VERB"],
        lemmas=[word.lower() for word in words],
    )
    selected, native = native_columns(doc)
    vocab = retained_native_vocab(selected, native)
    _block, restored, annotations, start, end = next(
        retained_native_documents(selected, native, vocab)
    )
    assert restored.text == "Rain" + gap + "falls"
    assert (start, end) == (0, len(restored.text))
    assert len(annotations) == len(words)
    assert restored.has_annotation("POS", require_complete=True)
    assert restored[0].head.i == index and restored[index].dep_ == "ROOT"
    matches, _ = PreparedConstructions(vocab).match(restored)
    assert any(match.rule_id == "tc.native.active.v1" for match in matches)


def test_literal_disjunction_and_collective_distribution_are_distinct_structures():
    result = recognize("A or B.")
    assert result.reducer is not None
    assert any(
        t["value"] == "or" and t["kind"] == "operator" for t in result.reducer.terms.values()
    )
    distributions = [
        g
        for g in result.reducer.choices.values()
        if {result.reducer.terms[m["root"]]["value"] for m in g["members"]}
        == {"collective", "distributive"}
    ]
    assert distributions


def test_nested_reporting_quotes_and_modality_retain_separate_nodes():
    result = recognize('Ada says "Rain may fall."')
    assert result.root
    assert result.reducer is not None
    meanings = {t["value"] for t in result.reducer.terms.values()}
    assert {"reporting", "quotation", "modality"} <= meanings


def test_existing_deadline_owner_distinguishes_expiry_and_thread_refusal():
    from concurrent.futures import ThreadPoolExecutor

    expired = recognize("Rain falls.", parse_seconds=0)
    assert expired.outcome == "partial"
    assert expired.reason is not None
    assert "deadline expired" in expired.reason
    with ThreadPoolExecutor(max_workers=1) as pool:
        refused = pool.submit(recognize, "Rain falls.").result()
    assert refused.outcome == "unsupported"
    assert refused.reason is not None
    assert "main thread" in refused.reason

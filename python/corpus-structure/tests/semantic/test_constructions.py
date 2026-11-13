"""Independent positioned and symbolic expectations for shared constructions."""

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest
from lark import Lark
from spacy.lang.en import English
from spacy.tokens import Doc

from corpus_structure.semantic.constructions import (
    FAMILIES,
    PackedReducer,
    ProtectedAtom,
    recognize,
)
from corpus_structure.semantic.constructions.forest import terminal_guard
from corpus_structure.semantic.constructions.layers import ConstructionLayer
from corpus_structure.semantic.constructions.matching import RAW_GROUP, PreparedConstructions


def source(text):
    base = dict(task_id=7, product_key="document", content_digest="a" * 64)
    projection = "b" * 64
    selector = dict(projection=projection, native_pointer="#/texts/0", start=0, end=len(text))
    scope = dict(
        source_view_ids=[11],
        source_views=[
            dict(
                source_view_id=11,
                key="source",
                base_document=base,
                section_pointer="#/groups/0",
                membership="descendants",
                projection_digest=projection,
                recipe_digest="c" * 64,
            )
        ],
        profile="full",
        selectors=[selector],
    )
    operation = dict(
        key="text.constructions",
        version="1",
        runtime="test",
        model="none",
        grammar="tc-constructions-1",
        configuration="cfg",
        input="input",
        context="scope",
    )
    builder = ConstructionLayer(base, scope, operation)
    view = SimpleNamespace(
        ref=SimpleNamespace(id=11, projection_digest=projection),
        text=text,
        pieces=(dict(start=0, end=len(text), kind="native_text", item_ref="#/texts/0", page=3),),
    )
    return builder, view


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
    from corpus_structure.semantic.product_reference import ProductReference

    vocab = English().vocab
    doc = Doc(
        vocab,
        words=words,
        spaces=[True] * (len(words) - 1) + [False],
        heads=heads,
        deps=deps,
        pos=pos,
        lemmas=[w.lower() for w in words],
        **({"morphs": morphs} if morphs else {}),
    )
    builder, view = source(doc.text)
    annotations = {
        i: dict(local_id=f"token-{i}", native_token=dict(text=w, lemma=w.lower()))
        for i, w in enumerate(words)
    }
    pin = ProductReference(task_id=8, product_key="layer", content_digest="d" * 64)
    builder.native(view, pin, "container", doc, annotations, 0, PreparedConstructions(vocab))
    return builder


@pytest.mark.parametrize("separator", ["\n", "\t", "\n\n", "  "])
def test_native_layout_tokens_are_not_semantic_participants(separator):
    builder = native_case(
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
        premise["local_id"] != "token-1"
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
    builder = native_case([spelling, "varies"], [1, 1], ["nsubj", "ROOT"], ["NOUN", "VERB"])
    participant = next(term for term in builder.terms.values() if term["value"] == "x + y")
    assert participant["provenance"] == ["lexical-normalization:whitespace-folding-1"]
    assert participant["external_premises"][0]["local_id"] == "token-0"
    assert [
        extent["text"]
        for oid in participant["occurrences"]
        for extent in builder.occurrences[oid]["extents"]
    ] == [spelling]


def test_native_inflection_and_modal_force_are_explicit_supported_proposals():
    builder = native_case(
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
    inherited = native_case(
        ["Rain", "falls", "and", "melts"],
        [1, 1, 3, 1],
        ["nsubj", "ROOT", "cc", "conj"],
        ["NOUN", "VERB", "CCONJ", "VERB"],
    )
    assert any(
        t["value"] == "inherited-grammatical-subject" and t["premises"]
        for t in inherited.terms.values()
    )
    local = native_case(
        ["Rain", "falls", "and", "snow", "melts"],
        [1, 1, 4, 4, 1],
        ["nsubj", "ROOT", "cc", "nsubj", "conj"],
        ["NOUN", "VERB", "CCONJ", "NOUN", "VERB"],
    )
    assert not any(t["value"] == "inherited-grammatical-subject" for t in local.terms.values())


def test_native_quantification_has_distinct_variable_restrictor_body():
    builder = native_case(
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
    payload = builder.payload("test-release")
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


def test_released_layer_and_wrong_host_control():
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.characterization import characterization_inputs, validate_layer

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    release = prepare_release(
        characterization_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )
    builder, view = source("Rain falls.")
    builder.region(view, 0, len(view.text))
    payload = builder.payload(release.release_id)
    report = validate_layer(release, payload)
    assert report.payload["roles"]
    invalid = copy.deepcopy(payload)
    role = invalid["roles"][0]
    role["owner"] = next(t["local_id"] for t in invalid["terms"])
    with pytest.raises(ValueError, match=r"witness|endpoint"):
        validate_layer(release, invalid)


def test_source_owned_atoms_are_protected_without_native_or_formal_layers():
    from corpus_structure.methods.construction_characterization import (
        ConstructionCharacterizationMethod,
    )

    text = "A uses x + y."
    builder, view = source(text)
    view.items = (
        dict(self_ref="#/texts/0", label="paragraph"),
        dict(self_ref="#/groups/1", label="inline", parent={"$ref": "#/texts/0"}),
        dict(self_ref="#/texts/1", label="formula", parent={"$ref": "#/groups/1"}),
    )
    view.ancestors = ()
    view.pieces = (
        dict(start=0, end=7, kind="native_text", item_ref="#/texts/0"),
        dict(start=7, end=12, kind="native_text", item_ref="#/texts/1"),
        dict(start=12, end=13, kind="native_text", item_ref="#/texts/0"),
    )
    vocab = English().vocab
    ConstructionCharacterizationMethod._view(
        builder,
        view,
        {},
        vocab,
        PreparedConstructions(vocab),
        SimpleNamespace(
            max_region_chars=4096, parse_seconds=2, math_scope_binders=None, math_domain_rules=()
        ),
        lambda: None,
    )
    atoms = [
        a
        for a in builder.annotations.values()
        if a.get("kind") == "grammar.terminal" and a.get("native_label") == "ATOM"
    ]
    assert atoms
    occurrence = builder.occurrences[atoms[0]["occurrences"][0]]
    assert [(e["start"], e["end"], e["text"]) for e in occurrence["extents"]] == [(7, 12, "x + y")]
    assert any(
        r["outcome"] == "partial" and "native-dependent" in r["reason"] for r in builder.coverage
    )


@pytest.mark.parametrize("gap", [" ", "\t", "\n  "])
def test_retained_working_doc_preserves_whitespace_and_native_named_dependencies(gap):
    from corpus_structure.semantic.characterization import LayerReport
    from corpus_structure.semantic.constructions.matching import retained_documents
    from corpus_structure.semantic.identity import canonical_bytes

    builder, view = source("Rain" + gap + "falls")
    rows = []
    for index, (text, a, b, head, dep, pos) in enumerate(
        (
            ("Rain", 0, 4, 1, "nsubj", "NOUN"),
            ("falls", 4 + len(gap), 9 + len(gap), 1, "ROOT", "VERB"),
        )
    ):
        oid = builder.occurrence(view, a, b)
        rows.append(
            dict(
                local_id=f"native-{index}",
                native_scheme="spacy-token-columns-1",
                occurrences=[oid],
                native_token=dict(
                    index=index,
                    container="block",
                    text=text,
                    lemma=text.lower(),
                    pos=pos,
                    tag="NN",
                    morphology=[],
                    native_head=head,
                    dependency=dep,
                ),
            )
        )
    rows.append(
        dict(
            local_id="block",
            kind="native.block",
            occurrences=[builder.occurrence(view, 0, len(view.text))],
        )
    )
    report = LayerReport(
        canonical_bytes(dict(occurrences=list(builder.occurrences.values()), annotations=rows))
    )
    pin = report.reference(100)
    vocab = English().vocab
    _, _, doc, annotations, _start, _end = next(retained_documents({pin: report}, view, vocab))
    assert doc.text == view.text
    assert len(annotations) == 2
    assert doc.has_annotation("POS", require_complete=True)
    matches, _ = PreparedConstructions(vocab).match(doc)
    assert any(m.rule_id == "tc.native.active.v1" for m in matches)


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


def test_lexical_formal_root_does_not_hide_paragraph_quantifier_or_predicate():
    from corpus_structure.methods.construction_characterization import (
        ConstructionCharacterizationMethod,
    )
    from corpus_structure.semantic.product_reference import ProductReference

    text = "All samples are finite."
    builder, view = source(text)
    view.items = (dict(self_ref="#/texts/0", label="paragraph"),)
    view.ancestors = ()
    pin = ProductReference(task_id=19, product_key="formal", content_digest="d" * 64)
    report = SimpleNamespace(
        payload=dict(
            source_scope=builder.scope,
            occurrences=[
                dict(local_id="parent", extents=[dict(source_view_id=11, start=0, end=len(text))])
            ],
            annotations=[
                dict(
                    local_id="lexical-root",
                    kind="formal.input",
                    family="formal.lexical",
                    occurrences=["parent"],
                    formal_input=dict(parent_occurrence="parent"),
                )
            ],
            memberships=[],
            roles=[],
            terms=[],
            choices=[],
            coverage=[],
        )
    )
    vocab = English().vocab
    ConstructionCharacterizationMethod._view(
        builder,
        view,
        {pin: report},
        vocab,
        PreparedConstructions(vocab),
        SimpleNamespace(
            max_region_chars=4096, parse_seconds=2, math_scope_binders=None, math_domain_rules=()
        ),
        lambda: None,
    )
    assert any(row["kind"] == "binder" for row in builder.terms.values())
    assert any(row["kind"] == "predicate" for row in builder.terms.values())
    assert not any(row.get("native_label") == "ATOM" for row in builder.annotations.values())

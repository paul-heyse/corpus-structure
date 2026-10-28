"""Canonical forms, label normalization and keys (D1 §6.2, §7, §10.1; D5 §3.3, §5.2, §5.3).

Expectations are relations between keys (equal or different) or hand-written canonical forms;
fixtures never pin a hash (D1 §10.1).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from corpus_structure.core.candidates import (
    CandidateStatement,
    KeyedCandidateSet,
)
from corpus_structure.core.evidence import (
    MacroDef,
    RenditionContent,
    Segment,
    SegmentKind,
    content_digest,
    document_key,
    rendition_key,
    segment_key,
)
from corpus_structure.core.keys import (
    KeyContext,
    KeySchema,
    LabelRules,
    Member,
    Rewrite,
    alternative_group_key,
    canonical_condition,
    canonical_value,
    identity_group_key,
    key_claims,
    normalize_label,
    statement_anchor,
    symbol_form,
)

MACROS = {"\\R": MacroDef(body="\\mathbb{R}")}
DOC = document_key("statistics", "special/Test.html", "0" * 64)


def ident(ref: str) -> str:
    return f"key:{ref}"


# --- Label normalization (D5 §3.3 point 5) ---------------------------------------------------

RULES = LabelRules(
    articles=("the", "a", "an"),
    head_words={"DistributionFamily": ("distribution", "distributions")},
    rewrites=(
        Rewrite(match=r"^(\w+)ly distributed$", replace=r"\1"),
        Rewrite(match=r"^(\w+) distributed$", replace=r"\1"),
    ),
)


@pytest.mark.parametrize(
    ("text", "type_", "label"),
    [
        ("The  Normal Distribution", "DistributionFamily", "normal"),
        ("normally distributed", "DistributionFamily", "normal"),
        ("gamma distributed", "DistributionFamily", "gamma"),
        ("the normal distributions", "DistributionFamily", "normal"),
        ("distribution", "DistributionFamily", "distribution"),  # never emptied
        ("The normal distribution", "Concept", "normal distribution"),  # no head words there
        ("the", "Concept", "the"),  # a lone article stays
        ("An  exponential family", "Concept", "exponential family"),
    ],
)
def test_normalize_label(text: str, type_: str, label: str) -> None:
    assert normalize_label(text, type_, RULES) == label


def test_symbols_in_key_form() -> None:
    assert symbol_form("\\mu", MACROS) == "mu"
    assert symbol_form("a + b X", MACROS) == "a+bX"
    assert symbol_form("\\R", MACROS) == "\\mathbb R"
    assert symbol_form("X_{1}", MACROS) == "X_1"


# --- Canonical values ------------------------------------------------------------------------


def cv(value: dict) -> Any:
    return canonical_value(value, MACROS, ident)


def test_canonical_values() -> None:
    assert cv({"t": "text", "v": "  Location-Scale\nFamily "}) == {
        "t": "text", "v": "location-scale family"
    }  # fmt: skip
    assert cv({"t": "number", "v": "30", "unit": " cm "}) == {
        "t": "number",
        "v": "30",
        "unit": "cm",
    }
    assert cv({"t": "number", "v": "30", "unit": "cm"}) != cv(
        {"t": "number", "v": "0.3", "unit": "m"}
    )
    assert cv({"t": "formula", "latex": "b^{2} \\, \\sigma", "symbols": {"b": {"bind": "free"}},
               "sympy": "x", "parse": "ok"}) == {"t": "formula", "latex": "b^2\\sigma"}  # fmt: skip
    assert cv({"t": "set", "latex": "\\R"}) == {"t": "set", "latex": "\\mathbb R"}
    assert cv({"t": "date", "v": "2026-01-31"}) == {"t": "date", "v": "2026-01-31"}
    assert cv({"t": "phrase", "text": "Roughly", "start": 3, "end": 10}) == cv(
        {"t": "phrase", "text": "roughly", "sentence": "s1"}
    )
    assert cv({"t": "interval", "start": {"t": "date", "v": "2026"}, "end_incl": True}) == {
        "t": "interval", "start": {"t": "date", "v": "2026"}, "end_incl": True
    }  # fmt: skip
    assert cv({"ref": "X"}) == {"key": "key:X"}


# --- Canonical conditions --------------------------------------------------------------------


def member(x: str, s: str) -> dict:
    return {"op": "member", "x": {"t": "formula", "latex": x}, "set": {"t": "set", "latex": s}}


def cc(node: dict, symmetric: frozenset[str] = frozenset()) -> Any:
    return canonical_condition(node, MACROS, ident, symmetric)


def test_and_or_flatten_collapse_drop_and_sort() -> None:
    a, b, c = member("a", "\\R"), member("b", "\\R"), {"op": "claim", "ref": "c1"}
    nested = {"op": "and", "args": [a, {"op": "and", "args": [b, {"op": "or", "args": [c]}]}]}
    flat = {"op": "and", "args": [c, b, a]}
    assert cc(nested) == cc(flat)
    assert cc(flat)["op"] == "and" and len(cc(flat)["args"]) == 3
    assert cc({"op": "and", "args": [a]}) == cc(a)
    assert cc({"op": "and", "args": []}) is None
    assert cc({"op": "and", "args": [{"op": "or", "args": []}, a]}) == cc(a)
    assert cc({"op": "not", "arg": {"op": "and", "args": []}}) is None
    # and(or(and(a, b))) collapses to and(a, b), which then flattens into its parent
    deep = {"op": "and", "args": [{"op": "or", "args": [{"op": "and", "args": [a, b]}]}, c]}
    assert cc(deep) == cc(flat)
    assert cc({"op": "or", "args": [a, b]}) != cc({"op": "and", "args": [a, b]})


def test_greater_is_written_as_less_with_sides_swapped() -> None:
    def cmp(rel: str, lhs: str, rhs: str) -> dict:
        return {"op": "cmp", "rel": rel, "lhs": {"t": "formula", "latex": lhs},
                "rhs": {"t": "formula", "latex": rhs}}  # fmt: skip

    assert cc(cmp(">", "t", "1")) == cc(cmp("<", "1", "t"))
    assert cc(cmp(">=", "t", "1")) == cc(cmp("<=", "1", "t"))
    assert cc(cmp("<", "t", "1")) != cc(cmp("<", "1", "t"))


def test_pred_arguments_sorted_only_when_symmetric() -> None:
    xy = {"op": "pred", "name": "independent", "args": [{"ref": "X"}, {"ref": "Y"}]}
    yx = {"op": "pred", "name": "independent", "args": [{"ref": "Y"}, {"ref": "X"}]}
    assert cc(xy) != cc(yx)
    assert cc(xy, frozenset({"independent"})) == cc(yx, frozenset({"independent"}))


def test_phrase_leaves_enter_by_text_alone() -> None:
    stored = {"op": "unsupported", "text": "For  ALL t", "start": 1, "end": 9, "coarse": True,
              "reason": "quantifier"}  # fmt: skip
    authored = {"op": "unsupported", "text": "for all t", "sentence": "s2", "reason": "other"}
    assert cc(stored) == cc(authored) == {"op": "unsupported", "text": "for all t"}
    assert cc({"op": "phrase", "text": "x"}) != cc({"op": "unsupported", "text": "x", "reason": ""})


def test_forall_canonicalizes_its_parts() -> None:
    node = {"op": "forall", "var": "\\mu", "set": {"t": "set", "latex": "\\R"},
            "body": {"op": "and", "args": [member("x_{i}", "\\R")]}}  # fmt: skip
    assert cc(node) == {
        "op": "forall", "var": "mu", "set": {"t": "set", "latex": "\\mathbb R"},
        "body": {"op": "member", "x": {"t": "formula", "latex": "x_i"},
                 "set": {"t": "set", "latex": "\\mathbb R"}},
    }  # fmt: skip


# --- A synthetic page ------------------------------------------------------------------------

PAGE = "special/Test.html"


def page(units: list[list[str]], *, ids: bool = True) -> RenditionContent:
    """Units of one paragraph of sentences each, separated as canonical text separates blocks."""
    text, blocks = "", []
    for i, sentences in enumerate(units):
        if text:
            text += "\n\n"
        start = len(text)
        parts = []
        for sentence in sentences:
            if parts:
                text += " "
            parts.append(Segment(kind=SegmentKind.SENTENCE, start=len(text),
                                 end=len(text) + len(sentence)))  # fmt: skip
            text += sentence
        paragraph = Segment(kind=SegmentKind.PARAGRAPH, start=start, end=len(text), children=parts)
        attrs = {"id": f"u{i + 1}"} if ids else {}
        blocks.append(Segment(kind=SegmentKind.UNIT, start=start, end=len(text), attrs=attrs,
                              children=(paragraph,)))  # fmt: skip
    return RenditionContent(
        canonical_text=text, document=Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text),
                                              children=blocks),
        macros=MACROS,
    )  # fmt: skip


def context(content: RenditionContent) -> KeyContext:
    return KeyContext(DOC, content, PAGE, dict(content.macros))


def seg_key(ctx: KeyContext, segment: Segment) -> str:
    ren = rendition_key(ctx.document_key, content_digest(ctx.content))
    return segment_key(ren, segment.kind, segment.start, segment.end)


def sentences_of(content: RenditionContent) -> list[Segment]:
    return [s for s in content.document.walk() if s.kind is SegmentKind.SENTENCE]


UNITS = [
    ["Suppose that X is normal.", "Then a + b X is normal."],
    ["Recall the gamma function.", "It is positive."],
]


def candidates(ctx: KeyContext, **claim: Any) -> KeyedCandidateSet:
    """X (local to unit 1), N (global), statement st1 at unit 1's sentences, and claims."""
    sentences = sentences_of(ctx.content)
    unit = next(s for s in ctx.content.document.walk() if s.kind is SegmentKind.UNIT)
    base = {"predicate": "has_distribution", "subject": "X", "object": {"ref": "N"},
            "statement": "st1",
            "evidence": [{"start": 0, "end": 5, "role": "primary"}]}  # fmt: skip
    claims = claim.pop("claims", [{"id": "c1", **base, "qualifiers": claim.pop("qualifiers", {})}])
    return KeyedCandidateSet.model_validate({
        "entities": [
            {"id": "X", "type": "RandomVariable", "label": "X", "scope": "local",
             "scope_segment": seg_key(ctx, unit), "symbol": "X"},
            {"id": "N", "type": "DistributionFamily", "label": "the normal distribution",
             "scope": "global"},
            {"id": "S", "type": "Person", "label": "Smith", "scope": "global"},
            {"id": "J", "type": "Person", "label": "Jones", "scope": "global"},
        ],
        "statements": [{"id": "st1", "kind": "theorem",
                        "anchor": [seg_key(ctx, s) for s in sentences[:2]]}],
        "claims": [{**base, **c} for c in claims],
    })  # fmt: skip


SCHEMA = KeySchema(
    identity_qualifiers={"has_distribution": ("param_values",)},
    symmetric_predicates=frozenset({"independent"}),
    predicate_names={"has_distribution": "stat:has_distribution"},
)


def claim_key(qualifiers: dict, **extra: Any) -> str:
    ctx = context(page(UNITS))
    keys = key_claims(candidates(ctx, qualifiers=qualifiers, **extra), ctx, SCHEMA, RULES)
    return keys.claims["c1"]


def interval(start: str, end: str) -> dict:
    return {"t": "interval", "start": {"t": "date", "v": start}, "end": {"t": "date", "v": end}}


def test_defaults_present_or_absent_give_equal_keys() -> None:
    assert claim_key({}) == claim_key({"modality": "asserted", "polarity": "positive"})
    assert claim_key({}) != claim_key({"modality": "supposed"})
    assert claim_key({}) != claim_key({"polarity": "negative"})


def test_permuted_and_arguments_give_equal_keys() -> None:
    a, b = member("a", "\\R"), member("b", "\\R \\setminus \\{0\\}")
    assert claim_key({"conditions": {"op": "and", "args": [a, b]}}) == claim_key(
        {"conditions": {"op": "and", "args": [b, a]}}
    )
    assert claim_key({"conditions": {"op": "and", "args": []}}) == claim_key({})


def test_identity_qualifiers_move_the_key() -> None:
    first = claim_key({"valid_time": interval("2026-01-01", "2026-06-30")})
    second = claim_key({"valid_time": interval("2026-07-01", "2026-12-31")})
    assert first != second != claim_key({})
    smith = claim_key({"modality": "cited", "attribution": {"ref": "S"}})
    jones = claim_key({"modality": "cited", "attribution": {"ref": "J"}})
    assert smith != jones
    pv = {"param_values": {"mean": {"t": "formula", "latex": "\\mu"}}}
    assert claim_key(pv) != claim_key({})
    xy = {"op": "pred", "name": "owns", "args": [{"ref": "S"}, {"ref": "J"}]}
    yx = {"op": "pred", "name": "owns", "args": [{"ref": "J"}, {"ref": "S"}]}
    assert claim_key({"conditions": xy}) != claim_key({"conditions": yx})


def test_parts_outside_the_key_do_not_move_it() -> None:
    plain = claim_key({})
    assert claim_key({"attribution": {"ref": "S"}}) == plain  # attribution outside `cited`
    assert claim_key({"hedge": {"t": "phrase", "text": "roughly", "start": 1, "end": 4}}) == plain
    assert claim_key({"scope": {"extent": "section", "segment": "seg:x"}}) == plain
    assert claim_key({"other_qualifier": {"t": "text", "v": "x"}}) == plain  # not declared
    bound = {"param_values": {"mean": {"t": "formula", "latex": "\\mu",
                                       "symbols": {"mu": {"bind": "free"}}}}}  # fmt: skip
    other = {"param_values": {"mean": {"t": "formula", "latex": "\\mu",
                                       "symbols": {"mu": {"bind": "param_of", "claim": "c1",
                                                          "param": "mean"}}}}}  # fmt: skip
    assert claim_key(bound) == claim_key(other)


def test_content_identical_renditions_give_identical_keys() -> None:
    one = page(UNITS)
    two = RenditionContent.model_validate_json(one.model_dump_json())
    assert content_digest(one) == content_digest(two)
    k1 = key_claims(candidates(context(one)), context(one), SCHEMA, RULES)
    k2 = key_claims(candidates(context(two)), context(two), SCHEMA, RULES)
    assert (k1.entities, k1.statements, k1.claims) == (k2.entities, k2.statements, k2.claims)


# --- Members and groups ----------------------------------------------------------------------


def test_members_differing_only_in_bindings_get_distinct_keys() -> None:
    ctx = context(page(UNITS))
    free = {"t": "formula", "latex": "\\mu", "symbols": {"mu": {"bind": "free"}}}
    bound = {"t": "formula", "latex": "\\mu",
             "symbols": {"mu": {"bind": "param_of", "claim": "c0", "param": "mean"}}}  # fmt: skip
    claims = [
        {"id": "c0", "qualifiers": {"modality": "supposed"}},
        {"id": "c1", "qualifiers": {"param_values": {"mean": free}}},
        {"id": "c2", "qualifiers": {"param_values": {"mean": bound}}},
    ]
    keys = key_claims(candidates(ctx, claims=claims), ctx, SCHEMA, RULES,
                      members={c: Member(bindings=True) for c in ("c1", "c2")})  # fmt: skip
    assert keys.claims["c1"] == keys.claims["c2"]  # one key: bindings are outside it
    assert keys.members["c1"] != keys.members["c2"]
    assert keys.claims["c1"] not in (keys.members["c1"], keys.members["c2"])
    group = alternative_group_key([keys.members["c2"], keys.members["c1"]])
    assert group == alternative_group_key([keys.members["c1"], keys.members["c2"]])
    assert group.startswith("alt:") and identity_group_key(["a", "b"]).startswith("idg:")


def hedge_at(text: str, start: int) -> dict:
    return {"t": "phrase", "text": text, "start": start, "end": start + 3}


def test_members_disagreeing_on_a_qualifier_or_leaving_it_unset() -> None:
    ctx = context(page(UNITS))
    claims = [
        {"id": "c1", "qualifiers": {"hedge": hedge_at("roughly", 1)}},
        {"id": "c2", "qualifiers": {}},
        {"id": "c3", "qualifiers": {"hedge": hedge_at("Roughly", 9)}},
    ]  # fmt: skip
    hedge = Member(qualifiers=("hedge",))
    keys = key_claims(candidates(ctx, claims=claims), ctx, SCHEMA, RULES,
                      members={c: hedge for c in ("c1", "c2", "c3")})  # fmt: skip
    assert len({keys.claims[c] for c in ("c1", "c2", "c3")}) == 1
    assert keys.members["c1"] != keys.members["c2"]  # unset counts as a disagreement
    assert keys.members["c1"] == keys.members["c3"]  # the same phrase by its text form


# --- Batch keying order and cycles -----------------------------------------------------------


def premise(ref: str) -> dict:
    return {"conditions": {"op": "claim", "ref": ref}}


def test_claims_key_in_condition_reference_order() -> None:
    ctx = context(page(UNITS))
    plain = [{"id": "c2", "qualifiers": premise("c1")}, {"id": "c1", "qualifiers": {}}]
    moved = [{"id": "c2", "qualifiers": premise("c1")},
             {"id": "c1", "qualifiers": {"modality": "supposed"}}]  # fmt: skip
    a = key_claims(candidates(ctx, claims=plain), ctx, SCHEMA, RULES)
    b = key_claims(candidates(ctx, claims=moved), ctx, SCHEMA, RULES)
    assert a.dropped == {} and a.claims["c1"] != b.claims["c1"]
    assert a.claims["c2"] != b.claims["c2"]  # the premise's key is part of the conclusion's


def test_a_condition_cycle_is_dropped_with_its_reason() -> None:
    ctx = context(page(UNITS))
    claims = [
        {"id": "c1", "qualifiers": premise("c2")},
        {"id": "c2", "qualifiers": premise("c1")},
        {"id": "c3", "qualifiers": premise("c1")},
        {"id": "c4", "qualifiers": premise("c9")},
        {"id": "c5", "qualifiers": premise("c5")},
        {"id": "c6", "qualifiers": {}},
    ]
    keys = key_claims(candidates(ctx, claims=claims), ctx, SCHEMA, RULES)
    assert set(keys.claims) == {"c6"}
    assert "condition reference cycle: c1 -> c2 -> c1" in keys.dropped["c1"]
    assert "cycle" in keys.dropped["c2"]
    assert keys.dropped["c3"] == "depends on dropped claim 'c1'"
    assert "unknown claim 'c9'" in keys.dropped["c4"]
    assert keys.dropped["c5"] == "condition reference cycle: c5 -> c5"


def test_an_unknown_subject_drops_the_claim() -> None:
    ctx = context(page(UNITS))
    keys = key_claims(candidates(ctx, claims=[{"id": "c1", "subject": "nobody"}]), ctx, SCHEMA,
                      RULES)  # fmt: skip
    assert keys.claims == {} and "nobody" in keys.dropped["c1"]


# --- Entities --------------------------------------------------------------------------------


def entity_keys(entities: list[dict], schema: KeySchema = SCHEMA) -> dict[str, str]:
    ctx = context(page(UNITS))
    unit = next(s for s in ctx.content.document.walk() if s.kind is SegmentKind.UNIT)
    for e in entities:
        if e.get("scope") == "local":
            e.setdefault("scope_segment", seg_key(ctx, unit))
    cands = KeyedCandidateSet.model_validate({"entities": entities})
    return key_claims(cands, ctx, schema, RULES).entities


def test_global_entity_keys() -> None:
    family = {"type": "DistributionFamily", "scope": "global"}
    keys = entity_keys([
        {"id": "a", "label": "The normal distribution", **family},
        {"id": "b", "label": "normally distributed", **family},
        {"id": "c", "label": "gamma distribution", **family},
    ])  # fmt: skip
    assert keys["a"] == keys["b"] != keys["c"]
    schema = KeySchema(
        identity_keys={"FamilyParameter": ("family", "canonical_name")},
        entity_identity={"FamilyParameter": ("family",)},
    )
    param = {"type": "FamilyParameter", "scope": "global"}

    def named(name: str) -> dict:
        return {"family": "N", "canonical_name": name}

    keys = entity_keys([
        {"id": "N", "label": "normal", **family},
        {"id": "p", "label": "location", "identity": named("location"), **param},
        {"id": "q", "label": "the mean", "identity": named("Location"), **param},
        {"id": "r", "label": "location", "identity": {"family": "N"}, **param},
        {"id": "s", "label": "the mean", "identity": {"family": "N"}, **param},
    ], schema)  # fmt: skip
    assert keys["p"] == keys["q"]  # identity complete: the label is not part of the key
    assert keys["r"] != keys["s"]  # incomplete: the normalized label is
    assert keys["p"] != keys["r"]


def test_local_entity_keys() -> None:
    local = {"type": "RandomVariable", "scope": "local"}
    keys = entity_keys([
        {"id": "a", "label": "X", "symbol": "X", **local},
        {"id": "b", "label": "the variable", "symbol": "X", **local},
        {"id": "c", "label": "a + b X", "symbol": "a + b X", **local},
        {"id": "d", "label": "a+bX", "symbol": "a+b X", **local},
        {"id": "e", "label": "the sum", **local},
        {"id": "f", "label": "X", "symbol": "X", "type": "RandomVariable", "scope": "global"},
    ])  # fmt: skip
    assert keys["a"] == keys["b"]  # by symbol, label aside
    assert keys["c"] == keys["d"]  # symbols by token form
    assert len({keys["a"], keys["c"], keys["e"], keys["f"]}) == 4


def test_an_existing_key_is_kept() -> None:
    keys = entity_keys([{"id": "a", "key": "ent:linked", "label": "x", "type": "T",
                         "scope": "global"}])  # fmt: skip
    assert keys["a"] == "ent:linked"


# --- Statements: locators, and edits that stay local -----------------------------------------


def statement_keys(content: RenditionContent) -> dict[str, str]:
    """One statement per sentence of every unit, anchored at that sentence."""
    ctx = context(content)
    statements = [
        CandidateStatement(id=f"st{i}", kind="theorem", anchor=(seg_key(ctx, s),))
        for i, s in enumerate(sentences_of(content))
    ]
    return key_claims(
        KeyedCandidateSet(statements=tuple(statements)), ctx, SCHEMA, RULES
    ).statements


def test_statement_anchor_and_ordinal() -> None:
    content = page(UNITS)
    ctx = context(content)
    sentences = sentences_of(content)
    anchor, ordinal = statement_anchor(
        CandidateStatement(id="s", kind="theorem", anchor=(seg_key(ctx, sentences[1]),)), ctx
    )
    assert (anchor.kind, anchor.attrs["id"], ordinal) == (SegmentKind.UNIT, "u1", 2)
    keys = statement_keys(content)
    assert len(set(keys.values())) == len(keys)


WORDS = ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot"]  # no word prefixes another


@given(
    st.lists(st.lists(st.sampled_from(["x", "y z", "\\(a\\)"]), min_size=1, max_size=3),
             min_size=2, max_size=5),
    st.data(),
    st.booleans(),
)  # fmt: skip
def test_an_edit_inside_one_block_moves_no_other_statement_key(
    tails: list[list[str]], data: st.DataObject, ids: bool
) -> None:
    units = [[f"{WORDS[i]} {tail}." for tail in sentences] for i, sentences in enumerate(tails)]
    edited_unit = data.draw(st.integers(0, len(units) - 1))
    edited_sentence = data.draw(st.integers(0, len(units[edited_unit]) - 1))
    insert = data.draw(st.sampled_from([" more words", " \\(b + c\\)", " and so on"]))
    edited = [list(u) for u in units]
    sentence = edited[edited_unit][edited_sentence]
    edited[edited_unit][edited_sentence] = sentence[:-1] + insert + "."  # opening words kept
    before, after = statement_keys(page(units, ids=ids)), statement_keys(page(edited, ids=ids))
    assert before == after  # sentence ordinals and every anchor locator are unchanged


# --- The trace's T3 rows on the Normal page (D3 §10) -----------------------------------------

DATA = Path(__file__).resolve().parents[1] / "data" / "locators"


def normal_page() -> RenditionContent:
    raw = json.loads((DATA / "special__Normal.json").read_text(encoding="utf-8"))
    return RenditionContent(canonical_text=raw["canonical_text"], document=raw["document"],
                            macros=MACROS)  # fmt: skip


def t3(content: RenditionContent) -> tuple[KeyContext, KeyedCandidateSet]:
    ctx = KeyContext(document_key("statistics", "special/Normal.html", "1" * 64), content,
                     "special/Normal.html", dict(content.macros))  # fmt: skip
    rel1 = ctx.index.resolve("special/Normal.html#rel1")
    paragraph, details = rel1.children
    proof = details.children[1]
    k_rel1, k_paragraph, k_proof = (seg_key(ctx, s) for s in (rel1, paragraph, proof))
    mu = {"t": "formula", "latex": "\\mu", "symbols": {"mu": {"bind": "free"}}}
    sigma2 = {"t": "formula", "latex": "\\sigma^2", "symbols": {"sigma": {"bind": "free"}}}
    in_r = member("a", "\\R")
    in_r0 = member("b", "\\R \\setminus \\{0\\}")
    ev = [{"start": paragraph.start, "end": paragraph.end, "role": "primary"}]
    return ctx, KeyedCandidateSet.model_validate({
        "entities": [
            {"id": "X", "type": "RandomVariable", "label": "X", "symbol": "X", "scope": "local",
             "scope_segment": k_rel1},
            {"id": "Y", "type": "RandomVariable", "label": "a + b X", "symbol": "a + b X",
             "scope": "local", "scope_segment": k_rel1},
            {"id": "N", "type": "DistributionFamily", "label": "normal distribution",
             "scope": "global"},
        ],
        "statements": [
            {"id": "rel1", "kind": "theorem", "anchor": [k_paragraph]},
            {"id": "proof", "kind": "proof", "anchor": [k_proof]},
        ],
        "claims": [
            {"id": "C1", "predicate": "has_distribution", "subject": "X", "object": {"ref": "N"},
             "qualifiers": {"modality": "supposed",
                            "param_values": {"mean": mu, "variance": sigma2}},
             "statement": "rel1", "statement_role": "premise", "evidence": ev},
            {"id": "C2", "predicate": "defined_as", "subject": "Y",
             "object": {"t": "formula", "latex": "a + b X"},
             "qualifiers": {"modality": "defined",
                            "conditions": {"op": "and", "args": [in_r, in_r0]}},
             "statement": "rel1", "statement_role": "definiens", "evidence": ev},
            {"id": "C3", "predicate": "has_distribution", "subject": "Y", "object": {"ref": "N"},
             "qualifiers": {"conditions": {"op": "and", "args": [{"op": "claim", "ref": "C1"},
                                                                  in_r, in_r0]}},
             "statement": "rel1", "statement_role": "conclusion", "evidence": ev},
            {"id": "C4", "predicate": "proves", "subject": "proof", "object": {"ref": "rel1"},
             "statement": "proof", "evidence": ev},
            {"id": "C4s", "predicate": "proves", "subject": "proof", "object": {"ref": "rel1"},
             "statement": "proof", "evidence": ev, "qualifiers": {"modality": "asserted"}},
        ],
    })  # fmt: skip


def test_the_t3_claims_key_deterministically() -> None:
    schema = KeySchema(identity_qualifiers={"has_distribution": ("param_values",)},
                       predicate_names={"proves": "core:proves"})  # fmt: skip
    ctx, cands = t3(normal_page())
    keys = key_claims(cands, ctx, schema, RULES)
    again_ctx, again = t3(normal_page())
    assert keys == key_claims(again, again_ctx, schema, RULES)
    assert keys.dropped == {}
    assert len({keys.claims[c] for c in ("C1", "C2", "C3", "C4")}) == 4
    assert keys.claims["C4"] == keys.claims["C4s"]  # stated and synthesized `proves` share a key
    # the theorem anchors at unit #rel1, the proof at its details block (no id: a prefix locator)
    rel1, ordinal = statement_anchor(cands.statements[0], ctx)
    proof, _ = statement_anchor(cands.statements[1], ctx)
    assert ctx.locator_key(rel1) == {"doc": ctx.document_key, "id": "rel1"} and ordinal == 1
    assert ctx.locator_key(proof)["kind"] == "details"
    assert keys.statements["rel1"] != keys.statements["proof"]


def test_what_an_edit_can_move() -> None:
    """Negative controls for the property above (D1 §10.3)."""
    units = [["Alpha x.", "Alpha y."], ["Bravo x."]]
    base = statement_keys(page(units, ids=False))
    renamed = statement_keys(page([["Charlie x.", "Charlie y."], ["Bravo x."]], ids=False))
    assert renamed["st0"] != base["st0"] and renamed["st2"] == base["st2"]
    assert (
        statement_keys(page([["Charlie x.", "Charlie y."], ["Bravo x."]]))["st0"]
        == (statement_keys(page(units))["st0"])
    )  # an author id anchors through a change of opening words
    inserted = statement_keys(page([["Alpha w.", "Alpha x.", "Alpha y."], ["Bravo x."]],
                                   ids=False))  # fmt: skip
    # Keys follow the anchor and the ordinal (D1 §10.3): a sentence inserted first takes ordinal
    # 1's key, and the sentences after it move to the next ordinals' keys.
    assert inserted["st0"] == base["st0"] and inserted["st1"] == base["st1"]
    assert inserted["st2"] not in base.values()
    assert inserted["st3"] == base["st2"]


def test_equivalent_formulas_key_apart_and_the_key_format() -> None:
    """Ported from the spike's TestKeys: keys use the token form, never SymPy equivalence (fusion of
    equivalent formulas is C1's, D5 §5.3); every key is a prefix and 32 hex digits."""

    def with_mean(latex: str) -> str:
        return claim_key({"param_values": {"mean": {"t": "formula", "latex": latex}}})

    assert with_mean("a + b \\mu") != with_mean("\\mu b + a")
    assert with_mean("a + b \\mu") == with_mean("a+b\\,\\mu")
    ctx, cands = t3(normal_page())
    keys = key_claims(cands, ctx, SCHEMA, RULES)
    for key in (*keys.entities.values(), *keys.statements.values(), *keys.claims.values()):
        prefix, digits = key.split(":")
        assert prefix in ("ent", "stm", "clm") and len(digits) == 32
        assert int(digits, 16) >= 0

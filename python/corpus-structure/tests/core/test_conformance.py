"""Conformance vector v1: key scheme 1's hand-authored known answers (foundations §3.6; RC07, R12).

Each entry is an input and its key parts written out by hand, as canonical JSON bytes, from D1
§10.1 (which parts), TM §8 (each range's canonical form) and D1 §6.2, §7 (text, token and condition
forms). The expected key is computed here with `hashlib` over those bytes, never through
`make_key` or `canonical_json`, so the answers do not derive from the code under test. A key that
names another (a claim's subject, an `xrf`'s citing statement) is filled in from that entry's own
hand-computed key, bottom-up.

Scheme 1 froze at P0-F-2e, after `s5.keys-property` froze `core/tex.py`. Any change to an output
here is a key-bearing change (M4): a new scheme, a carry-over map and a new vector, never an edit
of v1. A seeded change to one canonical form fails the vector (the last tests).
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from corpus_structure.core import keys as keys_module
from corpus_structure.core.candidates import KeyedCandidateSet
from corpus_structure.core.evidence import (
    MacroDef,
    RenditionContent,
    Segment,
    SegmentKind,
    document_key,
    segment_key,
)
from corpus_structure.core.keys import (
    KeyContext,
    Keys,
    KeySchema,
    LabelRules,
    Rewrite,
    alternative_group_key,
    key_claims,
)

VECTOR = "v1"
SCHEME = 1


def key(prefix: str, parts: bytes) -> str:
    """D1 §10.1: the prefix and the first 32 hex digits of the SHA-256 of the parts' canonical
    JSON, written here by hand."""
    return f"{prefix}:{hashlib.sha256(parts).hexdigest()[:32]}"


def fill(template: bytes, **keys: str) -> bytes:
    """A hand-written template with `<name>` replaced by another entry's hand-computed key."""
    for name, value in keys.items():
        template = template.replace(f"<{name}>".encode(), value.encode())
    return template


# --- The inputs --------------------------------------------------------------------------------

PAGE = "special/Vector.html"
SENTENCES = {
    "u1": ["Let X be normal.", "The last result applies."],
    "u2": ["It holds for mu."],
}
MACROS = {"\\R": MacroDef(body="\\mathbb{R}")}


def rendition() -> RenditionContent:
    """Two units with author ids, each one paragraph of sentences."""
    text, units = "", []
    for unit_id, sentences in SENTENCES.items():
        if text:
            text += "\n\n"
        start, parts = len(text), []
        for sentence in sentences:
            if parts:
                text += " "
            parts.append(Segment(kind=SegmentKind.SENTENCE, start=len(text),
                                 end=len(text) + len(sentence)))  # fmt: skip
            text += sentence
        paragraph = Segment(kind=SegmentKind.PARAGRAPH, start=start, end=len(text), children=parts)
        units.append(Segment(kind=SegmentKind.UNIT, start=start, end=len(text),
                             attrs={"id": unit_id}, children=(paragraph,)))  # fmt: skip
    return RenditionContent(
        canonical_text=text,
        document=Segment(kind=SegmentKind.DOCUMENT, start=0, end=len(text), children=units),
        macros=MACROS,
    )


DOC_KEY = document_key("statistics", PAGE, "0" * 64)
CTX = KeyContext(DOC_KEY, rendition(), PAGE, MACROS)


def seg(kind: SegmentKind, n: int) -> str:
    segment = [s for s in CTX.content.document.walk() if s.kind is kind][n]
    return segment_key(CTX.rendition_key, segment.kind, segment.start, segment.end)


def span(text: str) -> dict[str, int]:
    start = CTX.content.canonical_text.index(text)
    return {"start": start, "end": start + len(text)}


RULES = LabelRules(
    articles=("the",),
    head_words={"stat:DistributionFamily": ("distribution",)},
    rewrites=(Rewrite(match=r"^(\w+)ly distributed$", replace=r"\1"),),
)
SCHEMA = KeySchema(
    predicates=frozenset({"stat:p", "core:follows_from"}),
    identity_keys={"stat:FamilyParameter": ("stat:family", "stat:canonical_name")},
    entity_identity={"stat:FamilyParameter": ("stat:family",)},
)
EVIDENCE = [{"start": 0, "end": 3, "role": "primary"}]
OBJECTS: dict[str, Any] = {  # one claim per range form of a claim object (TM §8)
    "c_text": {"t": "text", "v": "  Location-Scale\nFamily "},
    "c_number": {"t": "number", "v": "1.5", "unit": " m ", "basis": "per  year"},
    "c_bool": {"t": "bool", "v": True},
    "c_enum": {"t": "enum", "enum": "stat:Shape", "v": "Rate"},
    "c_formula": {"t": "formula", "latex": "a + b X",
                  "symbols": {"X": {"bind": "variable", "entity": "X"}}},
    "c_set": {"t": "set", "latex": "\\R"},
    "c_date": {"t": "date", "v": "2026-01-31"},
    "c_interval": {"t": "interval", "start": {"t": "number", "v": "0"},
                   "end": {"t": "formula", "latex": "\\infty"}, "start_incl": True},
    "c_phrase": {"t": "phrase", "text": "Roughly  Normal", "start": 0, "end": 3},
    "c_entity": {"ref": "N"},
}  # fmt: skip


def candidates() -> KeyedCandidateSet:
    claims = [
        {
            "id": cid,
            "predicate": "stat:p",
            "subject": "X",
            "object": obj,
            "statement": "st1",
            "evidence": EVIDENCE,
        }
        for cid, obj in OBJECTS.items()
    ]
    claims += [
        {"id": "c_cond", "predicate": "stat:p", "subject": "X", "object": {"ref": "N"},
         "statement": "st1", "evidence": EVIDENCE,
         "qualifiers": {
             "core:modality": "supposed", "core:polarity": "negative",
             "core:conditions": {"op": "and", "args": [
                 {"op": "member", "x": {"t": "formula", "latex": "a"},
                  "set": {"t": "set", "latex": "\\R"}},
                 {"op": "cmp", "rel": ">", "lhs": {"t": "formula", "latex": "t"},
                  "rhs": {"t": "formula", "latex": "1"}},
             ]},
         }},
        {"id": "c_xrf", "predicate": "core:follows_from", "subject": "st2",
         "object": {"ref": "xr"}, "statement": "st2", "evidence": EVIDENCE},
    ]  # fmt: skip
    return KeyedCandidateSet.model_validate({
        "renditions": [CTX.rendition_key],
        "entities": [
            {"id": "X", "type": "stat:RandomVariable", "label": "X", "symbol": "X",
             "scope": "local", "scope_segment": seg(SegmentKind.UNIT, 0)},
            {"id": "M", "type": "stat:RandomVariable", "label": "mu", "symbol": "\\mu",
             "scope": "local", "scope_segment": seg(SegmentKind.UNIT, 1)},
            {"id": "N", "type": "stat:DistributionFamily", "label": "The  Normal Distribution",
             "scope": "global"},
            {"id": "P", "type": "stat:FamilyParameter", "label": "the mean", "scope": "global",
             "identity": {"stat:family": "N", "stat:canonical_name": "Location"}},
        ],
        "statements": [
            {"id": "st1", "kind": "theorem", "anchor": [seg(SegmentKind.SENTENCE, 0)]},
            {"id": "st2", "kind": "corollary", "anchor": [seg(SegmentKind.SENTENCE, 1)]},
            {"id": "st3", "kind": "remark", "anchor": [seg(SegmentKind.SENTENCE, 2)]},
        ],
        "references": [
            {"id": "xr", "descriptor": {**span("The last result"),
                                        "target": "special/Normal.html#thm3"}},
        ],
        "claims": claims,
    })  # fmt: skip


# --- The hand-written parts --------------------------------------------------------------------

# doc: project, source URI, original bytes' hash (D1 §10.1)
DOC = key("doc", b'{"content_hash":"' + b"0" * 64
          + b'","project":"statistics","source_uri":"special/Vector.html"}')  # fmt: skip
# stm: the anchor's structured locator (an id-bearing unit: the document key and the id) and the
# 1-based ordinal of the first sentence among the anchor's sentences
STM_1 = key("stm", fill(b'{"anchor":{"doc":"<doc>","id":"u1"},"ordinal":1}', doc=DOC))
STM_2 = key("stm", fill(b'{"anchor":{"doc":"<doc>","id":"u1"},"ordinal":2}', doc=DOC))
STM_3 = key("stm", fill(b'{"anchor":{"doc":"<doc>","id":"u2"},"ordinal":1}', doc=DOC))
# ent, local: type, scope locator, the symbol in key form (`\mu` is `mu`)
ENT_X = key("ent", fill(b'{"scope":{"doc":"<doc>","id":"u1"},"symbol":"X",'
                        b'"type":"stat:RandomVariable"}', doc=DOC))  # fmt: skip
ENT_M = key("ent", fill(b'{"scope":{"doc":"<doc>","id":"u2"},"symbol":"mu",'
                        b'"type":"stat:RandomVariable"}', doc=DOC))  # fmt: skip
# ent, global without declared identity: the normalized label ("the" dropped, head word dropped)
ENT_N = key("ent", b'{"identity":{},"label":"normal","type":"stat:DistributionFamily"}')
# ent, global with complete identity: the entity slot's key and the literal's text form; no label
ENT_P = key("ent", fill(b'{"identity":{"stat:canonical_name":"location","stat:family":"<n>"},'
                        b'"type":"stat:FamilyParameter"}', n=ENT_N))  # fmt: skip
# xrf: the citing statement's key, the quote's text form, the link target as written
XRF = key("xrf", fill(b'{"quote":"the last result","statement":"<st>",'
                      b'"target":"special/Normal.html#thm3"}', st=STM_2))  # fmt: skip

# clm: subject, prefixed predicate, {key} or {value: canonical}, statement, identity qualifiers.
# Each object's canonical form, written from TM §8 (JSON-escaped: `\\` is one backslash).
OBJECT_PARTS: dict[str, bytes] = {
    "c_text": b'{"value":{"t":"text","v":"location-scale family"}}',
    "c_number": b'{"value":{"basis":"per year","t":"number","unit":"m","v":"1.5"}}',
    "c_bool": b'{"value":{"t":"bool","v":true}}',
    "c_enum": b'{"value":{"enum":"stat:Shape","t":"enum","v":"Rate"}}',
    "c_formula": b'{"value":{"latex":"a+bX","t":"formula"}}',
    "c_set": b'{"value":{"latex":"\\\\mathbb R","t":"set"}}',
    "c_date": b'{"value":{"t":"date","v":"2026-01-31"}}',
    "c_interval": b'{"value":{"end":{"latex":"\\\\infty","t":"formula"},'
                  b'"start":{"t":"number","v":"0"},"start_incl":true,"t":"interval"}}',
    "c_phrase": b'{"value":{"t":"phrase","text":"roughly normal"}}',
    "c_entity": b'{"key":"<n>"}',
}  # fmt: skip


def claim(obj: bytes, qualifiers: bytes = b"{}", predicate: bytes = b"stat:p",
          subject: str = ENT_X, statement: str = STM_1) -> str:  # fmt: skip
    parts = (b'{"object":' + obj + b',"predicate":"' + predicate + b'","qualifiers":'
             + qualifiers + b',"statement":"<st>","subject":"<subject>"}')  # fmt: skip
    return key("clm", fill(parts, st=statement, subject=subject, n=ENT_N))


CLM = {cid: claim(obj) for cid, obj in OBJECT_PARTS.items()}
# the condition tree: `>` as `<` with the sides swapped, `and` arguments sorted by canonical JSON
# ('{"lhs"…' before '{"op"…'), the macro expanded; modality and polarity enter when not default
CLM["c_cond"] = claim(
    b'{"key":"<n>"}',
    b'{"core:conditions":{"args":['
    b'{"lhs":{"latex":"1","t":"formula"},"op":"cmp","rel":"<","rhs":{"latex":"t","t":"formula"}},'
    b'{"op":"member","set":{"latex":"\\\\mathbb R","t":"set"},"x":{"latex":"a","t":"formula"}}'
    b'],"op":"and"},"core:modality":"supposed","core:polarity":"negative"}',
)
# a claim citing the unresolved external reference keys it by its xrf key
CLM["c_xrf"] = claim(fill(b'{"key":"<xrf>"}', xrf=XRF), predicate=b"core:follows_from",
                     subject=STM_2, statement=STM_2)  # fmt: skip


@pytest.fixture(scope="module")
def keyed() -> Keys:
    return key_claims(candidates(), CTX, SCHEMA, RULES)


def test_the_vector_is_scheme_1(keyed: Keys) -> None:
    assert (VECTOR, keyed.scheme, SCHEMA.key_scheme) == ("v1", SCHEME, SCHEME)
    assert keyed.dropped == {}


def test_the_document_key(keyed: Keys) -> None:
    assert DOC_KEY == DOC


def test_statement_keys(keyed: Keys) -> None:
    assert keyed.statements == {"st1": STM_1, "st2": STM_2, "st3": STM_3}


def test_entity_keys(keyed: Keys) -> None:
    assert keyed.entities == {"X": ENT_X, "M": ENT_M, "N": ENT_N, "P": ENT_P}


def test_the_external_reference_key(keyed: Keys) -> None:
    assert keyed.references == {"xr": XRF}


@pytest.mark.parametrize("claim_id", list(CLM))
def test_claim_keys(keyed: Keys, claim_id: str) -> None:
    assert keyed.claims[claim_id] == CLM[claim_id]


def test_an_alternative_group_key(keyed: Keys) -> None:
    members = sorted((CLM["c_text"], CLM["c_bool"]))
    parts = b'["' + members[0].encode() + b'","' + members[1].encode() + b'"]'
    assert alternative_group_key((keyed.claims["c_text"], keyed.claims["c_bool"])) == key(
        "alt", parts
    )


# --- A seeded canonical-form change fails the vector -------------------------------------------


def mismatches(keyed: Keys) -> set[str]:
    want = {**{f"stm/{k}": v for k, v in (("st1", STM_1), ("st2", STM_2), ("st3", STM_3))},
            **{f"ent/{k}": v for k, v in (("X", ENT_X), ("M", ENT_M), ("N", ENT_N),
                                           ("P", ENT_P))},
            "xrf/xr": XRF, **{f"clm/{k}": v for k, v in CLM.items()}}  # fmt: skip
    got = {**{f"stm/{k}": v for k, v in keyed.statements.items()},
           **{f"ent/{k}": v for k, v in keyed.entities.items()},
           **{f"xrf/{k}": v for k, v in keyed.references.items()},
           **{f"clm/{k}": v for k, v in keyed.claims.items()}}  # fmt: skip
    return {name for name in want if got.get(name) != want[name]}


@pytest.mark.parametrize(
    ("target", "seeded", "moved"),
    [
        # the text form stops casefolding: labels, quotes, text and phrases move, and every key
        # that names a moved one (N is the object of c_entity and c_cond; xr of c_xrf)
        ("text_form", lambda text, case=None: " ".join(text.split()),
         {"ent/N", "ent/P", "xrf/xr", "clm/c_text", "clm/c_phrase", "clm/c_entity", "clm/c_cond",
          "clm/c_xrf"}),
        # the token form keeps the source spelling: formulas and sets not already in token form
        # move (`\mu` and `\infty` are; `a + b X`, `\R` and the condition's `\R` are not)
        ("token_form", lambda latex, macros=None: latex,
         {"clm/c_formula", "clm/c_set", "clm/c_cond"}),
    ],
)  # fmt: skip
def test_a_seeded_canonical_form_change_fails_the_vector(
    monkeypatch: pytest.MonkeyPatch, target: str, seeded, moved: set[str]
) -> None:
    assert mismatches(key_claims(candidates(), CTX, SCHEMA, RULES)) == set()
    monkeypatch.setattr(keys_module, target, seeded)
    assert mismatches(key_claims(candidates(), CTX, SCHEMA, RULES)) == moved

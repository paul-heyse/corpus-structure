"""D1 shapes in both forms, payloads, ops JSON and the JSON Schema files (foundations §6 F2b).

jsonschema is the independent oracle: every dumped instance must satisfy the committed schema file,
which Pydantic generated but jsonschema validates by its own implementation.
"""

from __future__ import annotations

import copy
import functools
import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis_jsonschema import from_schema
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from corpus_structure.core import schemas
from corpus_structure.core.batch import (
    AuthoredBatch,
    AuthoredQualifiers,
    CitationFrame,
    StoredBatch,
    cited_sentences,
)
from corpus_structure.core.payloads import PAYLOADS, ClaimProposalPayload, validate_payload
from corpus_structure.core.values import (
    CONDITION_ADAPTERS,
    VALUE_ADAPTERS,
    SymbolBinding,
)
from corpus_structure.core.vocab import ObservationKind

REPO = Path(__file__).resolve().parents[4]
V1 = REPO / "docs/design_review/evidence/2026-10-28_design-spikes/results/s0r2/reference_model_v1"
SCHEMA_DIR = schemas.DIRECTORY


def schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / f"{name}.json").read_text(encoding="utf-8"))


def validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(schema(name))


# --- Strategies over JSON (hand-written: the condition and batch schemas are recursive) -------

SYMBOLS = st.sampled_from(["a", "b", "X", "\\mu", "\\sigma"])
LATEX = st.sampled_from(["a", "b^{2}", "a + b \\mu", "\\R", "(0, \\infty)", "\\sigma^2"])
TEXT = st.text(min_size=1, max_size=12)
REF = st.sampled_from(["X", "N", "c1", "st1"])


def binding() -> st.SearchStrategy[dict]:
    return st.one_of(
        st.builds(lambda k, e: {"bind": k, "entity": e},
                  st.sampled_from(["variable", "family_param"]), REF),
        st.builds(lambda k, c, p: {"bind": k, "claim": c, "param": p},
                  st.sampled_from(["param_of", "param_expr_of"]), REF, TEXT),
        st.builds(lambda k: {"bind": k}, st.sampled_from(["free", "constant", "unresolved"])),
    )  # fmt: skip


def expression(t: str) -> st.SearchStrategy[dict]:
    return st.builds(
        lambda latex, symbols: {"t": t, "latex": latex, "symbols": symbols},
        LATEX,
        st.dictionaries(SYMBOLS, binding(), max_size=3),
    )


NUMBER = st.builds(
    lambda v, unit: {"t": "number", "v": v, **({"unit": unit} if unit else {})},
    st.from_regex(r"0|-?[1-9][0-9]{0,4}(\.[0-9]{0,3}[1-9])?", fullmatch=True),
    st.sampled_from([None, "cm", "kPa"]),
)
DATE = st.builds(lambda v: {"t": "date", "v": v}, st.sampled_from(["2026", "2026-01-31"]))


def phrase(form: str, tag: dict) -> st.SearchStrategy[dict]:
    if form == "authored":
        return st.builds(lambda text, s: {**tag, "text": text, **({"sentence": s} if s else {})},
                         TEXT, st.sampled_from([None, "s1", "c2"]))  # fmt: skip
    return st.builds(lambda text, a, n: {**tag, "text": text, "start": a, "end": a + n},
                     TEXT, st.integers(0, 50), st.integers(1, 9))  # fmt: skip


def value(form: str) -> st.SearchStrategy[dict]:
    return st.one_of(
        st.builds(lambda v: {"t": "text", "v": v}, TEXT),
        NUMBER,
        st.builds(lambda v: {"t": "bool", "v": v}, st.booleans()),
        st.builds(lambda e, v: {"t": "enum", "enum": e, "v": v}, TEXT, TEXT),
        expression("formula"),
        expression("set"),
        DATE,
        st.builds(lambda s, e: {"t": "interval", **({"start": s} if s else {}),
                                **({"end": e} if e else {})},
                  st.none() | NUMBER | DATE, st.none() | NUMBER | DATE),
        phrase(form, {"t": "phrase"}),
    )  # fmt: skip


def condition(form: str) -> st.SearchStrategy[dict]:
    leaves = st.one_of(
        st.builds(lambda r: {"op": "claim", "ref": r}, REF),
        st.builds(lambda x, s: {"op": "member", "x": x, "set": s},
                  expression("formula"), expression("set")),
        st.builds(lambda r, lhs, rhs: {"op": "cmp", "rel": r, "lhs": lhs, "rhs": rhs},
                  st.sampled_from(["<", "<=", "=", "!=", ">", ">="]),
                  expression("formula"), expression("formula")),
        st.builds(lambda n, a: {"op": "pred", "name": n, "args": a}, TEXT,
                  st.lists(st.builds(lambda r: {"ref": r}, REF) | expression("formula"),
                           min_size=1, max_size=3)),
        phrase(form, {"op": "phrase"}),
        phrase(form, {"op": "unsupported"}).map(lambda d: {**d, "reason": "r"}),
    )  # fmt: skip
    return st.recursive(
        leaves,
        lambda inner: st.one_of(
            st.builds(lambda a: {"op": "and", "args": a}, st.lists(inner, max_size=3)),
            st.builds(lambda a: {"op": "or", "args": a}, st.lists(inner, max_size=3)),
            st.builds(lambda a: {"op": "not", "arg": a}, inner),
            st.builds(
                lambda v, s, b: {"op": "forall", "var": v, "set": s, "body": b},
                SYMBOLS,
                expression("set"),
                inner,
            ),
        ),
        max_leaves=8,
    )


FORMS = ("authored", "stored")


@pytest.mark.parametrize("form", FORMS)
@given(data=st.data())
def test_values_round_trip_and_satisfy_the_schema(form: str, data: st.DataObject) -> None:
    raw = data.draw(value(form))
    adapter = VALUE_ADAPTERS[form]
    model = adapter.validate_python(raw)
    dumped = json.loads(adapter.dump_json(model))
    assert dumped == raw
    assert adapter.validate_json(json.dumps(raw), strict=True) == model
    validator(f"value.{form}").validate(dumped)


@pytest.mark.parametrize("form", FORMS)
@given(data=st.data())
def test_conditions_round_trip_and_satisfy_the_schema(form: str, data: st.DataObject) -> None:
    raw = data.draw(condition(form))
    adapter = CONDITION_ADAPTERS[form]
    model = adapter.validate_json(json.dumps(raw), strict=True)
    dumped = json.loads(adapter.dump_json(model))
    assert dumped == raw
    validator(f"condition.{form}").validate(dumped)


NON_RECURSIVE = sorted(
    name for name in schemas.SCHEMAS() if not name.startswith(("condition", "batch"))
    and name != "payload.claim_proposal"
)  # fmt: skip


@functools.cache
def drawn(name: str) -> st.SearchStrategy[Any]:
    return from_schema({k: v for k, v in schema(name).items() if k != "$schema"})


@pytest.mark.parametrize("name", NON_RECURSIVE)
@settings(max_examples=40)
@given(data=st.data())
def test_schema_drawn_instances_round_trip(name: str, data: st.DataObject) -> None:
    # Draw from the schema; whatever Pydantic accepts must dump back to a schema-valid equal value.
    instance = data.draw(drawn(name))
    adapter = schemas.SCHEMAS()[name]
    try:
        model = adapter.validate_python(instance)
    except ValidationError:
        return  # a model rule the schema cannot state (span order, binding fields, one-of)
    dumped = json.loads(adapter.dump_json(model))
    validator(name).validate(dumped)
    assert adapter.validate_python(dumped) == model


# --- Per-form refusals ---------------------------------------------------------------------------


def errors(adapter: Any, raw: Any) -> list[tuple[str, str]]:
    with pytest.raises(ValidationError) as caught:
        adapter.validate_python(raw)
    return [(".".join(map(str, e["loc"])), e["type"]) for e in caught.value.errors()]


def test_an_offset_in_the_authored_form_is_refused_at_its_path() -> None:
    raw = {"op": "and", "args": [{"op": "phrase", "text": "x", "start": 1, "end": 2}]}
    assert ("and.args.0.phrase.start", "extra_forbidden") in errors(
        CONDITION_ADAPTERS["authored"], raw
    )
    stored = {"op": "and", "args": [{"op": "phrase", "text": "x", "sentence": "s1"}]}
    found = errors(CONDITION_ADAPTERS["stored"], stored)
    assert ("and.args.0.phrase.sentence", "extra_forbidden") in found
    assert ("and.args.0.phrase.start", "missing") in found


def test_a_non_canonical_number_is_refused_with_its_canonical_spelling() -> None:
    with pytest.raises(ValidationError, match=r"'2\.50' is not a canonical decimal; write '2\.5'"):
        VALUE_ADAPTERS["stored"].validate_python({"t": "number", "v": "2.50"})
    with pytest.raises(ValidationError, match="not a decimal number"):
        VALUE_ADAPTERS["stored"].validate_python({"t": "number", "v": "two"})


def test_optional_fields_are_absent_never_null() -> None:
    with pytest.raises(ValidationError):
        VALUE_ADAPTERS["stored"].validate_python({"t": "number", "v": "1", "unit": None})
    plain = VALUE_ADAPTERS["stored"].validate_python({"t": "number", "v": "1"})
    assert VALUE_ADAPTERS["stored"].dump_python(plain, mode="json") == {"t": "number", "v": "1"}


def test_entity_references_have_one_shape() -> None:
    raw = {"op": "pred", "name": "independent", "args": [{"t": "entity", "ref": "X"}]}
    assert ("pred.args.0.EntityRef.t", "extra_forbidden") in errors(
        CONDITION_ADAPTERS["stored"], raw
    )
    with pytest.raises(ValidationError):
        VALUE_ADAPTERS["stored"].validate_python({"t": "entity", "ref": "X"})


@pytest.mark.parametrize(
    ("raw", "ok"),
    [
        ({"bind": "variable", "entity": "X"}, True),
        ({"bind": "variable"}, False),
        ({"bind": "variable", "entity": "X", "param": "mean"}, False),
        ({"bind": "param_of", "claim": "c1", "param": "mean"}, True),
        ({"bind": "param_of", "claim": "c1"}, False),
        ({"bind": "free"}, True),
        ({"bind": "free", "entity": "X"}, False),
        ({"bind": "bound"}, False),
    ],
)
def test_binding_fields_follow_the_kind(raw: dict, ok: bool) -> None:
    if ok:
        assert SymbolBinding.model_validate(raw).model_dump(mode="json") == raw
    else:
        with pytest.raises(ValidationError):
            SymbolBinding.model_validate(raw)


def test_qualifier_defaults_are_filled_and_omitted() -> None:
    q = AuthoredQualifiers.model_validate({"modality": "asserted", "param_values": {"k": 1}})
    assert q.modality == "asserted" and q.polarity == "positive"
    assert q.model_dump(mode="json") == {"param_values": {"k": 1}}
    assert AuthoredQualifiers.model_validate({"modality": "asserted"}) == AuthoredQualifiers()
    negative = AuthoredQualifiers.model_validate({"polarity": "negative", "scope": "section"})
    assert negative.model_dump(mode="json") == {"polarity": "negative", "scope": "section"}


# --- Batches ---------------------------------------------------------------------------------


def v1(unit: str) -> dict:
    return json.loads((V1 / f"{unit}.json").read_text(encoding="utf-8"))


def entity_refs_canonical(node: Any) -> Any:
    """S4's V1 rewrite: `{t: entity, ref}` becomes the one entity-reference shape `{ref}`."""
    if isinstance(node, dict):
        if node.get("t") == "entity" and set(node) == {"t", "ref"}:
            return {"ref": node["ref"]}
        return {k: entity_refs_canonical(v) for k, v in node.items()}
    if isinstance(node, list):
        return [entity_refs_canonical(v) for v in node]
    return node


V1_UNITS = ("T1", "T2", "T3", "T4", "U5", "U6", "U7", "U8", "U9", "U10", "U11", "U12")


@pytest.mark.parametrize("unit", V1_UNITS)
def test_the_v1_reference_batches_validate_and_round_trip(unit: str) -> None:
    raw = entity_refs_canonical(v1(unit))
    batch = AuthoredBatch.model_validate_json(json.dumps(raw), strict=True)
    dumped = batch.model_dump(mode="json")
    validator("batch.authored").validate(dumped)
    assert AuthoredBatch.model_validate_json(batch.model_dump_json(), strict=True) == batch
    assert cited_sentences(batch)


def test_v1_pred_arguments_needed_the_entity_reference_rewrite() -> None:
    with pytest.raises(ValidationError, match=r"EntityRef\.t"):
        AuthoredBatch.model_validate(v1("U11"))


def test_batch_refusals() -> None:
    raw = entity_refs_canonical(v1("T3"))
    duplicate = copy.deepcopy(raw)
    duplicate["claims"][1]["local_ref"] = duplicate["entities"][0]["local_ref"]
    with pytest.raises(ValidationError, match="is used by entities and claims"):
        AuthoredBatch.model_validate(duplicate)
    m11 = copy.deepcopy(raw)
    m11["claims"][1]["object"]["sympy"] = "Symbol('a')"
    with pytest.raises(ValidationError, match="set by M11 only"):
        AuthoredBatch.model_validate(m11)
    no_evidence = copy.deepcopy(raw)
    no_evidence["claims"][0]["evidence"] = []
    with pytest.raises(ValidationError):
        AuthoredBatch.model_validate(no_evidence)
    global_extent = copy.deepcopy(raw)
    global_extent["entities"][2]["extent"] = "section"
    with pytest.raises(ValidationError, match="only a local entity has an extent"):
        AuthoredBatch.model_validate(global_extent)


def stored_t3() -> dict:
    """A hand-made stored form of a T3-like batch (offsets and keys are placeholders)."""
    return {
        "unit_ref": "special/Normal.html#rel1",
        "entities": [
            {"local_ref": "X", "type": "RandomVariable", "label": "X", "scope": "local",
             "extent": "statement", "symbol": "X", "scope_segment": "seg:1"},
            {"local_ref": "N", "type": "DistributionFamily", "label": "normal distribution",
             "scope": "global", "aliases": ["normally distributed"]},
        ],
        "statements": [{"local_ref": "st1", "kind": "theorem", "anchor": ["seg:2"]}],
        "claims": [
            {"local_ref": "c1", "predicate": "has_distribution", "subject": "X",
             "object": {"ref": "N"}, "qualifiers": {"modality": "supposed"}, "statement": "st1",
             "statement_role": "premise",
             "evidence": [{"start": 10, "end": 40, "role": "primary"}]},
        ],
        "unsupported": [{"local_ref": "u1", "start": 41, "end": 50, "reason": "r",
                         "coarse": True}],
    }  # fmt: skip


def test_the_stored_form() -> None:
    batch = StoredBatch.model_validate_json(json.dumps(stored_t3()), strict=True)
    validator("batch.stored").validate(batch.model_dump(mode="json"))
    no_segment = stored_t3()
    del no_segment["entities"][0]["scope_segment"]
    with pytest.raises(ValidationError, match="scope_segment exactly when it is local"):
        StoredBatch.model_validate(no_segment)
    empty = stored_t3()
    empty["claims"][0]["evidence"][0]["end"] = 10
    with pytest.raises(ValidationError, match="empty or reversed"):
        StoredBatch.model_validate(empty)
    sentence = stored_t3()
    sentence["claims"][0]["evidence"][0]["sentence"] = "s1"
    with pytest.raises(ValidationError, match="Extra inputs"):
        StoredBatch.model_validate(sentence)


# --- Payloads --------------------------------------------------------------------------------


def test_every_observation_kind_has_a_payload_model() -> None:
    assert set(PAYLOADS) == set(ObservationKind)


def test_claim_proposal_authored_and_frame_come_together() -> None:
    frame = {"s1": {"locator": "special/Normal.html@sentence:Suppose", "text": "Suppose X."}}
    authored = entity_refs_canonical(v1("U7"))
    ok = {"batch": stored_t3(), "authored": authored, "citation_frame": frame}
    payload = validate_payload("claim_proposal", ok)
    assert isinstance(payload, ClaimProposalPayload)
    validator("payload.claim_proposal").validate(payload.model_dump(mode="json"))
    for missing in ("authored", "citation_frame"):
        partial = {k: v for k, v in ok.items() if k != missing}
        with pytest.raises(ValidationError, match="present together"):
            validate_payload("claim_proposal", partial)
    with pytest.raises(ValidationError, match="derived_from and rule"):
        validate_payload("claim_proposal", {"batch": stored_t3(), "establishment": "derived"})


def test_payload_rules_the_schema_cannot_state() -> None:
    base = {"candidate": "ent:1", "score": 0.9, "features": {}}
    with pytest.raises(ValidationError, match="exactly one"):
        validate_payload("link", base)
    with pytest.raises(ValidationError, match="exactly one"):
        validate_payload("link", {**base, "mention_ref": {"ordinal": 1}, "pair": ["a", "b"]})
    judgment = {"target": {"kind": "claim", "ref": "clm:1"}, "decision": "choose",
                "rationale": "r", "guideline_version": "1"}  # fmt: skip
    with pytest.raises(ValidationError, match="chosen"):
        validate_payload("judgment", judgment)
    failing = {"claim_key": "clm:1", "verifier": "M19", "verdict": "refuted",
               "detail": {"rule": "stat.r1", "severity": "warning", "message": "m"}}  # fmt: skip
    validate_payload("verification", failing)
    scope = {"mention_ref": {"ordinal": 1}, "start": 3, "end": 4, "scope_segment": "seg:1",
             "extent": "section", "binding_site": {"mention_ref": {"task": 7, "ordinal": 0},
                                                   "start": 0, "end": 2},
             "reopens": {"mention_ref": {"ordinal": 0}, "start": 0, "end": 1}}  # fmt: skip
    validate_payload("scope", scope)
    value = {"value": {"t": "formula", "latex": "a", "sympy": "Symbol('a')", "parse": "ok"},
             "math_kind": "formula"}  # fmt: skip
    dumped = validate_payload("value", value).model_dump(mode="json")
    assert dumped == {**value, "value": {**value["value"], "symbols": {}}}


def test_the_citation_frame_keys_are_sentence_ids() -> None:
    entry = {"locator": "p@sentence:A", "text": "A."}
    frame = CitationFrame.model_validate({"s1": entry, "c2": entry})
    assert list(frame) == ["s1", "c2"] and "s1" in frame
    with pytest.raises(ValidationError):
        CitationFrame.model_validate({"x1": entry})
    assert not Draft202012Validator(schema("citation_frame")).is_valid({"x1": entry})


# --- The committed schema files --------------------------------------------------------------


def test_schema_files_are_current_and_valid(tmp_path: Path) -> None:
    written = schemas.write(tmp_path)
    assert {p.name for p in written} == {p.name for p in SCHEMA_DIR.glob("*.json")}
    for path in written:
        committed = SCHEMA_DIR / path.name
        assert committed.read_text(encoding="utf-8") == path.read_text(encoding="utf-8"), (
            f"{path.name} is stale: run `uv run python -m corpus_structure.core.schemas`"
        )
        document = json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(document)
        assert document["$schema"] == schemas.DRAFT
        assert '"title"' not in path.read_text(encoding="utf-8")


def test_the_keyed_candidate_set() -> None:
    from corpus_structure.core.candidates import KeyedCandidateSet

    raw = {
        "entities": [
            {"id": "X", "type": "RandomVariable", "label": "X", "scope": "local",
             "scope_segment": "seg:1", "symbol": "X"},
            {"id": "N", "key": "ent:abc", "type": "DistributionFamily", "label": "normal",
             "scope": "global"},
        ],
        "statements": [{"id": "st1", "kind": "theorem", "anchor": ["seg:2"]}],
        "claims": [{"id": "c1", "predicate": "has_distribution", "subject": "X",
                    "object": {"ref": "N"}, "qualifiers": {"modality": "supposed"},
                    "statement": "st1", "statement_role": "premise",
                    "evidence": [{"start": 0, "end": 4, "role": "primary"}]}],
    }  # fmt: skip
    cands = KeyedCandidateSet.model_validate(raw)
    assert KeyedCandidateSet.model_validate_json(cands.model_dump_json()) == cands
    assert cands.claims[0].establishment == "stated" and cands.entities[0].key is None
    twice = {**raw, "statements": [{"id": "X", "kind": "theorem", "anchor": ["seg:2"]}]}
    with pytest.raises(ValidationError, match="used twice"):
        KeyedCandidateSet.model_validate(twice)
    no_segment = {**raw, "entities": [{**raw["entities"][0], "scope_segment": None}]}
    with pytest.raises(ValidationError, match="scope_segment exactly when it is local"):
        KeyedCandidateSet.model_validate(no_segment)


def test_a_statement_outside_the_unit() -> None:
    """S4 V2: a statement the unit refers to but that lies outside it ("the last result")."""
    authored = {
        "unit_ref": "special/Normal.html#rel2",
        "statements": [
            {"local_ref": "here", "kind": "corollary", "anchor": "unit"},
            {"local_ref": "last", "kind": "theorem", "anchor": "outside"},
        ],
        "claims": [
            {"local_ref": "c1", "predicate": "follows_from", "subject": "here",
             "object": {"ref": "last"}, "statement": "here",
             "evidence": [{"sentence": "s1", "quote": "the last result", "role": "primary"}]},
        ],
    }  # fmt: skip
    batch = AuthoredBatch.model_validate_json(json.dumps(authored), strict=True)
    assert batch.statements[1].anchor == "outside"
    dumped = batch.model_dump(mode="json")
    assert dumped["statements"] == authored["statements"]
    validator("batch.authored").validate(dumped)
    assert cited_sentences(batch) == ["s1"]
    stored = stored_t3()
    stored["statements"].append({"local_ref": "last", "kind": "theorem", "anchor": "outside"})
    stored_batch = StoredBatch.model_validate_json(json.dumps(stored), strict=True)
    validator("batch.stored").validate(stored_batch.model_dump(mode="json"))
    for bad in ("inside", "", ["outside"]):
        with pytest.raises(ValidationError):
            AuthoredBatch.model_validate(
                {**authored, "statements": [{"local_ref": "x", "kind": "k", "anchor": bad}]}
            )
    with pytest.raises(ValidationError):  # "unit" is an authored anchor only
        StoredBatch.model_validate(
            {**stored, "statements": [{"local_ref": "x", "kind": "k", "anchor": "unit"}]}
        )

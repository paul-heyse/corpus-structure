"""The DuckDB engine against the Python reference (P0-P-2; pool and interchange §3.2, §6 "Set
equality"): both engines give equal results, in the steps' key order, on the Arrow fixtures, on
shuffled inputs and on generated inputs; no database server."""

from __future__ import annotations

import json
import random
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pyarrow as pa
import pytest
import yaml
from hypothesis import given
from hypothesis import strategies as st

from corpus_structure.pool import contract
from corpus_structure.pool.duckdb_engine import DuckDBEngine
from corpus_structure.pool.harness import EngineDisagreement, agree, engine
from corpus_structure.pool.steps import (
    DISAGREEMENTS,
    KEYED_CLAIMS,
    LINKABLE,
    MEANINGS,
    REFERENCE_CLASS,
    VIEW_ALTERNATIVES,
    VIEW_CLAIMS,
    VIEW_ENTITIES,
    VIEW_IDENTITY,
    PythonEngine,
    ViewSpec,
)
from corpus_structure.schema.pack import ViewDecl

REPO = Path(__file__).resolve().parents[4]
STATISTICS_RULES = REPO / "domains" / "statistics" / "schema" / "rules.yaml"


@pytest.fixture(scope="module")
def duck() -> Iterator[DuckDBEngine]:
    with DuckDBEngine() as e:
        yield e


def both(step: str, duck: DuckDBEngine, *inputs: Any) -> pa.Table:
    return agree(step, *inputs, engines=(PythonEngine(), duck))


def shuffled(table: pa.Table, seed: int) -> pa.Table:
    order = list(range(table.num_rows))
    random.Random(seed).shuffle(order)
    return table.take(pa.array(order, pa.int64()))


def family_params() -> ViewSpec:
    """The statistics pack's own `views:` declaration, as S2's file model reads it."""
    raw = yaml.safe_load(STATISTICS_RULES.read_text())["views"]["family_params"]
    declaration = ViewDecl.model_validate(raw).model_dump(mode="json")
    return ViewSpec.from_declaration("family_params", declaration, ["stat:has_distribution"])


# --- Step inputs from the pool (identity forms are Python stand-ins here) ----------------------


def scoped(oid: int, ref: str | None) -> str | None:
    return None if ref is None else f"{oid}:{ref}"


def pool_inputs(pool: contract.Pool) -> SimpleNamespace:
    claims = pool[contract.CLAIMS].to_pylist()
    entities = pool[contract.ENTITIES].to_pylist()
    items = [json.loads(c["item"]) for c in claims]
    linkable = [
        {"entity": scoped(e["observation_id"], e["local_ref"]), "type": e["type"],
         "normalized": e["label"].casefold()}
        for e in entities if e["scope"] == "global"
    ]  # fmt: skip
    keyed = [
        {"key": f"{c['predicate']}|{c['subject']}|{c['object']}",
         "observation_id": c["observation_id"], "evidence": c["evidence"]}
        for c in claims
    ]  # fmt: skip
    meanings = [
        {"key": k["key"], "meaning": json.dumps(i["qualifiers"], sort_keys=True) or None}
        for k, i in zip(keyed, items, strict=True)
    ]
    view_claims = [
        {"claim": scoped(c["observation_id"], c["local_ref"]), "predicate": c["predicate"],
         "subject": scoped(c["observation_id"], c["subject"]),
         "object": scoped(c["observation_id"], json.loads(c["object"]).get("ref")),
         "statement": scoped(c["observation_id"], c["statement"])}
        for c in claims
    ]  # fmt: skip
    view_entities = [
        {"entity": scoped(e["observation_id"], e["local_ref"]), "key": None, "type": e["type"],
         "label": e["label"], "symbol": e["symbol"]}
        for e in entities
    ]  # fmt: skip
    identity = [
        {"entity": scoped(e["observation_id"], e["local_ref"]), "slot": slot, "value": value}
        for e in entities for slot, value in json.loads(e["item"]).get("identity", {}).items()
    ]  # fmt: skip
    alternatives = [
        {"group": f"{a['observation_id']}:{a['ordinal']}", "claim": scoped(a["observation_id"], r)}
        for a in pool[contract.ALTERNATIVES].to_pylist() for r in a["refs"]
    ]  # fmt: skip
    return SimpleNamespace(
        linkable=pa.Table.from_pylist(linkable, schema=LINKABLE),
        keyed=pa.Table.from_pylist(keyed, schema=KEYED_CLAIMS),
        meanings=pa.Table.from_pylist(meanings, schema=MEANINGS),
        views=(
            pa.Table.from_pylist(view_claims, schema=VIEW_CLAIMS),
            pa.Table.from_pylist(view_entities, schema=VIEW_ENTITIES),
            pa.Table.from_pylist(identity, schema=VIEW_IDENTITY),
            pa.Table.from_pylist(alternatives, schema=VIEW_ALTERNATIVES),
        ),
    )


def test_both_engines_agree_on_the_arrow_pool(
    arrow_pool: SimpleNamespace, duck: DuckDBEngine
) -> None:
    pool = arrow_pool.build()
    given_ = pool_inputs(pool)
    refs = (pool[contract.REFERENCE_ENTITIES], pool[contract.REFERENCE_ALIASES])
    links = both("alias_links", duck, given_.linkable, *refs)
    assert links.column("entity").to_pylist() == ["101:N", "102:N", "102:N"]
    fused = both("fuse", duck, given_.keyed)
    assert fused.column("supports").to_pylist() == [[101]]  # c0 and c1 share the stand-in key
    assert fused.column("candidates").to_pylist() == [2]
    disagreeing = both("disagreements", duck, given_.meanings)
    assert disagreeing.num_rows == 2  # c1 sets a modality, c0 none
    facts = both("views", duck, *given_.views, [family_params()])
    by = {(r["claim"], r["view"]): r["facts"] for r in facts.to_pylist()}
    assert by["101:c0", "same_slot"] == ["101:c1"]
    assert by["101:c1", "alternative_of"] == ["101:c0"]
    assert by["101:c0", "family_params"] == []  # no has_parameter source claims
    for seed in range(3):  # set results: the input order does not matter
        assert both("alias_links", duck, shuffled(given_.linkable, seed), *refs).equals(links)
        assert both("fuse", duck, shuffled(given_.keyed, seed)).equals(fused)
        shuffled_views = [shuffled(t, seed) for t in given_.views]
        assert both("views", duck, *shuffled_views, [family_params()]).equals(facts)


def test_views_compute_the_declared_and_generic_facts(duck: DuckDBEngine) -> None:
    """Independent expectation: `family_params` of a has_distribution claim is the canonical names
    of the parameters its object family has (D5 §8.2), whichever side is matched."""
    claims = pa.Table.from_pylist([
        {"claim": "d1", "predicate": "stat:has_distribution", "subject": "X", "object": "N",
         "statement": "s1"},
        {"claim": "d2", "predicate": "stat:has_distribution", "subject": "X", "object": "G",
         "statement": "s1"},
        {"claim": "d3", "predicate": "stat:has_distribution", "subject": "X", "object": None,
         "statement": None},
        {"claim": "d4", "predicate": "stat:has_distribution", "subject": "X", "object": "N",
         "statement": None},
        {"claim": "p1", "predicate": "stat:has_parameter", "subject": "N", "object": "mu",
         "statement": "s1"},
        {"claim": "p2", "predicate": "stat:has_parameter", "subject": "N", "object": "sigma",
         "statement": "s1"},
        {"claim": "p3", "predicate": "stat:has_parameter", "subject": "N", "object": "nobody",
         "statement": "s1"},
        {"claim": "p4", "predicate": "stat:has_parameter", "subject": "N", "object": "xrf",
         "statement": "s1"},
    ], schema=VIEW_CLAIMS)  # fmt: skip
    entities = pa.Table.from_pylist([
        {"entity": e, "key": None, "type": t, "label": e, "symbol": None}
        for e, t in (("X", "stat:RandomVariable"), ("N", "stat:DistributionFamily"),
                     ("G", "stat:DistributionFamily"), ("mu", "stat:FamilyParameter"),
                     ("sigma", "stat:FamilyParameter"), ("xrf", REFERENCE_CLASS))
    ], schema=VIEW_ENTITIES)  # fmt: skip
    identity = pa.Table.from_pylist([
        {"entity": "mu", "slot": "stat:canonical_name", "value": "mean"},
        {"entity": "sigma", "slot": "stat:canonical_name", "value": "standard_deviation"},
        {"entity": "sigma", "slot": "stat:family", "value": "N"},
        {"entity": "xrf", "slot": "stat:canonical_name", "value": "cited"},
    ], schema=VIEW_IDENTITY)  # fmt: skip
    alternatives = pa.Table.from_pylist([
        {"group": "g", "claim": "d1"}, {"group": "g", "claim": "d2"},
        {"group": "g", "claim": "elsewhere"},
    ], schema=VIEW_ALTERNATIVES)  # fmt: skip
    labels = ViewSpec("labels", frozenset({"stat:has_parameter"}), "stat:has_parameter",
                      "subject", "subject", "object", "label")  # fmt: skip
    facts = both("views", duck, claims, entities, identity, alternatives, [family_params(), labels])
    by = {(r["claim"], r["view"]): r["facts"] for r in facts.to_pylist()}
    assert by["d1", "family_params"] == ["mean", "standard_deviation"]
    assert by["d4", "family_params"] == ["mean", "standard_deviation"]
    assert by["d2", "family_params"] == []
    assert by["d3", "family_params"] == []  # a value object matches nothing
    assert ("p1", "family_params") not in by  # not a predicate it applies to
    # `nobody` is no entity of the input, and an ExternalReference is none for a projection (S2)
    assert by["p1", "labels"] == ["mu", "sigma"]
    assert by["d1", "same_slot"] == ["d2"]
    assert by["d3", "same_slot"] == ["d4"]  # an absent statement equals an absent statement
    assert by["d1", "alternative_of"] == ["d2"]  # `elsewhere` is not in the input
    assert by["p1", "alternative_of"] == []
    with pytest.raises(ValueError, match="shadow a generic fact"):
        PythonEngine().views(claims, entities, identity, alternatives,
                             [ViewSpec("same_slot", frozenset(), "p", "subject", "subject",
                                       "object", "id")])  # fmt: skip
    with pytest.raises(ValueError, match="claim ids are not unique"):
        duck.views(pa.concat_tables([claims, claims]), entities, identity, alternatives, [])


# --- Generated inputs --------------------------------------------------------------------------

TEXT = st.sampled_from(["a", "B", "b", "é", "ß", "Z", "a b", ""])
IDS = st.sampled_from(["e1", "e2", "E3", "é4", "e5"])


@given(
    linkable=st.lists(st.fixed_dictionaries({
        "entity": IDS, "type": st.sampled_from(["t1", "t2"]), "normalized": TEXT}), max_size=8),
    entities=st.lists(st.tuples(st.sampled_from(["t1", "t2"]), IDS), max_size=5),
    aliases=st.lists(st.tuples(st.integers(0, 6), TEXT, st.sampled_from(["label", "term"])),
                     max_size=10),
)  # fmt: skip
def test_alias_links_agree_on_generated_inputs(
    duck: DuckDBEngine, linkable: list, entities: list, aliases: list
) -> None:
    ents = [
        {"id": i, "run_id": 3, "key": f"ent:{key}", "schema_version_id": 1, "type": type_,
         "label": key, "scope": "global", "scope_segment_id": None, "attrs": "{}", "kind": None,
         "resolved_to_id": None, "confidence": None}
        for i, (type_, key) in enumerate(entities)
    ]  # fmt: skip
    seen: set[tuple[int, str, str]] = set()
    rows = []
    for entity_id, normalized, kind in aliases:
        if entity_id < len(ents) and (entity_id, normalized, kind) not in seen:
            seen.add((entity_id, normalized, kind))
            rows.append({"entity_id": entity_id, "alias": normalized, "normalized": normalized,
                         "alias_kind": kind})  # fmt: skip
    ref_e = pa.Table.from_pylist(ents, schema=contract.reference_schema("reference_entities"))
    ref_a = pa.Table.from_pylist(rows, schema=contract.reference_schema("reference_aliases"))
    both("alias_links", duck, pa.Table.from_pylist(linkable, schema=LINKABLE), ref_e, ref_a)


EVIDENCE = st.fixed_dictionaries(
    {"start": st.integers(0, 3), "end": st.integers(4, 6),
     "role": st.sampled_from(["primary", "context", "é"])},
    optional={"coarse": st.booleans()},
)  # fmt: skip


@given(st.lists(st.tuples(IDS, st.integers(1, 4), st.lists(EVIDENCE, max_size=3)), max_size=8))
def test_fuse_agrees_on_generated_inputs(duck: DuckDBEngine, rows: list) -> None:
    claims = [
        {"key": key, "observation_id": oid,
         "evidence": json.dumps(items, ensure_ascii=bool(oid % 2))}
        for key, oid, items in rows
    ]  # fmt: skip
    both("fuse", duck, pa.Table.from_pylist(claims, schema=KEYED_CLAIMS))


@given(st.lists(st.tuples(IDS, st.one_of(st.none(), TEXT)), max_size=10))
def test_disagreements_agree_on_generated_inputs(duck: DuckDBEngine, rows: list) -> None:
    meanings = [{"key": k, "meaning": m} for k, m in rows]
    result = both("disagreements", duck, pa.Table.from_pylist(meanings, schema=MEANINGS))
    assert result.schema.equals(DISAGREEMENTS, check_metadata=True)


NODES = st.sampled_from(["n1", "n2", "n3", "n4", "é5"])
SIDES = st.sampled_from(["subject", "object"])
SPECS = st.lists(st.builds(
    lambda i, applies, source, ms, mc, head, attr: ViewSpec(
        f"v{i}", frozenset(applies), source, ms, mc, head,
        "identity" if attr.startswith("stat:") else attr,
        attr if attr.startswith("stat:") else None),
    st.integers(0, 3), st.sets(st.sampled_from(["p", "q"]), max_size=2),
    st.sampled_from(["p", "q"]), SIDES, SIDES, SIDES,
    st.sampled_from(["id", "key", "type", "label", "symbol", "stat:a", "stat:b"]),
), max_size=3, unique_by=lambda s: s.name)  # fmt: skip


@given(
    claims=st.lists(st.tuples(st.sampled_from(["p", "q"]), NODES, st.one_of(st.none(), NODES),
                              st.one_of(st.none(), st.sampled_from(["s1", "s2"]))), max_size=8),
    entities=st.sets(NODES, min_size=3),
    keyed=st.booleans(),
    identity=st.lists(st.tuples(NODES, st.sampled_from(["stat:a", "stat:b"]), TEXT), max_size=6),
    groups=st.lists(st.tuples(st.sampled_from(["g1", "g2"]), st.integers(0, 9)), max_size=6),
    specs=SPECS,
)  # fmt: skip
def test_views_agree_on_generated_inputs(
    duck: DuckDBEngine, claims: list, entities: set, keyed: bool, identity: list, groups: list,
    specs: list,
) -> None:
    claim_rows = [
        {"claim": f"c{i}", "predicate": p, "subject": s, "object": o, "statement": t}
        for i, (p, s, o, t) in enumerate(claims)
    ]
    entity_rows = [
        {"entity": e, "key": f"ent:{e}" if keyed else None,
         "type": REFERENCE_CLASS if e.endswith("2") else "t", "label": e.upper(),
         "symbol": e if e.endswith("1") else None}
        for e in sorted(entities)
    ]  # fmt: skip
    identity_rows = [{"entity": e, "slot": s, "value": v} for e, s, v in set(identity)]
    group_rows = [{"group": g, "claim": f"c{i}"} for g, i in set(groups)]
    both("views", duck,
         pa.Table.from_pylist(claim_rows, schema=VIEW_CLAIMS),
         pa.Table.from_pylist(entity_rows, schema=VIEW_ENTITIES),
         pa.Table.from_pylist(identity_rows, schema=VIEW_IDENTITY),
         pa.Table.from_pylist(group_rows, schema=VIEW_ALTERNATIVES),
         specs)  # fmt: skip


# --- The harness and the engine ----------------------------------------------------------------


class Skewed(PythonEngine):
    """An engine that loses a row: the harness must see it."""

    name = "skewed"

    def disagreements(self, meanings: pa.Table) -> pa.Table:
        return super().disagreements(meanings).slice(1)


class NotASet(PythonEngine):
    name = "not_a_set"

    def disagreements(self, meanings: pa.Table) -> pa.Table:
        result = super().disagreements(meanings)
        return pa.concat_tables([result, result])


def test_the_harness_refuses_a_disagreement_and_a_non_set() -> None:
    meanings = pa.Table.from_pylist(
        [{"key": "k", "meaning": "a"}, {"key": "k", "meaning": "b"}], schema=MEANINGS
    )
    with pytest.raises(EngineDisagreement, match=r"python alone \[\('k', 'a'\)\]"):
        agree("disagreements", meanings, engines=(PythonEngine(), Skewed()))
    with pytest.raises(EngineDisagreement, match="two rows on one"):
        agree("disagreements", meanings, engines=(PythonEngine(), NotASet()))
    assert agree("disagreements", meanings).num_rows == 2  # the default pair: Python and DuckDB


def test_the_engine_session_is_in_utc_and_holds_no_inputs(duck: DuckDBEngine) -> None:
    zone = duck.con.sql("SELECT current_setting('TimeZone') AS z").to_arrow_table()
    assert zone.column("z").to_pylist() == ["UTC"]
    tables = duck.con.sql("SELECT count(*) AS n FROM duckdb_views() WHERE NOT internal")
    assert tables.to_arrow_table().column("n").to_pylist() == [0]  # inputs unregistered
    assert engine("python").name == "python"
    made = engine("duckdb")
    assert isinstance(made, DuckDBEngine)
    made.close()

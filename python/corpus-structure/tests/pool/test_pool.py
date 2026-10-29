"""The pool contract, T3 hydration and the Python reference steps on Arrow fixtures (P0-P-1; pool
and interchange §3.1, §6): no database server."""

from __future__ import annotations

import json
import random
from types import SimpleNamespace

import pyarrow as pa
import pytest

from corpus_structure.core import candidates as C
from corpus_structure.core.batch import StoredDescriptor, StoredEvidence, StoredQualifiers
from corpus_structure.core.payload_schemas import UnknownPayloadSchema
from corpus_structure.core.translations import completeness
from corpus_structure.core.values import EntityRef
from corpus_structure.core.vocab import (
    EntityExtent,
    EntityScope,
    EvidenceRole,
    StatementRole,
)
from corpus_structure.pool import PythonEngine, contract, hydrate
from corpus_structure.pool.hydrate import T3
from corpus_structure.pool.steps import KEYED_CLAIMS, LINKABLE, MEANINGS
from corpus_structure.schema import interchange, model


def ipc(table: pa.Table) -> bytes:
    sink = pa.BufferOutputStream()
    with pa.ipc.new_stream(sink, table.schema) as writer:
        writer.write_table(table)
    return sink.getvalue().to_pybytes()


def shuffled(table: pa.Table, seed: int) -> pa.Table:
    order = list(range(table.num_rows))
    random.Random(seed).shuffle(order)
    return table.take(order)


def meta(table: pa.Table) -> dict[str, str]:
    return {k.decode(): v.decode() for k, v in (table.schema.metadata or {}).items()}


# --- The contract ------------------------------------------------------------------------------


def test_payload_relations_are_the_model_payload_schemas(arrow_pool: SimpleNamespace) -> None:
    pool = arrow_pool.build()
    m3 = interchange.installed()
    for kind in contract.ALL_KINDS:
        relation = pool.payload(kind)
        assert relation.schema.names[0] == "observation_id"
        assert pa.schema(list(relation.schema)[1:]).equals(m3.payload(kind), check_metadata=False)
        assert meta(relation)["cs.payload"] == kind
    index = pool[contract.OBSERVATIONS]
    assert [f for f in index.schema if f.name != "run_id"] == [
        f for f in m3.tables["kb.observation"] if f.name != "payload"
    ]
    for name, table in (("reference_entities", "kb.entity"), ("reference_aliases",
                                                              "kb.entity_alias")):  # fmt: skip
        assert pool[name].schema.equals(m3.tables[table], check_metadata=False)


def test_every_relation_carries_the_run_cut_and_registry_ids(arrow_pool: SimpleNamespace) -> None:
    """DA-009: a relation read from payloads names the registry id its fields follow; the index
    keeps each row's recorded id, so an observation stored under an older version stays visible."""
    pool = arrow_pool.build()
    proposal = pool.meta.payload_schema_ids["claim_proposal"]
    assert proposal == 100  # the newest version, the one payloads are upcast to
    for name, table in pool.relations.items():
        m = meta(table)
        assert (m["cs.relation"], m["cs.run_id"], m["cs.cut_at"]) == (
            name,
            "7",
            "2026-10-28T12:00:00+00:00",
        )
        assert m["cs.model_revision"] == interchange.installed().model_revision
    for name in (*contract.CANDIDATES, contract.BATCHES, "payload_claim_proposal"):
        assert meta(pool[name])["cs.payload_schema_id"] == "100"
    assert meta(pool.payload("judgment"))["cs.payload_schema_id"] == str(
        pool.meta.payload_schema_ids["judgment"]
    )
    recorded = dict(zip(*pool[contract.OBSERVATIONS].select(["id", "payload_schema_id"]).to_pydict()
                        .values(), strict=True))  # fmt: skip
    assert recorded[101] == 100 and recorded[102] != 100
    unsealed = arrow_pool.build(
        run=contract.RunRow(7, None, 1, 1, 1, None), reference_entities=None, reference_aliases=None
    )
    assert "cs.cut_at" not in meta(unsealed[contract.CLAIMS])
    assert unsealed[contract.REFERENCE_ENTITIES].num_rows == 0


def test_candidates_lift_typed_fields_and_keep_the_stored_item(arrow_pool: SimpleNamespace) -> None:
    pool = arrow_pool.build()
    claims = {r["local_ref"]: r for r in pool[contract.CLAIMS].to_pylist()}
    assert claims["c0"]["establishment"] == "stated"  # the default, as a value
    assert claims["c0"]["statement_role"] is None  # MISSING is absent
    assert claims["c1"]["statement_role"] == "premise"
    assert json.loads(claims["c1"]["object"]) == {"ref": "N"}
    stored = arrow_pool.stored[101]
    for claim in stored.claims:
        assert json.loads(claims[claim.local_ref]["item"]) == claim.model_dump(mode="json")
    # an `outside` statement item is an ExternalReference candidate, never a statement
    assert pool[contract.STATEMENTS].column("local_ref").to_pylist() == ["st1"]
    reference = pool[contract.REFERENCES].to_pylist()
    assert [r["local_ref"] for r in reference] == ["last"]
    assert json.loads(reference[0]["descriptor"])["target"] == "special/Normal.html#thm3"
    assert pool[contract.ALTERNATIVES].to_pylist()[0]["refs"] == ["c1", "c0"]
    batches = pool[contract.BATCHES].to_pylist()
    assert [(b["observation_id"], b["unit_ref"]) for b in batches] == [
        (101, "special/Normal.html#rel1"), (102, "special/Normal.html#rel2"),
        (105, "special/Normal.html#rel3"),
    ]  # fmt: skip
    entities = pool[contract.ENTITIES].select(["observation_id", "local_ref"]).to_pylist()
    assert [(e["observation_id"], e["local_ref"]) for e in entities] == [
        (101, "N"),
        (101, "X"),
        (102, "N"),
    ]


def test_json_null_and_absent_stay_apart(arrow_pool: SimpleNamespace) -> None:
    """The null policy: a JSON null is the text `null`; an absent field is Arrow null."""
    row = arrow_pool.build().payload("author_markup").to_pylist()[0]
    assert row["value"] == "null"
    assert row["target"] is None


# --- Determinism (TM §10) ----------------------------------------------------------------------


def test_repeated_builds_in_any_input_order_are_byte_equal(arrow_pool: SimpleNamespace) -> None:
    first = arrow_pool.build()
    for seed in range(5):
        again = arrow_pool.build(
            observations=shuffled(arrow_pool.observations, seed),
            reference_entities=shuffled(arrow_pool.reference_entities, seed),
            reference_aliases=shuffled(arrow_pool.reference_aliases, seed),
            registry=list(reversed(arrow_pool.registry)),
        )
        assert again.meta == first.meta
        assert again.relations.keys() == first.relations.keys()
        for name, table in first.relations.items():
            assert ipc(again[name]) == ipc(table), name
    assert hydrate(arrow_pool.build()) == hydrate(first)


# --- Refusals ----------------------------------------------------------------------------------


def test_inputs_the_pool_refuses(arrow_pool: SimpleNamespace) -> None:
    obs = arrow_pool.observations
    other_run = obs.set_column(0, obs.schema.field("run_id"), pa.array([7, 7, 8, 7, 7]))
    with pytest.raises(contract.PoolInputError, match="runs"):
        arrow_pool.build(observations=other_run)
    with pytest.raises(contract.PoolInputError, match="unselected kinds"):
        arrow_pool.build(kinds=["claim_proposal"])
    i = obs.schema.get_field_index("payload_schema_id")
    unknown = obs.set_column(i, obs.schema.field(i), pa.array([100, 999, 7, 17, 1], pa.int64()))
    with pytest.raises(UnknownPayloadSchema):
        arrow_pool.build(observations=unknown)
    i = obs.schema.get_field_index("ordinal")
    wrong_type = obs.set_column(i, "ordinal", pa.array([0] * 5, pa.int64()))
    with pytest.raises(contract.PoolSchemaError, match="ordinal is int64"):
        arrow_pool.build(observations=wrong_type)
    with pytest.raises(contract.PoolInputError, match="reference entities of runs"):
        arrow_pool.build(run=contract.RunRow(7, None, 1, 1, 1, None))
    with pytest.raises(contract.PoolInputError, match=r"entities \[51\] not loaded"):
        arrow_pool.build(reference_entities=arrow_pool.reference_entities.slice(1))
    with pytest.raises(contract.PoolSchemaError, match="lacks payload"):
        arrow_pool.build(observations=obs.drop_columns(["payload"]))
    only = arrow_pool.build(
        observations=obs.filter(pa.array([k == "judgment" for k in obs["kind"].to_pylist()])),
        kinds=["judgment"],
    )
    assert set(only.relations) == {
        contract.OBSERVATIONS, "payload_judgment", contract.BATCHES, *contract.CANDIDATES,
        contract.REFERENCE_ENTITIES, contract.REFERENCE_ALIASES,
    }  # fmt: skip
    assert only[contract.CLAIMS].num_rows == 0


# --- T3 ----------------------------------------------------------------------------------------


def test_t3_hydrates_one_candidate_set_per_proposal(arrow_pool: SimpleNamespace) -> None:
    """Independent expectation: the keyed candidate set of BATCH_A written out by hand."""
    hydrated = {h.observation_id: h.candidates for h in hydrate(arrow_pool.build())}
    assert sorted(hydrated) == [101, 102, 105]
    ren = "ren:" + "1" * 32
    expected = C.KeyedCandidateSet(
        renditions=(ren,),
        entities=(
            C.CandidateEntity(id="N", type="stat:DistributionFamily", label="normal distribution",
                              scope=EntityScope.GLOBAL, aliases=("normally distributed",)),
            C.CandidateEntity(id="X", type="stat:RandomVariable", label="X",
                              scope=EntityScope.LOCAL, extent=EntityExtent.STATEMENT,
                              scope_segment="seg:1", symbol="X"),
        ),
        statements=(C.CandidateStatement(id="st1", kind="theorem", anchor=("seg:2",)),),
        references=(C.CandidateReference(
            id="last",
            descriptor=StoredDescriptor(start=3, end=18, target="special/Normal.html#thm3")),),
        claims=(
            C.CandidateClaim(id="c0", predicate="stat:has_distribution", subject="X",
                             object=EntityRef(ref="N"), statement="st1",
                             evidence=(StoredEvidence(start=41, end=60, role=EvidenceRole.PRIMARY,
                                                      coarse=True),)),
            C.CandidateClaim(id="c1", predicate="stat:has_distribution", subject="X",
                             object=EntityRef(ref="N"),
                             qualifiers=StoredQualifiers.model_validate(
                                 {"core:modality": "supposed"}),
                             statement="st1", statement_role=StatementRole.PREMISE,
                             evidence=(StoredEvidence(start=10, end=40,
                                                      role=EvidenceRole.PRIMARY),)),
        ),
        alternatives=(C.CandidateAlternative(refs=("c1", "c0"), reason="two readings"),),
        unsupported=(C.CandidateUnsupported(id="u1", start=61, end=70, reason="r", coarse=True),),
    )  # fmt: skip
    assert hydrated[101] == expected
    assert hydrated[105] == C.KeyedCandidateSet(renditions=(ren,))
    assert [e.label for e in hydrated[102].entities] == ["normal"]
    assert all(c.key is C.UNKEYED for c in hydrated[101].claims)
    assert hydrated[101].references[0].resolved_to is C.AWAITING


def test_t3_declaration_is_complete() -> None:
    m = model.load()
    view = m.system

    def slots(cls: str, form: str) -> list[str]:
        out = []
        for slot in view.class_induced_slots(cls):
            declared = model.ci_annotations(slot).get("ci:form")
            if declared in (None, form):
                out.append(str(slot.name))
        return out

    assert completeness(T3, slots) == []


# --- The Python reference steps ----------------------------------------------------------------


def test_alias_links_count_matching_reference_keys(arrow_pool: SimpleNamespace) -> None:
    pool = arrow_pool.build()
    linkable = pa.Table.from_pylist([
        {"entity": "e1", "type": "stat:DistributionFamily", "normalized": "normal distribution"},
        {"entity": "e2", "type": "stat:DistributionFamily", "normalized": "normal"},
        {"entity": "e3", "type": "stat:RandomVariable", "normalized": "normal"},
        {"entity": "e2", "type": "stat:DistributionFamily", "normalized": "normal"},
    ], schema=LINKABLE)  # fmt: skip
    links = PythonEngine().alias_links(
        linkable, pool[contract.REFERENCE_ENTITIES], pool[contract.REFERENCE_ALIASES]
    )
    b, c = "ent:" + "b" * 32, "ent:" + "c" * 32
    assert links.to_pylist() == [
        {"entity": "e1", "key": b, "matches": 1},  # one match links
        {"entity": "e2", "key": b, "matches": 2},  # two reference entities: ambiguous
        {"entity": "e2", "key": c, "matches": 2},
    ]  # e3: another type, no match
    with pytest.raises(ValueError, match="reference_aliases"):
        PythonEngine().alias_links(linkable, pool[contract.REFERENCE_ENTITIES], linkable)


def test_fuse_unions_supports_and_evidence() -> None:
    def row(key: str, observation_id: int, *evidence: dict) -> dict:
        return {"key": key, "observation_id": observation_id, "evidence": json.dumps(evidence)}

    claims = pa.Table.from_pylist([
        row("k2", 5, {"start": 1, "end": 2, "role": "primary"}),
        row("k1", 9, {"role": "primary", "end": 9, "start": 3}),
        row("k1", 4, {"start": 3, "end": 9, "role": "primary"},
            {"start": 0, "end": 2, "role": "context"}),
        row("k1", 4),
    ], schema=KEYED_CLAIMS)  # fmt: skip
    fused = PythonEngine().fuse(claims).to_pylist()
    assert [(r["key"], r["supports"], r["candidates"]) for r in fused] == [
        ("k1", [4, 9], 3),
        ("k2", [5], 1),
    ]
    assert json.loads(fused[0]["evidence"]) == [
        {"end": 2, "role": "context", "start": 0},
        {"end": 9, "role": "primary", "start": 3},
    ]
    assert PythonEngine().fuse(shuffled(claims, 1)).equals(PythonEngine().fuse(claims))


def test_disagreements_count_null_as_a_meaning() -> None:
    meanings = pa.Table.from_pylist([
        {"key": "k1", "meaning": "hedge=a"}, {"key": "k1", "meaning": None},
        {"key": "k2", "meaning": "hedge=a"}, {"key": "k2", "meaning": "hedge=a"},
        {"key": "k3", "meaning": "b"}, {"key": "k3", "meaning": "a"},
    ], schema=MEANINGS)  # fmt: skip
    assert PythonEngine().disagreements(meanings).to_pylist() == [
        {"key": "k1", "meaning": None}, {"key": "k1", "meaning": "hedge=a"},
        {"key": "k3", "meaning": "a"}, {"key": "k3", "meaning": "b"},
    ]  # fmt: skip

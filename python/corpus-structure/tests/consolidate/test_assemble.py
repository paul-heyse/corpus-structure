"""Assembly on Arrow pools (P0-C-1; consolidation §3.2 to §3.5, §6): no database server.

The anchor is the trace through D5 row 0: the `fixtures/s0` batches of the trace units and the
hand-written `fixtures/trace` targets, each located on the production rendition by A0's `parse`
and assembled by the same pass, give the same claim keys (key equality, never key values),
except for the differences `fixtures/trace/README.md` lists. Every case runs under both engines,
whose knowledge must be equal.
"""

from __future__ import annotations

import json
import random
from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.consolidate import finalize as F
from corpus_structure.consolidate.assemble import REFERENCE, STATEMENT, Knowledge, assemble
from corpus_structure.consolidate.report import PassOutcome, Tally
from corpus_structure.consolidate.write import InvariantViolation, check_invariants
from corpus_structure.core.batch import AuthoredBatch, CitationFrame, StoredBatch
from corpus_structure.methods.llm.parse import parse
from corpus_structure.pool.duckdb_engine import DuckDBEngine
from corpus_structure.pool.steps import PythonEngine

NORMAL = ("T2", "T3", "U5", "U6", "U7", "U8")


def run(
    world: SimpleNamespace, rows: list[dict[str, Any]], reference: Any = None, **inputs: Any
) -> tuple[Knowledge, Tally]:
    """Assemble under both engines; their knowledge must be equal."""
    pool = world.pool(rows, reference)
    out = []
    for engine in (PythonEngine(), DuckDBEngine()):
        tally = Tally()
        out.append((assemble(pool, world.inputs(**inputs), engine, tally), tally))
    (a, ta), (b, tb) = out
    assert snapshot(a) == snapshot(b)
    assert ta.counts == tb.counts
    return a, ta


def snapshot(k: Knowledge) -> Any:
    entities = {
        key: (
            e.type,
            e.label,
            e.scope,
            e.kind,
            e.resolved_to,
            sorted(e.aliases),
            sorted(e.mentions),
            sorted(e.identity.items()),
        )
        for key, e in k.entities.items()
    }
    claims = {
        key: (r.claim.model_dump_json(), r.evidence, r.supports, r.status, r.group)
        for key, r in k.claims.items()
    }
    return entities, claims, sorted((x.from_key, x.to_key, json.dumps(x.detail)) for x in k.links)


def edit(batch: StoredBatch, change: Any) -> StoredBatch:
    raw = batch.model_dump(mode="json", by_alias=True)
    change(raw)
    return StoredBatch.model_validate(raw)


# --- The trace ---------------------------------------------------------------------------------

TRACE = {"T1": ("T1-leadin", "T1-dfn1"), "T2": ("T2",), "T3": ("T3",), "T4": ("T4",)}


@pytest.mark.parametrize("trace_unit", sorted(TRACE))
def test_the_trace_targets_and_the_s0_batches_key_alike(
    world: SimpleNamespace, trace_unit: str
) -> None:
    units = TRACE[trace_unit]
    path = world.repo / "fixtures/trace" / f"{trace_unit}.target.json"
    target = json.loads(path.read_text(encoding="utf-8"))
    page = world.page_of_unit(units[0])
    located = parse(
        page.view,
        AuthoredBatch.model_validate(target["batch"]),
        CitationFrame.model_validate(target["frame"]),
        world.compiled().names.to_prefixed,
    )
    assert located.report.problems == ()
    expected, _ = run(world, [world.proposal(500, units[0], batch=located.stored)])
    got, tally = run(world, [world.proposal(600 + i, u) for i, u in enumerate(units)])
    assert not [
        c for c in tally.counts if c in {d.value for d in PassOutcome} - {"unhinted_statement_kind"}
    ]
    # statements: every target statement is one of the run's, by key
    targets = {k for k, e in expected.entities.items() if e.type == STATEMENT and e.mentions}
    assert targets <= set(got.entities)

    def known_difference(k: Knowledge, key: str) -> bool:  # fixtures/trace/README.md
        claim = k.claims[key].claim
        if claim.predicate == "core:unschematized":
            return True  # T1: the s0 lead-in states unsupported items; the target none
        subject = k.entities[claim.subject]
        return trace_unit == "T3" and subject.label == "a + b X"  # T3's Y: symbol in v1 only

    missing = {
        k for k in set(expected.claims) - set(got.claims) if not known_difference(expected, k)
    }
    extra = {k for k in set(got.claims) - set(expected.claims) if not known_difference(got, k)}
    assert (missing, extra) == (set(), set())
    for key in set(expected.claims) & set(got.claims):
        assert got.claims[key].claim.predicate == expected.claims[key].claim.predicate


def test_order_independence_and_repeated_assembly(world: SimpleNamespace) -> None:
    rows = [world.proposal(100 + i, u) for i, u in enumerate(NORMAL)]
    first, _ = run(world, rows)
    shuffled = rows[:]
    random.Random(3).shuffle(shuffled)
    again, _ = run(world, shuffled)
    assert snapshot(again) == snapshot(first)


# --- Fusion and alternatives -------------------------------------------------------------------


def test_equal_keys_fuse_with_their_supports(world: SimpleNamespace) -> None:
    k, _ = run(world, [world.proposal(101, "T2"), world.proposal(102, "T2")])
    claims = [r for r in k.claims.values() if r.claim.predicate.startswith("stat:")]
    assert len(claims) == 3 and all(r.supports == [101, 102] for r in claims)
    assert all(r.status == "accepted" for r in claims) and not k.groups


def test_a_meaning_disagreement_gives_an_alternative_group(world: SimpleNamespace) -> None:
    base = world.stored("T2")
    text = world.page_of_unit("T2").content.canonical_text

    def hedge(raw: dict) -> None:
        claim = next(c for c in raw["claims"] if c["local_ref"] == "c_X_normal")
        ev = claim["evidence"][0]
        claim["qualifiers"]["core:hedge"] = {
            "t": "phrase",
            "text": text[ev["start"] : ev["end"]],
            "start": ev["start"],
            "end": ev["end"],
        }

    plain, _ = run(world, [world.proposal(101, "T2")])
    k, _ = run(
        world, [world.proposal(101, "T2"), world.proposal(102, "T2", batch=edit(base, hedge))]
    )
    ((group, members),) = k.groups.items()
    assert len(members) == 2 and group.startswith("clm:") is False
    assert all(k.claims[m].status == "ambiguous" for m in members)
    assert not set(members) & set(plain.claims)  # member keys, not the claim key
    assert {(x.from_key, x.to_key) for x in k.links} == {tuple(sorted(members))}
    assert sorted(s for m in members for s in k.claims[m].supports) == [101, 102]


def test_batch_alternatives_form_a_group(world: SimpleNamespace) -> None:
    def alternatives(raw: dict) -> None:
        raw["alternatives"] = [{"refs": ["c_loc_is_mean", "c_scale_is_sd"], "reason": "r"}]

    k, _ = run(world, [world.proposal(101, "T2", batch=edit(world.stored("T2"), alternatives))])
    (members,) = k.groups.values()
    assert len(members) == 2 and all(k.claims[m].status == "ambiguous" for m in members)
    assert [x.detail["reason"] for x in k.links] == ["r"]


# --- Drops by code -----------------------------------------------------------------------------


def test_a_claim_without_primary_evidence_is_dropped_by_code(world: SimpleNamespace) -> None:
    def no_primary(raw: dict) -> None:
        claim = next(c for c in raw["claims"] if c["local_ref"] == "c_loc_is_mean")
        claim["evidence"] = [{**e, "role": "condition"} for e in claim["evidence"]]

    k, tally = run(world, [world.proposal(101, "T2", batch=edit(world.stored("T2"), no_primary))])
    # the batch checks, the validator propose_claims ran, drop it first, by their INV-01 code
    assert tally.drops["INV-01"] == {"observation:101:claims.1.evidence"}
    assert len([r for r in k.claims.values() if r.claim.predicate.startswith("stat:")]) == 2


def test_a_condition_cycle_and_its_dependants_are_dropped(world: SimpleNamespace) -> None:
    def cycle(raw: dict) -> None:
        a = next(c for c in raw["claims"] if c["local_ref"] == "c_loc_is_mean")
        b = next(c for c in raw["claims"] if c["local_ref"] == "c_scale_is_sd")
        a["qualifiers"]["core:conditions"] = {"op": "claim", "ref": "c_scale_is_sd"}
        b["qualifiers"]["core:conditions"] = {"op": "claim", "ref": "c_loc_is_mean"}

    k, tally = run(world, [world.proposal(101, "T2", batch=edit(world.stored("T2"), cycle))])
    # refused by the batch checks (the shared validator) with the keying code, both claims
    assert tally.drops["condition_cycle"] == {
        "observation:101:claims.1",
        "observation:101:claims.2",
    }
    assert len([r for r in k.claims.values() if r.claim.predicate.startswith("stat:")]) == 1


# --- Linking and external references -----------------------------------------------------------


def _reference(key: str, type_: str, label: str, normalized: str, eid: int) -> tuple[dict, dict]:
    entity = {
        "id": eid,
        "run_id": 3,
        "key": key,
        "schema_version_id": 1,
        "type": type_,
        "label": label,
        "scope": "global",
        "scope_segment_id": None,
        "attrs": "{}",
        "kind": None,
        "resolved_to_id": None,
        "confidence": None,
    }
    alias = {"entity_id": eid, "alias": label, "normalized": normalized, "alias_kind": "label"}
    return entity, alias


def test_a_reference_run_alias_match_keeps_its_key(world: SimpleNamespace) -> None:
    plain, _ = run(world, [world.proposal(101, "T2")])
    family = next(k for k, e in plain.entities.items() if e.type == "stat:DistributionFamily")
    old = "ent:" + "f" * 32
    e1, a1 = _reference(old, "stat:DistributionFamily", "Gaussian", "normal", 1)
    k, tally = run(world, [world.proposal(101, "T2")], ([e1], [a1]))
    assert old in k.entities and family not in k.entities
    assert tally.counts[PassOutcome.LINKED] == 1
    e2, a2 = _reference("ent:" + "e" * 32, "stat:DistributionFamily", "normal", "normal", 2)
    k, tally = run(world, [world.proposal(101, "T2")], ([e1, e2], [a1, a2]))
    assert family in k.entities and tally.counts[PassOutcome.LINK_AMBIGUOUS] == 1


def test_an_external_reference_resolves_by_link_target_and_rekeys(world: SimpleNamespace) -> None:
    unresolved, tally = run(world, [world.proposal(101, "U6")])
    assert tally.counts[PassOutcome.REFERENCE_UNRESOLVED] == 1
    (xrf,) = [k for k, e in unresolved.entities.items() if e.type == REFERENCE]
    follows = next(
        r for r in unresolved.claims.values() if r.claim.predicate == "core:follows_from"
    )
    assert follows.claim.object.ref == xrf  # type: ignore[union-attr]

    def linked(raw: dict) -> None:
        item = next(s for s in raw["statements"] if s.get("anchor") == "outside")
        item["descriptor"]["target"] = "#rel1"

    k, tally = run(
        world,
        [
            world.proposal(101, "U6", batch=edit(world.stored("U6"), linked)),
            world.proposal(102, "T3"),
        ],
    )
    assert tally.counts[PassOutcome.REFERENCE_RESOLVED] == 1
    (xrf2,) = [k_ for k_, e in k.entities.items() if e.type == REFERENCE]
    statement = k.entities[xrf2].resolved_to
    assert statement is not None and k.entities[statement].type == STATEMENT
    rekeyed = next(r for r in k.claims.values() if r.claim.predicate == "core:follows_from")
    assert rekeyed.claim.object.ref == statement  # type: ignore[union-attr]
    assert rekeyed.key != follows.key


def test_a_proposal_on_another_rendition_is_located_again(world: SimpleNamespace) -> None:
    direct, _ = run(world, [world.proposal(101, "T2")])
    page = world.page_of_unit("T2")
    other = page.rendition_id + 50  # another rendition of the same document
    moved, tally = run(
        world,
        [world.proposal(101, "T2", rendition_id=other)],
        documents={**{i: i for i in world.pages()}, other: page.document_id},
    )
    assert tally.counts[PassOutcome.REDERIVED] == 1
    assert set(moved.claims) == set(direct.claims)


# --- Finalize, edges and invariants ------------------------------------------------------------


def test_finalize_reads_values_runs_m19_and_sets_statuses(world: SimpleNamespace) -> None:
    def second(raw: dict) -> None:  # two asserted distributions of X in one statement
        c = next(c for c in raw["claims"] if c["local_ref"] == "c_X_normal")
        raw["entities"].append(
            {
                "local_ref": "e_gamma",
                "type": "stat:DistributionFamily",
                "label": "gamma distribution",
                "scope": "global",
            }
        )
        raw["claims"].append(
            {**c, "local_ref": "c_X_other", "object": {"ref": "e_gamma"}, "qualifiers": {}}
        )

    k, _ = run(
        world,
        [
            world.proposal(101, "T2", batch=edit(world.stored("T2"), second)),
            world.proposal(102, "T3"),
        ],
    )
    inputs = world.inputs()
    readings = F.read_values(k, inputs)
    assert readings and all(r.status for r in readings.values())
    outcome = F.run_m19(k, inputs, readings)
    assert outcome.evaluated
    errors = {f.claim for f in outcome.findings if f.severity == "error"}
    F.set_statuses(k, "finalize", outcome.findings)
    assert errors and all(k.claims[c].status == "rejected" for c in errors)
    assert {r.status for r in k.claims.values()} <= {
        "accepted",
        "rejected",
        "unsupported",
        "ambiguous",
    }
    claim_edges, entity_edges = F.edges(k)
    assert any(e.kind == "condition_premise" for e in claim_edges)
    assert any(e.role == "binding_variable" for e in entity_edges)
    paths = [(e.claim, e.kind, e.path) for e in claim_edges]
    assert len(paths) == len(set(paths))  # one row per reference path
    check_invariants(k, inputs)
    F.set_statuses(k, "assemble", ())
    assert {r.status for r in k.claims.values()} <= {"candidate", "unsupported"}


def test_an_invariant_violation_names_its_keys(world: SimpleNamespace) -> None:
    k, _ = run(world, [world.proposal(101, "T2")])
    key, row = next(
        (key, r) for key, r in sorted(k.claims.items()) if r.claim.predicate.startswith("stat:")
    )
    row.evidence = [{**e, "role": "condition"} for e in row.evidence]
    with pytest.raises(InvariantViolation, match="INV-01") as err:
        check_invariants(k, world.inputs())
    assert err.value.keys == (key,)


def test_an_external_reference_keeps_its_key_resolved_or_not(world: SimpleNamespace) -> None:
    def other_page(raw: dict) -> None:
        item = next(s for s in raw["statements"] if s.get("anchor") == "outside")
        item["descriptor"]["target"] = "LogNormal.html#dfn"

    rows = [world.proposal(101, "U6", batch=edit(world.stored("U6"), other_page))]
    resolved, tally = run(world, rows)
    assert tally.counts[PassOutcome.REFERENCE_RESOLVED] == 1
    without = {i: p for i, p in world.pages().items() if p.page != "special/LogNormal.html"}
    unresolved, tally = run(world, rows, pages=without)
    assert tally.unresolved["other_page"] == 1  # the target page is not one of the run's
    keys = [
        {k for k, e in kn.entities.items() if e.type == REFERENCE} for kn in (resolved, unresolved)
    ]
    assert keys[0] == keys[1] and len(keys[0]) == 1
    (key,) = keys[0]
    assert resolved.entities[key].resolved_to is not None
    assert unresolved.entities[key].resolved_to is None


# --- Context premises, labels and readings -----------------------------------------------------


def test_a_context_premise_joins_the_statement_it_lies_in(world: SimpleNamespace) -> None:
    """An `assumption` statement whose first sentence lies in unit `#rel1` after the theorem's
    first sentence joins the theorem: its claims take the theorem's statement, and it is no
    statement of its own."""

    def context_premise(raw: dict) -> None:
        theorem = next(st for st in raw["statements"] if st.get("kind") == "theorem")
        raw["statements"].append(
            {"local_ref": "st_ctx", "kind": "assumption", "anchor": theorem["anchor"][1:]}
        )
        premise = next(c for c in raw["claims"] if c.get("statement_role") == "premise")
        premise["statement"] = "st_ctx"

    plain, _ = run(world, [world.proposal(101, "T3")])
    k, _ = run(world, [world.proposal(101, "T3", batch=edit(world.stored("T3"), context_premise))])
    assert not [e for e in k.entities.values() if e.type == STATEMENT and e.kind == "assumption"]
    assert set(k.entities) == set(plain.entities)
    (theorem,) = [key for key, e in k.entities.items() if e.label == "theorem rel1" and e.mentions]
    premises = [r for r in k.claims.values() if r.claim.statement_role == "premise"]
    assert premises and all(r.claim.statement == theorem for r in premises)


def test_a_context_premise_outside_units_keeps_its_own_statement(world: SimpleNamespace) -> None:
    """U12's standing-context premise `c1` lies in a paragraph outside units, where no other
    statement is anchored: it keeps its own statement."""
    k, _ = run(world, [world.proposal(101, "U12")])
    (statement,) = [e for e in k.entities.values() if e.kind == "assumption"]
    premise = next(r for r in k.claims.values() if r.claim.statement_role == "premise")
    assert premise.claim.statement in k.entities and statement.label.startswith("assumption ¶")


def test_an_assumption_outside_units_keeps_its_own_statement(world: SimpleNamespace) -> None:
    k, _ = run(world, [world.proposal(101, "T1-leadin")])
    (statement,) = [e for e in k.entities.values() if e.kind == "assumption"]
    assert statement.label.startswith("assumption ¶")


def test_statement_labels_follow_d2(world: SimpleNamespace) -> None:
    k, _ = run(world, [world.proposal(101, "T3")])
    labels = {e.label for e in k.entities.values() if e.type == STATEMENT}
    assert "theorem rel1" in labels  # a unit with an id: `<kind> <unit id>`
    assert all(" " in label for label in labels)
    assert {label.split(" ", 1)[1][0] for label in labels} >= {"¶"}  # blocks outside units


def test_a_page_title_is_preferred_as_the_label(world: SimpleNamespace) -> None:
    page = world.page_of_unit("T2")
    assert page.title  # the vendored page has one
    k, _ = run(world, [world.proposal(101, "T2")])
    family = next(e for e in k.entities.values() if e.type == "stat:DistributionFamily")
    labels = world.config().labels(world.compiled().names.to_prefixed)
    from corpus_structure.core.keys import normalize_label

    same = normalize_label(page.title, family.type, labels) == normalize_label(
        "normal distribution", family.type, labels
    )
    assert (family.label == page.title) is same


def test_every_value_has_a_reading(world: SimpleNamespace) -> None:
    k, _ = run(world, [world.proposal(101, "T3")])
    readings = F.read_values(k, world.inputs())
    paths = {path for _, path in readings}
    assert ("object",) in paths
    assert any(p[0] == "qualifiers" and len(p) > 2 for p in paths)  # map entries, condition leaves
    for key, row in k.claims.items():
        dump = row.claim.model_dump(mode="json", by_alias=True)
        for path, value in F.value_nodes(
            {"object": dump["object"], "qualifiers": dump.get("qualifiers", {})}
        ):
            assert value.get("parse") and (key, path) in readings


def test_each_consolidation_drop_after_keying(world: SimpleNamespace) -> None:
    """The model's `consolidation_drop` members, on a candidate set keyed without the batch checks
    (which refuse both earlier for a proposal): a stated claim left with no primary evidence is
    `malformed_evidence`; a supposed premise whose only dependant keying dropped is
    `orphaned_premise`, and claims depending on a dropped one follow (`dropped_dependency`)."""
    from corpus_structure.consolidate.assemble import Proposal, drop_after_keying
    from corpus_structure.core.keys import key_claims
    from corpus_structure.core.vocab import CONSOLIDATION_DROP, DropReason
    from corpus_structure.validate.adapter import candidates_from_batch

    page = world.page_of_unit("T2")
    cs = candidates_from_batch(world.stored("T2"), world.compiled())
    claims = []
    for c in cs.claims:
        if c.id == "c_scale_is_sd":  # no primary evidence
            c = c.model_copy(
                update={
                    "evidence": tuple(
                        e.model_copy(update={"role": "condition"}) for e in c.evidence
                    )
                }
            )
        if c.id == "c_loc_is_mean":  # the premise's only dependant; keying drops it
            c = c.model_copy(
                update={
                    "predicate": "stat:not_a_predicate",
                    "qualifiers": c.qualifiers.model_validate(
                        {"core:conditions": {"op": "claim", "ref": "c_X_normal"}}
                    ),
                }
            )
        claims.append(c)
    cs = cs.model_copy(update={"claims": tuple(claims)})
    labels = world.config().labels(world.compiled().names.to_prefixed)
    p = Proposal(101, 1, page, cs, key_claims(cs, page.ctx, world.compiled().key_schema, labels))
    assert p.keys.dropped["c_loc_is_mean"].code is DropReason.UNKNOWN_PREDICATE
    tally = Tally()
    drop_after_keying(p, tally)
    assert tally.drops == {
        DropReason.MALFORMED_EVIDENCE: {"observation:101:c_scale_is_sd"},
        DropReason.ORPHANED_PREMISE: {"observation:101:c_X_normal"},
    }
    assert set(tally.drops) == CONSOLIDATION_DROP
    assert not {"c_scale_is_sd", "c_X_normal"} & set(p.keys.claims)

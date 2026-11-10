"""Independent finite sets and hostile direct publication under native roles."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

import pytest
import yaml
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import canonical_bytes, fact_key, occurrence_key
from corpus_structure.semantic.inference import derive, publish_inference
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import (
    DerivationPremiseRow,
    DerivationRow,
    EntityRow,
    EvidenceRow,
    FactRow,
    MembershipRow,
    MembershipSupportRow,
    OccurrenceEstablishmentRow,
    OccurrenceEvidenceRow,
    OccurrenceRow,
    PublicationBatch,
    RoleRow,
    SelectionRow,
    SupportRow,
    ValueRow,
    publish_batch,
)
from corpus_structure.semantic.query import SnapshotBinding

from .inventory_reading import inventory_derivations

R, Z, C, P, Q = (
    "release:infer",
    "realization:infer",
    "https://example/Thing",
    "https://example/p",
    "https://example/q",
)


def setup(
    admin,
    writer,
    edges,
    *,
    rules=("transitive", "inverse"),
    contexts=None,
    positive=True,
    prepared=None,
    bundle=None,
    evidence=True,
    predicate=P,
    modality="asserted",
    establishment="stated",
    selected=True,
    subproperty=False,
):
    if prepared is None:
        from corpus_structure.semantic import (
            PreparationProfile,
            ResolvedDependencies,
            SourceArtifact,
            SourceBundle,
            prepare_release,
        )
        from corpus_structure.semantic.composed import composed_dependencies

        schema: dict[str, Any] = {
            "id": "https://example/inference-fixture",
            "name": "inference",
            "prefixes": {"ex": "https://example/"},
            "default_prefix": "ex",
            "types": {"string": {"base": "str"}, "boolean": {"base": "bool"}},
            "classes": {"Thing": {"slots": ["p", "q"]}},
            "slots": {
                "p": {"range": "Thing", "multivalued": True},
                "q": {"range": "Thing", "multivalued": True},
            },
        }
        if subproperty:
            schema["classes"]["Thing"]["slots"].append("child")
            schema["slots"]["child"] = {
                "range": "Thing",
                "multivalued": True,
                "is_a": "p",
                "transitive": False,
                "inverse": "q",
            }
        for kind in rules:
            if kind == "inverse":
                schema["slots"]["p"]["inverse"] = "q"
            else:
                schema["slots"]["p"][kind] = True
        bundle = SourceBundle("model", (SourceArtifact("model", yaml.safe_dump(schema).encode()),))
        prepared = prepare_release(
            bundle,
            composed_dependencies(ResolvedDependencies()),
            PreparationProfile(version="semantic-2"),
        )
        typed_qualification = False
    else:
        typed_qualification = True
    from corpus_structure.semantic import PreparationProfile, ResolvedDependencies
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.releases import persist_release

    r = prepared.release_id
    with admin.begin() as conn:
        assert bundle is not None
        persist_release(
            conn,
            bundle,
            composed_dependencies(ResolvedDependencies()),
            PreparationProfile(version="semantic-2"),
            prepared,
        )
        conn.execute(insert(table("data.project")).values(project_id="p"))
        conn.execute(
            insert(table("data.realization")).values(realization_id=Z, project_id="p", release_id=r)
        )
    entities = sorted({e for edge in edges for e in edge})
    contexts = contexts or ["same"] * len(edges)
    values = [ValueRow("v:" + e, "entity", entity_id=e) for e in entities]
    values += [
        ValueRow("modality", "string", text_value=modality),
        ValueRow("polarity", "boolean", boolean_value=positive),
    ]
    roles = []
    facts = []
    occurrences = []
    supports = []
    for i, ((s, o), ctx) in enumerate(zip(edges, contexts, strict=True)):
        q = "qual:" + str(i)
        values.extend(
            (
                ValueRow(
                    q,
                    "record" if typed_qualification else "mapping",
                    datatype="https://example/Qualification" if typed_qualification else None,
                ),
                ValueRow("scope:" + str(i), "string", text_value=ctx),
            )
        )
        roles.extend(
            (
                RoleRow(q, "modality", 0, "modality"),
                RoleRow(q, "polarity", 0, "polarity"),
                RoleRow(q, "scope", 0, "scope:" + str(i)),
            )
        )
        fid = fact_key(
            r, Z, s, predicate, o, {"modality": modality, "polarity": positive, "scope": ctx}
        )
        facts.append(FactRow(fid, s, predicate, "v:" + o, q))
        oid = occurrence_key(r, Z, "source", str(i))
        occurrences.append(OccurrenceRow(oid, fid, "source", str(i), "v:" + o, q))
        supports.append(SupportRow(fid, oid))
    batch = PublicationBatch(
        r,
        Z,
        "sources",
        entity=tuple(EntityRow(e) for e in entities),
        membership=tuple(MembershipRow(e, C, "stated") for e in entities),
        membership_support=tuple(MembershipSupportRow(e, C, "ev") for e in entities),
        occurrence_evidence=tuple(OccurrenceEvidenceRow(o.occurrence_id, "ev") for o in occurrences)
        if evidence
        else (),
        evidence=(EvidenceRow("ev", "source", "page#unit", "test", "1"),),
        typed_value=tuple(values),
        value_role=tuple(roles),
        fact=tuple(facts),
        occurrence=tuple(occurrences),
        occurrence_establishment=tuple(
            OccurrenceEstablishmentRow(o.occurrence_id, establishment) for o in occurrences
        ),
        support=tuple(supports),
        selection=tuple(SelectionRow(f.fact_id, selected) for f in facts),
    )
    receipt = publish_batch(writer, batch)
    return SnapshotBinding(r, Z, receipt.data_revision, "test"), batch


def compute(writer, binding):
    with (
        writer.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
        conn.begin(),
    ):
        return derive(conn, binding)


def projected(writer):
    with writer.connect() as conn:
        return set(
            conn.execute(
                text(
                    "SELECT f.subject_id,f.property_id,v.entity_id FROM data.fact f JOIN "
                    "data.typed_value v USING(release_id,realization_id) WHERE "
                    "f.object_value_id=v.value_id"
                )
            )
        )


def test_interacting_rules_and_canonical_context(semantic_db_engine, semantic_writer_engine):
    binding, _ = setup(semantic_db_engine, semantic_writer_engine, [("a", "b"), ("b", "c")])
    result = compute(semantic_writer_engine, binding)
    assert len(result.batch.fact) == 4
    receipt = publish_inference(semantic_writer_engine, result)
    assert projected(semantic_writer_engine) == {
        ("a", P, "b"),
        ("b", P, "c"),
        ("a", P, "c"),
        ("b", Q, "a"),
        ("c", Q, "b"),
        ("c", Q, "a"),
    }
    assert publish_inference(semantic_writer_engine, result) == receipt


def test_multiple_proofs_and_cycle_terminate(semantic_db_engine, semantic_writer_engine):
    binding, _ = setup(
        semantic_db_engine,
        semantic_writer_engine,
        [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("d", "a")],
        rules=("transitive",),
    )
    result = compute(semantic_writer_engine, binding)
    expected = fact_key(
        binding.release_id,
        Z,
        "a",
        P,
        "d",
        {"modality": "asserted", "polarity": True, "scope": "same"},
    )
    assert sum(d.conclusion_fact_id == expected for d in result.batch.derivation) >= 2
    publish_inference(semantic_writer_engine, result)
    assert projected(semantic_writer_engine) == {(a, P, b) for a in "abcd" for b in "abcd"}


@pytest.mark.parametrize("positive,contexts", [(False, None), (True, ["one", "two"])])
def test_negative_and_different_context_do_not_compose(
    semantic_db_engine, semantic_writer_engine, positive, contexts
):
    binding, _ = setup(
        semantic_db_engine,
        semantic_writer_engine,
        [("a", "b"), ("b", "c")],
        rules=("transitive",),
        positive=positive,
        contexts=contexts,
    )
    assert compute(semantic_writer_engine, binding).batch.fact == ()


def _inference_publication_state(conn, release_id, realization_id):
    """Independent persisted effects, receipts and revision of inference publication."""
    from sqlalchemy import select

    state = {}
    for name in (
        "data.realization",
        "data.batch",
        "data.fact",
        "data.typed_value",
        "data.value_role",
        "data.selection",
        "data.support",
        "data.derivation",
        "data.derivation_premise",
    ):
        relation = table(name)
        state[name] = tuple(
            dict(row)
            for row in conn.execute(
                select(relation)
                .where(
                    relation.c.release_id == release_id,
                    relation.c.realization_id == realization_id,
                )
                .order_by(*relation.primary_key.columns)
            ).mappings()
        )
    return state


def test_direct_transport_rejects_undeclared_proof_and_stale_analysis(
    semantic_db_engine, semantic_writer_engine
):
    binding, batch = setup(
        semantic_db_engine, semantic_writer_engine, [("a", "b")], rules=("inverse",)
    )
    fact = batch.fact[0].fact_id
    bad = PublicationBatch(
        binding.release_id,
        Z,
        "bad",
        derivation=(DerivationRow("d", fact, "unknown", "1"),),
        derivation_premise=(DerivationPremiseRow("d", 0, fact),),
    )
    with pytest.raises(DBAPIError, match="unadmitted inference"):
        publish_batch(semantic_writer_engine, bad)
    result = compute(semantic_writer_engine, binding)
    assert result.batch.fact and result.batch.derivation
    publish_batch(semantic_writer_engine, PublicationBatch(binding.release_id, Z, "advance"))
    with semantic_db_engine.connect() as conn:
        before = _inference_publication_state(conn, binding.release_id, Z)
    assert len(before["data.batch"]) == 2
    assert {row["batch_id"] for row in before["data.batch"]} == {"sources", "advance"}
    assert before["data.realization"][0]["data_revision"] == binding.data_revision + 1
    assert {row["fact_id"] for row in before["data.fact"]} == {fact}
    from corpus_structure.semantic.arrow_publication import StaleAnalysisError

    with pytest.raises(StaleAnalysisError, match="revision changed"):
        publish_inference(semantic_writer_engine, result)
    with semantic_db_engine.connect() as conn:
        after = _inference_publication_state(conn, binding.release_id, Z)
    assert {name: len(rows) for name, rows in after.items()} == {
        name: len(rows) for name, rows in before.items()
    }
    assert after == before
    assert result.batch.batch_id not in {row["batch_id"] for row in after["data.batch"]}


def proof(head, premises, rule="rule:symmetric"):
    version = sha256(
        canonical_bytes({"kind": rule.removeprefix("rule:"), "predicate": P})
    ).hexdigest()
    rule_id = "rule:" + version
    did = "derivation:" + sha256(canonical_bytes([rule_id, version, head, premises])).hexdigest()
    return DerivationRow(did, head, rule_id, version), tuple(
        DerivationPremiseRow(did, i, p) for i, p in enumerate(premises)
    )


def test_forged_cycle_and_ungrounded_alternate_proof_refuse(
    semantic_db_engine, semantic_writer_engine
):
    binding, sources = setup(
        semantic_db_engine, semantic_writer_engine, [("a", "b"), ("c", "d")], rules=("symmetric",)
    )
    qual = {"modality": "asserted", "polarity": True, "scope": "same"}
    a = fact_key(binding.release_id, Z, "a", P, "c", qual)
    b = fact_key(binding.release_id, Z, "c", P, "a", qual)
    da, pa = proof(a, (b,))
    db, pb = proof(b, (a,))
    bad = PublicationBatch(
        binding.release_id,
        Z,
        "cycle",
        fact=(FactRow(a, "a", P, "v:c", "qual:0"), FactRow(b, "c", P, "v:a", "qual:0")),
        derivation=(da, db),
        derivation_premise=pa + pb,
    )
    with pytest.raises(DBAPIError, match="ungrounded"):
        publish_batch(semantic_writer_engine, bad)
    # A grounded head cannot launder an ungrounded premise in an additional proof.
    reverse = fact_key(binding.release_id, Z, "b", P, "a", qual)
    d, ps = proof(sources.fact[0].fact_id, (reverse,))
    bad = PublicationBatch(
        binding.release_id,
        Z,
        "alternate",
        fact=(FactRow(reverse, "b", P, "v:a", "qual:0"),),
        derivation=(d,),
        derivation_premise=ps,
    )
    with pytest.raises(DBAPIError, match="ungrounded"):
        publish_batch(semantic_writer_engine, bad)


def test_unlocated_stated_support_cannot_seed(semantic_db_engine, semantic_writer_engine):
    binding, _ = setup(
        semantic_db_engine, semantic_writer_engine, [("a", "b"), ("b", "c")], evidence=False
    )
    assert compute(semantic_writer_engine, binding).batch.fact == ()


@pytest.mark.parametrize("seed_predicate", [P, Q])
def test_real_archived_binary_release_round_trip(
    semantic_db_engine, semantic_writer_engine, seed_predicate
):
    from corpus_structure.semantic import (
        PreparationProfile,
        ResolvedDependencies,
        SourceArtifact,
        SourceBundle,
        prepare_release,
    )
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.releases import load_release, persist_release

    schema = {
        "id": "https://example/model",
        "name": "inference",
        "prefixes": {"ex": "https://example/"},
        "default_prefix": "ex",
        "types": {
            "string": {"base": "str", "uri": "http://www.w3.org/2001/XMLSchema#string"},
            "boolean": {"base": "bool", "uri": "http://www.w3.org/2001/XMLSchema#boolean"},
        },
        "classes": {
            "Thing": {"slots": ["p", "q"]},
            "Qualification": {
                "attributes": {
                    "modality": {"required": True},
                    "polarity": {"range": "boolean", "required": True},
                    "scope": {"required": True},
                }
            },
        },
        "slots": {
            "p": {"range": "Thing", "multivalued": True, "transitive": True, "inverse": "q"},
            "q": {"range": "Thing", "multivalued": True},
        },
    }
    bundle = SourceBundle("model", (SourceArtifact("model", yaml.safe_dump(schema).encode()),))
    prepared = prepare_release(
        bundle,
        composed_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2"),
    )
    binding, _ = setup(
        semantic_db_engine,
        semantic_writer_engine,
        [("a", "b"), ("b", "c")],
        prepared=prepared,
        bundle=bundle,
        predicate=seed_predicate,
    )
    with semantic_db_engine.connect() as conn:
        assert load_release(conn, prepared.release_id) == prepared
    result = compute(semantic_writer_engine, binding)
    publish_inference(semantic_writer_engine, result)
    expected = (
        {("a", P, "b"), ("b", P, "c"), ("a", P, "c"), ("b", Q, "a"), ("c", Q, "b"), ("c", Q, "a")}
        if seed_predicate == P
        else {
            ("b", P, "a"),
            ("c", P, "b"),
            ("c", P, "a"),
            ("a", Q, "b"),
            ("b", Q, "c"),
            ("a", Q, "c"),
        }
    )
    assert projected(semantic_writer_engine) == expected
    if seed_predicate == P:
        from corpus_structure.semantic.query import read_session

        r = prepared.release_id
        qual = {"modality": "asserted", "polarity": True, "scope": "same"}
        head = fact_key(r, Z, "a", P, "c", qual)
        expected_premises = (fact_key(r, Z, "a", P, "b", qual), fact_key(r, Z, "b", P, "c", qual))
        with read_session(semantic_writer_engine, Z) as session:
            explanation = session.explain(head)
            assert explanation.binding == session.binding
            assert any(
                d.premise_fact_ids == expected_premises
                for d in inventory_derivations(session, head)
            )
    # Preserve source modality and prevent required scalar graph flags being admitted.
    schema["slots"]["p"]["range"] = "string"
    bad_bundle = SourceBundle("model", (SourceArtifact("model", yaml.safe_dump(schema).encode()),))
    bad_dependencies = composed_dependencies(ResolvedDependencies())
    bad_profile = PreparationProfile(version="semantic-2")
    bad = prepare_release(bad_bundle, bad_dependencies, bad_profile)
    from corpus_structure.semantic.publication import admit_release

    with semantic_db_engine.begin() as conn:
        persist_release(conn, bad_bundle, bad_dependencies, bad_profile, bad)
        with pytest.raises(
            ValueError, match="unsupported required native binary inference profile"
        ):
            admit_release(bad, connection=conn)


@pytest.mark.parametrize(
    "changes", [{"modality": "supposed"}, {"establishment": "agent_asserted"}, {"selected": False}]
)
def test_unauthorized_modality_establishment_and_selection_do_not_seed(
    semantic_db_engine, semantic_writer_engine, changes
):
    binding, _ = setup(
        semantic_db_engine, semantic_writer_engine, [("a", "b"), ("b", "c")], **changes
    )
    assert compute(semantic_writer_engine, binding).batch.fact == ()


def test_direct_proof_cannot_cross_canonical_contexts(semantic_db_engine, semantic_writer_engine):
    binding, sources = setup(
        semantic_db_engine,
        semantic_writer_engine,
        [("a", "b"), ("b", "c")],
        rules=("transitive",),
        contexts=["one", "two"],
    )
    head = fact_key(
        binding.release_id,
        Z,
        "a",
        P,
        "c",
        {"modality": "asserted", "polarity": True, "scope": "one"},
    )
    d, ps = proof(head, tuple(f.fact_id for f in sources.fact), "rule:transitive")
    bad = PublicationBatch(
        binding.release_id,
        Z,
        "context-crossing",
        fact=(FactRow(head, "a", P, "v:c", "qual:0"),),
        derivation=(d,),
        derivation_premise=ps,
    )
    with pytest.raises(DBAPIError, match="head/context"):
        publish_batch(semantic_writer_engine, bad)


def test_empty_seed_closure_retires_workspace(semantic_db_engine, semantic_writer_engine):
    binding, _ = setup(semantic_db_engine, semantic_writer_engine, [])
    with (
        semantic_writer_engine.connect().execution_options(
            isolation_level="REPEATABLE READ"
        ) as conn,
        conn.begin(),
    ):
        result = derive(conn, binding)
        assert result.batch.fact == ()
        assert result.batch.derivation == ()
        assert conn.scalar(text("SELECT to_regclass('pg_temp.semantic_inference_work')")) is None


def test_subproperty_inverse_and_transitivity_share_fixed_point(
    semantic_db_engine, semantic_writer_engine
):
    child = "https://example/child"
    binding, _ = setup(
        semantic_db_engine,
        semantic_writer_engine,
        [("a", "b"), ("b", "c")],
        predicate=child,
        subproperty=True,
    )
    result = compute(semantic_writer_engine, binding)
    publish_inference(semantic_writer_engine, result)
    assert projected(semantic_writer_engine) == {
        ("a", child, "b"),
        ("b", child, "c"),
        ("a", child, "c"),
        ("a", P, "b"),
        ("b", P, "c"),
        ("a", P, "c"),
        ("b", Q, "a"),
        ("c", Q, "b"),
        ("c", Q, "a"),
    }

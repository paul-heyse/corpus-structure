"""Independent finite sets and hostile direct publication under native roles."""

from __future__ import annotations

from hashlib import sha256

import pytest
import yaml
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.identity import canonical_bytes, fact_key
from corpus_structure.semantic.inference import derive, publish_inference
from corpus_structure.semantic.publication import (
    DerivationPremiseRow,
    DerivationRow,
    FactRow,
    PublicationBatch,
    publish_batch,
)
from semantic.inference_support import (
    P as P,
)
from semantic.inference_support import (
    Q as Q,
)
from semantic.inference_support import (
    Z as Z,
)
from semantic.inference_support import (
    _inference_publication_state as _inference_publication_state,
)
from semantic.inference_support import (
    compute as compute,
)
from semantic.inference_support import (
    setup as setup,
)
from semantic.inventory_reading import inventory_derivations


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


def test_interacting_rules_and_canonical_context(commit_db_engine, commit_writer_engine):
    binding, _ = setup(commit_db_engine, commit_writer_engine, [("a", "b"), ("b", "c")])
    result = compute(commit_writer_engine, binding)
    assert len(result.batch.fact) == 4
    receipt = publish_inference(commit_writer_engine, result)
    assert projected(commit_writer_engine) == {
        ("a", P, "b"),
        ("b", P, "c"),
        ("a", P, "c"),
        ("b", Q, "a"),
        ("c", Q, "b"),
        ("c", Q, "a"),
    }
    assert publish_inference(commit_writer_engine, result) == receipt


def test_multiple_proofs_and_cycle_terminate(commit_db_engine, commit_writer_engine):
    binding, _ = setup(
        commit_db_engine,
        commit_writer_engine,
        [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("d", "a")],
        rules=("transitive",),
    )
    result = compute(commit_writer_engine, binding)
    expected = fact_key(
        binding.release_id,
        Z,
        "a",
        P,
        "d",
        {"modality": "asserted", "polarity": True, "scope": "same"},
    )
    assert sum(d.conclusion_fact_id == expected for d in result.batch.derivation) >= 2
    publish_inference(commit_writer_engine, result)
    assert projected(commit_writer_engine) == {(a, P, b) for a in "abcd" for b in "abcd"}


@pytest.mark.parametrize("positive,contexts", [(False, None), (True, ["one", "two"])])
def test_negative_and_different_context_do_not_compose(
    commit_db_engine, commit_writer_engine, positive, contexts
):
    binding, _ = setup(
        commit_db_engine,
        commit_writer_engine,
        [("a", "b"), ("b", "c")],
        rules=("transitive",),
        positive=positive,
        contexts=contexts,
    )
    assert compute(commit_writer_engine, binding).batch.fact == ()


def test_direct_transport_rejects_undeclared_proof_and_stale_analysis(
    commit_db_engine, commit_writer_engine
):
    binding, batch = setup(commit_db_engine, commit_writer_engine, [("a", "b")], rules=("inverse",))
    fact = batch.fact[0].fact_id
    bad = PublicationBatch(
        binding.release_id,
        Z,
        "bad",
        derivation=(DerivationRow("d", fact, "unknown", "1"),),
        derivation_premise=(DerivationPremiseRow("d", 0, fact),),
    )
    with pytest.raises(DBAPIError, match="unadmitted inference"):
        publish_batch(commit_writer_engine, bad)
    result = compute(commit_writer_engine, binding)
    assert result.batch.fact and result.batch.derivation
    publish_batch(commit_writer_engine, PublicationBatch(binding.release_id, Z, "advance"))
    with commit_db_engine.connect() as conn:
        before = _inference_publication_state(conn, binding.release_id, Z)
    assert len(before["data.batch"]) == 2
    assert {row["batch_id"] for row in before["data.batch"]} == {"sources", "advance"}
    assert before["data.realization"][0]["data_revision"] == binding.data_revision + 1
    assert {row["fact_id"] for row in before["data.fact"]} == {fact}
    from corpus_structure.semantic.arrow_publication import StaleAnalysisError

    with pytest.raises(StaleAnalysisError, match="revision changed"):
        publish_inference(commit_writer_engine, result)
    with commit_db_engine.connect() as conn:
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


def test_forged_cycle_and_ungrounded_alternate_proof_refuse(commit_db_engine, commit_writer_engine):
    binding, sources = setup(
        commit_db_engine, commit_writer_engine, [("a", "b"), ("c", "d")], rules=("symmetric",)
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
        publish_batch(commit_writer_engine, bad)
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
        publish_batch(commit_writer_engine, bad)


def test_unlocated_stated_support_cannot_seed(commit_db_engine, commit_writer_engine):
    binding, _ = setup(
        commit_db_engine, commit_writer_engine, [("a", "b"), ("b", "c")], evidence=False
    )
    assert compute(commit_writer_engine, binding).batch.fact == ()


@pytest.mark.parametrize("seed_predicate", [P, Q])
def test_real_archived_binary_release_round_trip(
    commit_db_engine, commit_writer_engine, seed_predicate
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
        commit_db_engine,
        commit_writer_engine,
        [("a", "b"), ("b", "c")],
        prepared=prepared,
        bundle=bundle,
        predicate=seed_predicate,
    )
    with commit_db_engine.connect() as conn:
        assert load_release(conn, prepared.release_id) == prepared
    result = compute(commit_writer_engine, binding)
    publish_inference(commit_writer_engine, result)
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
    assert projected(commit_writer_engine) == expected
    if seed_predicate == P:
        from corpus_structure.semantic.query import read_session

        r = prepared.release_id
        qual = {"modality": "asserted", "polarity": True, "scope": "same"}
        head = fact_key(r, Z, "a", P, "c", qual)
        expected_premises = (fact_key(r, Z, "a", P, "b", qual), fact_key(r, Z, "b", P, "c", qual))
        with read_session(commit_writer_engine, Z) as session:
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

    with commit_db_engine.begin() as conn:
        persist_release(conn, bad_bundle, bad_dependencies, bad_profile, bad)
        with pytest.raises(
            ValueError, match="unsupported required native binary inference profile"
        ):
            admit_release(bad, connection=conn)


@pytest.mark.parametrize(
    "changes", [{"modality": "supposed"}, {"establishment": "agent_asserted"}, {"selected": False}]
)
def test_unauthorized_modality_establishment_and_selection_do_not_seed(
    commit_db_engine, commit_writer_engine, changes
):
    binding, _ = setup(commit_db_engine, commit_writer_engine, [("a", "b"), ("b", "c")], **changes)
    assert compute(commit_writer_engine, binding).batch.fact == ()


def test_direct_proof_cannot_cross_canonical_contexts(commit_db_engine, commit_writer_engine):
    binding, sources = setup(
        commit_db_engine,
        commit_writer_engine,
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
        publish_batch(commit_writer_engine, bad)


def test_empty_seed_closure_retires_workspace(commit_db_engine, commit_writer_engine):
    binding, _ = setup(commit_db_engine, commit_writer_engine, [])
    with (
        commit_writer_engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
        conn.begin(),
    ):
        result = derive(conn, binding)
        assert result.batch.fact == ()
        assert result.batch.derivation == ()
        assert conn.scalar(text("SELECT to_regclass('pg_temp.semantic_inference_work')")) is None


def test_subproperty_inverse_and_transitivity_share_fixed_point(
    commit_db_engine, commit_writer_engine
):
    child = "https://example/child"
    binding, _ = setup(
        commit_db_engine,
        commit_writer_engine,
        [("a", "b"), ("b", "c")],
        predicate=child,
        subproperty=True,
    )
    result = compute(commit_writer_engine, binding)
    publish_inference(commit_writer_engine, result)
    assert projected(commit_writer_engine) == {
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

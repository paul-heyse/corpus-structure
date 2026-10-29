"""Alignment and agreement (evaluation §3.5, §3.6, §6 P0-E-2a; D7 §5.2, §5.3, §3.3, §3.4).

Perturbations of real stored forms (`fixtures/s0` parsed onto production renditions by A0): each
compares the original (reference) with a perturbed copy (prediction), with the outcome written from
D7 §5.3 before running: the pairs matched at each tier and the fields that fail the full tier.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from corpus_structure.core import batch as B
from corpus_structure.core import values as V
from corpus_structure.evaluate.agreement import AgreementResult, unit_agreement
from corpus_structure.evaluate.align import AlignmentContext, AlignmentSide, align, assign

pytestmark = pytest.mark.filterwarnings("error::sympy.utilities.exceptions.SymPyDeprecationWarning")


def claims_of(batch: B.AuthoredBatch, ref: str, **update: Any) -> B.AuthoredBatch:
    claims = tuple(c.model_copy(update=update) if c.local_ref == ref else c for c in batch.claims)
    return batch.model_copy(update={"claims": claims})


def aligned(env: Any, name: str, perturbed: B.AuthoredBatch) -> Any:
    fx = env.s0(name)
    ctx = env.context(fx.view.macros)
    return align(fx.side(name="ref"), fx.side(fx.stored(perturbed), "pred"), ctx)


def same(*refs: str) -> list[tuple[str, str]]:
    return sorted((r, r) for r in refs)


# --- Assignment ---------------------------------------------------------------------------------


def test_masking_before_assignment_keeps_the_strong_pair() -> None:
    """Revealing case (interfaces note §5.1): assigning first keeps (0, 0) at 0.5 and drops the
    0.98 pair; masking below the threshold first keeps (1, 0)."""
    sim = np.array([[0.5, 0.0], [0.98, 0.49]])
    assert assign(sim, 0.5) == [(1, 0, 0.98)]


# --- Perturbations --------------------------------------------------------------------------------


def test_a_batch_aligns_with_itself_at_every_tier(env: Any) -> None:
    fx = env.s0("U5")
    ua = aligned(env, "U5", fx.batch)
    refs = [c.local_ref for c in fx.batch.claims]
    for tier in ("core", "full", "evidence"):
        assert ua.matches[tier] == same(*refs), tier
    assert ua.entity_unmatched_ref == [] and ua.converged


def test_a_changed_modality_fails_the_full_tier_only(env: Any) -> None:
    fx = env.s0("U5")
    claim = next(c for c in fx.batch.claims if c.local_ref == "c_S_mean")
    perturbed = claims_of(
        fx.batch,
        "c_S_mean",
        qualifiers=claim.qualifiers.model_copy(update={"modality": "supposed"}),
    )
    ua = aligned(env, "U5", perturbed)
    assert ("c_S_mean", "c_S_mean") in ua.matches["core"]
    assert ("c_S_mean", "c_S_mean") not in ua.matches["full"]
    assert ua.field_failures[("c_S_mean", "c_S_mean")] == ["modality"]


def test_an_equivalent_rewrite_keeps_the_core_tier(env: Any) -> None:
    fx = env.s0("U5")
    claim = next(c for c in fx.batch.claims if c.local_ref == "c_S_mean")
    assert isinstance(claim.object, V.Formula)
    rewritten = claim.object.model_copy(update={"latex": "\\mu_2 + \\mu_1"})
    ua = aligned(env, "U5", claims_of(fx.batch, "c_S_mean", object=rewritten))
    assert ("c_S_mean", "c_S_mean") in ua.matches["full"]


def test_swapped_values_lose_the_core_tier(env: Any) -> None:
    fx = env.s0("U5")
    by_ref = {c.local_ref: c for c in fx.batch.claims}
    mean, var = by_ref["c_S_mean"].object, by_ref["c_S_var"].object
    perturbed = claims_of(claims_of(fx.batch, "c_S_mean", object=var), "c_S_var", object=mean)
    ua = aligned(env, "U5", perturbed)
    core = dict(ua.matches["core"])
    assert "c_S_mean" not in core and "c_S_var" not in core


def test_a_dropped_premise_cascades_to_its_conclusions(env: Any) -> None:
    """When the premise `c_Xi_normal` fails the core tier (another predicate), the conclusions
    citing it in a `claim` leaf keep the core tier and fail the full tier only by the cascade."""
    fx = env.s0("U5")
    ua = aligned(env, "U5", claims_of(fx.batch, "c_Xi_normal", predicate="variance_value"))
    conclusions = {"c_S_normal", "c_S_mean", "c_S_var"}
    assert {a for a, _ in ua.matches["core"]} >= conclusions
    assert {a for a, _ in ua.cascaded} == conclusions
    assert not conclusions & {a for a, _ in ua.matches["full"]}


def test_evidence_in_another_sentence_fails_the_evidence_tier(env: Any) -> None:
    fx = env.s0("U5")
    claim = next(c for c in fx.batch.claims if c.local_ref == "c_proves")
    other = B.AuthoredEvidence(sentence="s1", quote="independent", role=claim.evidence[0].role)
    ua = aligned(env, "U5", claims_of(fx.batch, "c_proves", evidence=(other,)))
    assert ("c_proves", "c_proves") in ua.matches["full"]
    assert ("c_proves", "c_proves") not in ua.matches["evidence"]


# --- Properties -----------------------------------------------------------------------------------


@settings(max_examples=12, deadline=None)
@given(st.data())
def test_swapping_sides_transposes_and_order_does_not_matter(env: Any, data: Any) -> None:
    fx = env.s0("U5")
    ctx: AlignmentContext = env.context(fx.view.macros)
    refs = [c.local_ref for c in fx.batch.claims]
    kept = data.draw(st.lists(st.sampled_from(refs), unique=True, min_size=1))
    order = data.draw(st.permutations(kept))
    by_ref = {c.local_ref: c for c in fx.batch.claims}
    pred = fx.batch.model_copy(update={"claims": tuple(by_ref[r] for r in order)})
    a, b = fx.side(name="ref"), fx.side(fx.stored(pred), "pred")
    forward, backward = align(a, b, ctx), align(b, a, ctx)
    for tier in ("core", "full", "evidence"):
        assert sorted((y, x) for x, y in backward.matches[tier]) == forward.matches[tier]
    shuffled = fx.batch.model_copy(update={"claims": tuple(by_ref[r] for r in reversed(order))})
    again = align(a, fx.side(fx.stored(shuffled), "pred"), ctx)
    assert again.matches == forward.matches


# --- Weights on a large unit ---------------------------------------------------------------------


def test_weights_hold_beyond_a_thousand_candidates(env: Any) -> None:
    """40 x 40 core-compatible claims (1,600 candidates): the core matching has 40 pairs and, among
    them, as many full-compatible ones as exist (20 `supposed` and 20 `asserted` on each side)."""
    fx = env.s0("U5")
    base = fx.stored()
    template = next(c for c in base.claims if c.local_ref == "c_S_mean")

    def side(name: str, shift: int) -> AlignmentSide:
        claims = []
        for i in range(40):
            modality = "supposed" if (i + shift) % 2 else "asserted"
            q = B.StoredQualifiers.model_validate({"core:modality": modality})
            claims.append(template.model_copy(update={"local_ref": f"c{i}", "qualifiers": q}))
        stored = base.model_copy(update={"claims": tuple(claims), "alternatives": ()})
        return fx.side(stored, name)

    ua = align(side("ref", 0), side("pred", 1), env.context(fx.view.macros))
    assert len(ua.matches["core"]) == 40
    assert len(ua.matches["full"]) == 40
    assert set(ua.matches["full"]) == set(ua.matches["core"])  # the core matching prefers them


# --- The identity-key pass on a toy class --------------------------------------------------------


def test_the_identity_key_pass_aligns_a_toy_class(env: Any) -> None:
    """A class whose identity keys name an entity-valued slot, with no statistics name: two parts
    of aligned wholes with equal names align; a differing name is an identity near miss."""
    lookup, _ = env.statistics()
    family = lookup.entity_classes["FamilyParameter"]
    whole = dataclasses.replace(
        lookup.entity_classes["DistributionFamily"],
        name="Whole",
        prefixed="toy:Whole",
        identity_keys=(),
        entity_identity=(),
    )
    part = dataclasses.replace(
        family,
        name="Part",
        prefixed="toy:Part",
        identity_keys=("toy:whole", "toy:name"),
        entity_identity=("toy:whole",),
        identity_case={},
    )
    toy = dataclasses.replace(lookup, entity_classes={"Whole": whole, "Part": part})
    fx = env.s0("U5")
    ctx = dataclasses.replace(env.context(fx.view.macros), lookup=toy)

    def entity(ref: str, type_: str, label: str, identity: dict[str, str]) -> B.StoredEntity:
        return B.StoredEntity(
            local_ref=ref, type=type_, label=label, scope="global", identity=identity
        )

    def side(name: str, part_name: str) -> AlignmentSide:
        stored = fx.stored().model_copy(
            update={
                "entities": (
                    entity("w", "toy:Whole", "the gear train", {}),
                    entity(
                        "p",
                        "toy:Part",
                        f"part {part_name}",
                        {"toy:whole": "w", "toy:name": part_name},
                    ),
                ),
                "claims": (),
                "statements": (),
                "alternatives": (),
                "unsupported": (),
            }
        )
        return AlignmentSide(name, stored, {})

    ua = align(side("ref", "pinion"), side("pred", "Pinion"), ctx)
    assert ("p", "p") in [(p.ref, p.pred) for p in ua.entity_pairs]
    near = align(side("ref", "pinion"), side("pred", "spur"), ctx)
    assert "p" in near.entity_unmatched_ref
    assert [n[:2] for n in near.identity_near_misses] == [("p", "p")]


# --- Agreement and the pass-C diff ------------------------------------------------------------


def test_unit_agreement_and_its_diff(env: Any) -> None:
    fx = env.s0("U5")
    claim = next(c for c in fx.batch.claims if c.local_ref == "c_S_mean")
    b = claims_of(
        fx.batch,
        "c_S_mean",
        qualifiers=claim.qualifiers.model_copy(update={"modality": "supposed"}),
    )
    b = b.model_copy(update={"claims": tuple(c for c in b.claims if c.local_ref != "c_proves")})
    result = unit_agreement(
        (fx.batch, fx.frame),
        (b, fx.frame),
        fx.view,
        [fx.unit],
        env.statistics()[1],
        env.context(fx.view.macros),
    )
    assert result.tiers["core"].agreement == pytest.approx(2 * 5 / 11)
    assert result.tiers["full"].agreement == pytest.approx(2 * 4 / 11)
    assert [(d.a, d.fields) for d in result.differing] == [("c_S_mean", ("modality",))]
    assert [d.a for d in result.a_only] == ["c_proves"] and result.b_only == ()
    assert AgreementResult.model_validate_json(result.model_dump_json()) == result

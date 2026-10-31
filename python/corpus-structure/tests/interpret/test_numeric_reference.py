"""Prototype 1 on the pump passage: the joint reading beats every stream alone (D5 §14.10)."""

from __future__ import annotations

import pytest
from interpret_pump import GOLD, GROUPS, realized_value, registry, store, template

from corpus_structure.interpret.acceptance import binary_check_outcomes, evi
from corpus_structure.interpret.decisions import UNKNOWN
from corpus_structure.interpret.harness import (
    GainDecomposition,
    interaction_index,
    mobius,
    shapley,
    value_table,
)
from corpus_structure.interpret.templates.numeric_reference import (
    FULL,
    REFERENCE_RECORD,
    Mechanisms,
)

REF = "ref:this_pressure"


def _reading(groups: tuple[str, ...], mechanisms: Mechanisms = FULL):
    return template().interpret(store().masked(groups), mechanisms)


def test_all_streams_resolve_the_reference_and_every_role() -> None:
    result = _reading(GROUPS)
    assert result.accepted() == GOLD
    assert result.record(REF).probability > 0.9
    assert result.uncalibrated == ()


def test_proximity_alone_prefers_the_wrong_antecedent_and_is_not_accepted() -> None:
    record = _reading(("proximity",)).record(REF)
    assert record.option == "q_100"
    assert not record.accepted  # 0.51 is below tau = 0.75: no error is accepted


def test_no_evidence_accepts_nothing() -> None:
    assert _reading(()).accepted() == {}


def test_units_exclude_flow_rates_as_referents() -> None:
    marginal = _reading(("units",)).posterior.marginal(REF)
    assert marginal["q_120"] == 0.0 and marginal["q_100"] == 0.0
    assert marginal["q_2bar"] == pytest.approx(0.5)
    assert marginal[UNKNOWN] == pytest.approx(0.5)


def test_reference_value_is_synergy_between_stream_groups() -> None:
    def v(groups: frozenset[str]) -> float:
        return realized_value(_reading(tuple(sorted(groups))).accepted(), {REF})

    table = value_table(GROUPS, v)
    # No group resolves the reference alone; units with either partner does.
    assert all(table[frozenset({g})] == 0.0 for g in GROUPS)
    dividends = mobius(GROUPS, table)
    assert dividends[frozenset({"units", "proximity"})] == pytest.approx(1.0)
    assert dividends[frozenset({"units", "frames"})] == pytest.approx(1.0)
    assert dividends[frozenset(GROUPS)] == pytest.approx(-1.0)  # the two routes overlap
    assert sum(dividends.values()) == pytest.approx(table[frozenset(GROUPS)])
    phi = shapley(GROUPS, table)
    assert sum(phi.values()) == pytest.approx(table[frozenset(GROUPS)] - table[frozenset()])
    assert phi["units"] > phi["proximity"] == pytest.approx(phi["frames"])
    assert interaction_index(GROUPS, table, "units", "proximity") > 0


def test_gain_decomposition_by_mechanism() -> None:
    def v(mechanisms: Mechanisms) -> float:
        return realized_value(_reading(GROUPS, mechanisms).accepted())

    split = GainDecomposition(
        independent=v(Mechanisms(constraints=False, coupling=False)),
        assembly_closure=v(Mechanisms(constraints=True, coupling=False)),
        disambiguation=v(Mechanisms(constraints=True, coupling=True)),
        coverage=v(Mechanisms(constraints=True, coupling=True, window=2)),
    )
    # The role cues are accepted from the start; the unit constraint adds the reference.
    assert split.independent == 3.0
    assert split.gains["assembly_closure"] == 1.0
    assert split.total == 1.0


def test_coupling_raises_the_reference_posterior() -> None:
    loose = _reading(GROUPS, Mechanisms(coupling=False)).record(REF).probability
    joint = _reading(GROUPS).record(REF).probability
    assert joint > loose


def test_lineage_invalidates_on_withdrawal() -> None:
    record = _reading(GROUPS).record(REF)
    proximity = "x:proximity:ref:this_pressure"
    assert proximity in record.lineage.variables
    assert record.lineage.holds(record.lineage.variables)
    assert record.lineage.restrict(proximity, False).is_zero()


def test_an_llm_check_is_worth_most_where_the_joint_reading_is_unsure() -> None:
    reference = registry()[REFERENCE_RECORD]
    unsure = _reading(("proximity", "frames")).record(REF).probability  # 0.54, withheld
    sure = _reading(GROUPS).record(REF).probability  # 0.94, accepted
    llm = {"sensitivity": 0.9, "specificity": 0.9}
    value_unsure = evi(unsure, binary_check_outcomes(unsure, **llm), reference)
    value_sure = evi(sure, binary_check_outcomes(sure, **llm), reference)
    assert value_unsure > value_sure >= 0.0

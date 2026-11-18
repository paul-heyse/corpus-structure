"""Acquire maintained statistics inputs for fixtures and ordinary consumers."""

from functools import cache

from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.regeneration import acquire_pack, prepare_packs
from corpus_structure.semantic.rich_rules import RichRulePolicy
from test_preparation import preparation_fixture


@cache
def statistics_bundle():
    return acquire_pack(DOMAINS / "statistics").bundle


@cache
def prepared_statistics_pack():
    return prepare_packs((DOMAINS / "statistics",))


@preparation_fixture("statistics_pack", scope="session")
def statistics_pack_inputs():
    return prepared_statistics_pack()


@preparation_fixture("statistics_pack", scope="session")
def statistics_pack_prepared(statistics_pack_inputs):
    return statistics_pack_inputs[3]


@preparation_fixture("statistics_pack", scope="session")
def statistics_rules_policy(statistics_pack_prepared):
    return RichRulePolicy(statistics_pack_prepared)

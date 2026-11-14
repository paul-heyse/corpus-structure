"""One session-owned statistics preparation shared by its pure policy consumers."""

import pytest

from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.domain_operations import ReleasedRulesPolicy
from corpus_structure.semantic.regeneration import prepare_packs


@pytest.fixture(scope="session")
def statistics_pack_inputs():
    return prepare_packs((DOMAINS / "statistics",))


@pytest.fixture(scope="session")
def statistics_pack_prepared(statistics_pack_inputs):
    return statistics_pack_inputs[3]


@pytest.fixture(scope="session")
def statistics_rules_policy(statistics_pack_prepared):
    return ReleasedRulesPolicy(statistics_pack_prepared)

"""Controlled fresh native acquisition for current serving unit fixtures."""

from copy import deepcopy
from hashlib import sha256

import pytest

from corpus_structure.semantic import demand_results
from corpus_structure.semantic.data_operation_json import json_bytes


def index_frontier(index):
    return {
        name: list(index.frontier_rows(name))
        for name in ("obligations", "uses", "populations", "original_source_admissions")
    }


def control_frontier(monkeypatch, select):
    calls = []

    def acquire(connection, demand_id, **options):
        calls.append((demand_id, options))
        cut, frontier = select(demand_id)
        return cut, deepcopy(frontier), sha256(json_bytes(frontier)).hexdigest()

    monkeypatch.setattr(demand_results, "recheck_selected_frontier", acquire)
    return calls


@pytest.fixture
def complete_serving_code(monkeypatch):
    """Controlled producing custody for tests whose native acquisition is already simulated."""
    from corpus_structure.semantic import selected_query_cache
    from corpus_structure.semantic.code_identity import CodeIdentity
    from corpus_structure.serve import rich_queries

    def controlled_basis(contract, entry, profile, model_identity, *, callables):
        meaning = json_bytes(
            [entry, profile, model_identity, callables, contract.model_json_schema()]
        )
        code = CodeIdentity((entry,), (), (), (), meaning)
        return sha256(meaning).hexdigest(), code

    monkeypatch.setattr(rich_queries, "_installed_read_basis", controlled_basis)
    monkeypatch.setattr(
        selected_query_cache, "_authorization_scope", lambda conn: ("controlled-native-reader",)
    )

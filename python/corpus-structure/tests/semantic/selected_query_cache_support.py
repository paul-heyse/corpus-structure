"""Controlled fresh native acquisition for current serving unit fixtures."""

from copy import deepcopy
from hashlib import sha256

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

"""Controlled fresh native acquisition for current serving unit fixtures."""

from copy import deepcopy
from hashlib import sha256

import pytest

from corpus_structure.semantic import demand_results
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.selected_query_cache import SELECTED_QUERY_CACHE


@pytest.fixture(autouse=True)
def clear_selected_query_cache():
    SELECTED_QUERY_CACHE.clear()
    yield
    SELECTED_QUERY_CACHE.clear()


def index_frontier(index):
    return {name: list(index.frontier_rows(name)) for name in
            ("obligations", "uses", "populations", "original_source_admissions")}


def control_frontier(monkeypatch, select):
    calls = []

    def acquire(connection, demand_id, **options):
        calls.append((demand_id, options))
        cut, frontier = select(demand_id)
        for name, actual in (("demand_id", demand_id), ("project_id", options["project_id"])):
            if name in cut.record and cut.record[name] != actual:
                raise ValueError("selected native scope differs")
        if options.get("read_id") not in (None, cut.record["read_id"]):
            raise ValueError("selected native read differs")
        if options.get("expected_cut") not in (None, cut.identity):
            raise ValueError("selected native cut/trust assessment differs")
        return cut, deepcopy(frontier), sha256(json_bytes(frontier)).hexdigest()

    monkeypatch.setattr(demand_results, "recheck_selected_frontier", acquire)
    return calls

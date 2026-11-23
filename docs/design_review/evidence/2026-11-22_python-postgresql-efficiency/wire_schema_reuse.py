"""Compare repeated admission of actual captured wire schemas in one process."""

from __future__ import annotations

import json
from hashlib import sha256
from time import perf_counter

from corpus_structure.semantic import data_operation_wire as wire
from corpus_structure.semantic.data_operation_json import finite_json_bytes
from semantic.data_operation_port_support import captured


def main():
    contracts = wire.wire_contracts(captured())
    results = []
    iterations = 10
    for operation, direction in (
        ("read_demand_result", "input"),
        ("read_demand_result", "output"),
        ("attach_data_requests", "input"),
    ):
        content = finite_json_bytes(contracts[operation][direction])
        started = perf_counter()
        for _ in range(iterations):
            wire._check_json_schema(json.loads(content), wire.Draft7Validator.check_schema)
        direct_seconds = perf_counter() - started
        wire._checked_json_schema_content.cache_clear()
        started = perf_counter()
        for _ in range(iterations):
            declaration = json.loads(content)
            assert wire.checked_json_schema(declaration) is declaration
        reuse_seconds = perf_counter() - started
        cache = wire._checked_json_schema_content.cache_info()
        results.append(
            {
                "operation": operation,
                "direction": direction,
                "schema_bytes": len(content),
                "schema_sha256": sha256(content).hexdigest(),
                "iterations": iterations,
                "direct_seconds": direct_seconds,
                "reuse_seconds_including_first_admission": reuse_seconds,
                "cache_hits": cache.hits,
                "cache_misses": cache.misses,
            }
        )
    print(
        json.dumps(
            {
                "scope": "repeated exact schema admission with a detached dictionary each time",
                "cache_bound": wire._checked_json_schema_content.cache_info().maxsize,
                "results": results,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

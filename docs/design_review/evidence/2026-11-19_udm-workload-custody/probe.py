"""Inspect workload eligibility using the installed Python source capture."""
import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

import corpus_structure
from corpus_structure.semantic.code_identity import capture_code_identity
from corpus_structure.semantic.native_program_store import capture_generator_code


def summarize(identity):
    return {
        "complete": identity.complete,
        "discovery_sites": len(identity.discovery_unknowns),
        "required_unknowns": len(identity.unknowns),
        "common_reasons": Counter(item.reason for item in identity.unknowns).most_common(8),
        "examples": [asdict(item) for item in identity.unknowns[:6]],
    }


def main():
    root = Path(corpus_structure.__file__).resolve().parent
    result = {"generator": summarize(capture_generator_code())}
    for entry, symbol in (
        ("semantic.demand_queries", "_serve_demand_query"),
        ("serve.rich_queries", "_serve_rich_query"),
        ("serve.contribution_facets", "_serve"),
    ):
        module = "corpus_structure." + entry
        identity = capture_code_identity(root, (module,), callables=(module + "." + symbol,))
        result[entry] = summarize(identity)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

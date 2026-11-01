"""DB/provider-free wrapper controls using retained comparator pairs and frozen facts."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from author_source_references import frozen_cases, write_new
from frozen_semantic_values import assess_frozen_values, compare_value

HERE = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    probe = HERE / "comparator-probe-20261101T183506Z.json"
    retained = json.loads(probe.read_bytes())["results"]
    expected_outcomes = {
        "zero_numeric_representation": "equivalent",
        "one_numeric_representation": "equivalent",
        "different_numeric": "different",
        "power_braces": "equivalent",
        "power_different": "undecided",
        "binomial_symmetry": "equivalent",
        "replacement_factorials": "undecided",
        "multinomial_same": "equivalent",
        "multinomial_spacing": "equivalent",
        # Written values agree; binding meaning is deliberately outside this scope.
        "unresolved_binding": "equivalent",
    }
    results = []
    for row in retained:
        original = copy.deepcopy(row["right"])
        expected = str(row["left"].get("expression", row["left"].get("number")))
        decision = compare_value(expected, row["right"])
        assert decision["outcome"] == expected_outcomes[row["case"]], (row["case"], decision)
        assert decision["actual_operand"] == original == row["right"]
        assert not decision["bindings_compared"] and not decision["conditions_supplied"]
        results.append({
            "case": row["case"], "expected_outcome": expected_outcomes[row["case"]],
            "decision": decision,
        })

    frozen = frozen_cases()  # Verifies both original six-fact file hashes.
    original_frozen = copy.deepcopy(frozen)
    by_case = {row["case"]: row for row in retained}
    no_replacement = next(
        row for row in frozen["sampling"]["assertions"]
        if row["id"] == "unordered-no-replacement"
    )
    actual = by_case["binomial_symmetry"]["right"]
    claim = {"id": "control-claim", "object": actual, "qualifications": []}
    authored = {
        "units": [{"source_case": "sampling", "authored_batch": {"claims": [claim]}}],
        "assertions": [{
            "id": no_replacement["id"], "latex": actual["expression"],
            "conditions": [], "claim_ids": [claim["id"]],
        }],
    }
    original_authored = copy.deepcopy(authored)
    linkage = assess_frozen_values({"sampling": {"assertions": [no_replacement]}}, authored)
    case = linkage["cases"][0]
    assert case["actual_linked_claims"] == [claim]
    assert case["value_comparisons"][0]["outcome"] == "equivalent"
    assert case["source_context_and_conditions"]["outcome"] == "undecided"
    assert linkage["outcome"] == "partial" and linkage["evaluation"] == "performed"
    assert original_authored == authored and original_frozen == frozen

    # Cross-challenge mismatch uses two existing source values. Unsupported ellipsis
    # interpretation must be retained as an explicit unknown, not crash or inequality.
    unsupported = compare_value(no_replacement["latex"], by_case["multinomial_same"]["right"])
    assert unsupported["outcome"] == "undecided"
    assert unsupported["error_type"].endswith(".NotRepresentable")

    receipt = {
        "verified_at": datetime.now(UTC).isoformat(), "outcome": "passed",
        "scope": (
            "existing comparator pairs, exact frozen-file hashes, value-only linkage and explicit "
            "unknowns; no actual C, database, provider or extraction grade"
        ),
        "input_probe_sha256": sha256(probe.read_bytes()).hexdigest(),
        "helper_sha256": {
            name: sha256((HERE / name).read_bytes()).hexdigest()
            for name in (
                "frozen_semantic_values.py", "author_source_references.py",
                "check_frozen_semantics.py",
            )
        },
        "controls": results, "linked_claim_control": linkage,
        "unsupported_cross_challenge": unsupported,
        "actual_journeys": "not_run; waiting for coordinator source/run notification",
    }
    write_new(args.output, json.dumps(receipt, indent=2).encode() + b"\n")
    print(json.dumps({
        "outcome": "passed", "control_pairs": len(results), "receipt": str(args.output),
    }))


if __name__ == "__main__":
    main()

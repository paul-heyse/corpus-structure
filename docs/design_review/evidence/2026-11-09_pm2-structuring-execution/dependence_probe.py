"""Demonstrate the effect of replaying an attributed factor, with a two-reading oracle."""

import json
import runpy
from dataclasses import replace
from math import isclose, log
from pathlib import Path

from corpus_structure.semantic import record_interpretation as ri

ROOT = Path(__file__).resolve().parents[4]
FIXTURE = ROOT / "python/corpus-structure/tests/semantic/test_record_interpretation.py"


def main():
    helpers = runpy.run_path(str(FIXTURE))
    template = helpers["value_template"]()
    request = helpers["request"](
        template,
        {
            ("12", "pressure", "pump", "below"): 1,
            ("10", "pressure", "pump", "below"): 1,
        },
        events=(helpers["event"](),),
    )
    weights = (log(2), 0.0, 0.0)
    first = ri.LogPotential("first", ("value",), weights, ("observation",))
    repeat = replace(first, key="repeated-window")
    independent = replace(first, key="independent-witness", dependency_ids=("retrieval",))
    opposed = ri.LogPotential("opposed", ("value",), (0.0, log(2), 0.0), ("counter",))
    linked = ri.DependenceScope(("value",), ("observation",), "same retained observation")
    scenarios = {
        "one_attributed_observation": ((first,), (), 2 / 3),
        "same_observation_replayed": ((first, repeat), (linked,), 4 / 5),
        "independent_corroboration": ((first, independent), (), 4 / 5),
        "opposed_evidence": ((first, opposed), (), 1 / 2),
    }
    report = {}
    for name, (factors, scopes, expected) in scenarios.items():
        result = ri.interpret_records(
            replace(request, potentials=request.potentials + factors, dependence_scopes=scopes)
        )
        assert result.outcome is ri.Outcome.COMPLETED, (result.outcome, result.detail)
        actual = helpers["probabilities"](result)["record"]
        assert isclose(actual, expected)
        report[name] = {"expected": expected, "observed": actual}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

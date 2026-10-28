"""Run every instrument test and print the logs used in results/s0/instruments_tests.md.

    cd code/tests_instruments
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python run_all.py [--logs]
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fixtures  # noqa: E402,F401
import test_align  # noqa: E402
import test_locate  # noqa: E402
import test_locate_cascade  # noqa: E402
import test_locate_real  # noqa: E402
import test_mathgrammar  # noqa: E402
import test_validate  # noqa: E402
import test_values  # noqa: E402

from instruments import values  # noqa: E402
from instruments.schema_lookup import SchemaLookup  # noqa: E402


def main() -> int:
    suite = unittest.TestSuite()
    for mod in (test_mathgrammar, test_validate, test_locate, test_locate_cascade, test_locate_real, test_values, test_align):
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(mod))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if "--logs" in sys.argv:
        print("\n# validation cases (name, expected category, code, reported)")
        print("\n".join(test_validate.CASE_LOG))
        print("\n# planted locator cases (name, expected tier, tier, matches, score, long, span text)")
        print("\n".join(test_locate.RESULTS))
        print("\n# quote cascade against the regex probe's perturbations")
        print(json.dumps(test_locate_cascade.RESULTS, indent=1))
        print("\n# real-text locator cases")
        print("\n".join(test_locate_real.RESULTS))
        print("\n# perturbations")
        print("\n".join(test_align.LOG))
        print("# math grammar: values not read into SymPy (status, reason)")
        for r in values.PARSE_LOG:
            print(f"{r['latex']!r}\t{r['status']}\t{r['error']}")
        print("\n# S4 observations")
        print("\n".join(SchemaLookup().observations()))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())

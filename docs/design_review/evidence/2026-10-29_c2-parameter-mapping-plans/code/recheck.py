"""Reuse the frozen Q4 inspection, selecting only the changed parameter_mapping query."""
from pathlib import Path

here = Path(__file__).resolve()
source_path = here.parents[2] / '2026-10-29_c2-query-plans/code/inspect_plans.py'
source = source_path.read_text()
selection = '        for name,params in cases.items():'
assert source.count(selection) == 1
source = source.replace(selection, "        cases={'parameter_mapping':cases['parameter_mapping']}\n" + selection)
# The reused script derives its output folder from __file__. No accepted old output is rewritten.
exec(compile(source, str(source_path), 'exec'), {'__file__':str(here)})

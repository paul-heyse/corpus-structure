# Source-only semantic trace references

**Authored, 2026-10-30.** `semantic-trace-reference.json` contains one independently chosen
assertion from each of the five units in the statistics `trace` slice. Expectations were written
from the vendored HTML source and statistics semantic declaration, without reading extracted
answers. The quotations are exact production-rendition sentences. Each batch has independent
local identifiers and an explicit source scope.

These are bounded reference assertions, not exhaustive annotations of every assertion in the
units, nor an accuracy threshold. They cover the section's real-valued-variable premise, an
affine variable definition and three separately scoped normal-distribution premises with the
source's parameter names and formulas. The historical Weibull examples are different source
material and remain unchanged.

Use the explicit evaluation helper with a completed fresh trace run and evaluator credentials:

```sh
uv run python docs/design_review/evidence/2026-10-30_semantic-pivot-final/code/evaluate_sources.py \
  --project semantic-pivot --run RUN_ID --label trace-independent-v1 \
  --fixture fixtures/trace/semantic-trace-reference.json
```

The helper applies the archived document split and forced-slice policy to the completed source
cut, locates each quotation independently, writes immutable pass C and runs automated grading.
Every required in-cut forced unit must have an authored batch; out-of-cut policy locators are
recorded explicitly in sampling metadata. No source extraction process receives these files.

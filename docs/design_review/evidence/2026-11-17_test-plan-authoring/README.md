# Test plan authoring: investigations behind the test domain-model and execution series — 2026-11-17

**Question.** What is true in source, and what do the pinned libraries provide, for the
decisions the
[test domain-model and execution plan series](../../../plans/test-domain-model-and-execution_2026-11-17.md)
had to settle while it was written?

**Consumer.** That plan series and, for two of the reports, the
[design review](../../reviews/design_review_test-domain-model-and-execution_2026-11-17.md) it
implements. No record is finalized: these are readings of source and installed libraries, not
probes or measurements.

## Method and limits

Every report was produced by a delegated read-only contributor on 2026-11-17. No test,
database command, provider call or benchmark was run. Source was read in frozen exports of
`main`, so cited lines are exact for the commit each report names and will have moved since.
Paths in the reports that begin with a session scratch directory refer to those exports, which
are not retained; read the same path at the named commit instead. Each report states what it
scanned exhaustively and what it sampled.

| Report | Read at | What it holds |
|---|---|---|
| [state.md](state.md) | `50827eb9f` | The state of every site the review's findings cite, what the model-owned SQL conversion had already corrected or made worse, and what a test can observe for each reuse or skip mechanism |
| [pdf-source-consumers.md](pdf-source-consumers.md) | `50827eb9f` | The consumers of the PDF source scenario classified by whether their claim starts after the capture, and how the seed registry would express a second stage |
| [seams.md](seams.md) | `50827eb9f` | Focused design advice for the three production seams and for treating the capture workspace as a binding |
| [test-map.md](test-map.md) | `1afa63f88` | Prepared-state inventory, fixture-graph facts, boundary doubles, tests coupled to SQL text and model restatement in tests |
| [library-capabilities.md](library-capabilities.md) | pinned versions on 2026-11-17 | pytest 9.1.1, pytest-xdist 3.8.0, Hypothesis 6.170.12, cachetools 7.2.7 and PostgreSQL 18 capabilities relevant to the test system; some items are marked inferred or not confirmed |

The reports are inputs, not conclusions. Where the plan relies on one, it says so and links
the report; where a report marks something inferred, the plan makes confirming it the first
step of the package that depends on it.

# Runtime preparation and production adoption

**Measured, bounded; implementation verification separately scoped — 2026-10-30.**
The [runtime package](../../../plans/production-efficiency/runtime-preparation-and-adoption.md)
owns PE-10–PE-12 acceptance; the coordinator owns finding disposition. Existing databases,
selected answers and grades remain unchanged. Fresh work uses `corpus_efficiency_20261030` on
`18/corpus:5434`, initial native 0039, execution compiler 9/profile 5; final byte custody uses forward 0040.

## Bounded observations

`probe_archive.py` uses the real read principal and a finalized archive in the unchanged prior
operational database. Before and after select the identical release. The warm read changes from
two queries with one payload SELECT to one joined header query with no payload SELECT. The cold
read changes from four queries to five, retaining full verification and adding the header-stability
check. One observed warm interval changes from 0.00776 to 0.00186 seconds; these single observations
are not an SLA or a controlled latency comparison. Runtime/native authority checks remain outside
cache authority.

Fresh-process app import used `/usr/bin/time` and Python `-X importtime` at the same repository
entry point: 1.51 seconds/316,648 KiB maximum process RSS before, 0.20 seconds/56,280 KiB after.
Raw traces are under `raw/`. These include launcher/interpreter work and are not isolated incremental
module memory or analysis-throughput claims. Help/dispatch/MCP registration also have independent
functional checks; low import time alone does not establish their correctness.

The existing unprofiled production page route was repeated with its normal grammar deadline.
It retains 195 spans and the independent prior distribution of 174 OK, 19 ambiguous and two failed
readings, both cold and warm. This observation records 3.776 seconds rendition preparation,
7.191 seconds cold reading and 0.00250 seconds warm reading. Preparation includes first-use model
work. This does not establish an analysis speedup; the general recognizer remains selected and
F01 remains open. Native checks and an authenticated extraction process were active on the host;
these timings are not a controlled hardware benchmark. No timeout-altering profiler was used.

## Operational adoption

The fresh target was creation-only bootstrapped through `ci db init` with an owned database token.
Statistics trace run 1, transfer run 2 and source-frame run 3 were prepared unselected through the
actual CLI. Extraction uses the configured authenticated provider and fresh run-bound MCP child,
with independent reference credentials excluded. All three completed extraction/consolidation/inference and selected generation 2 through completed
replay, without another extraction. Claims, explanation and both export formats passed for all
three. Transfer preserves `12.3400`. Default CLI query and fresh stdio initialization/discovery/
queue status passed. Independent automated grades persisted for statistics (all five trace units)
and transfer; both retain zero matched reference claims, without tuning or regrading. No accuracy
threshold or human grading step is introduced. Broad final qualification is separately in progress.

Logs are retained under `build/pe1012/` during execution. Final operational receipts will be copied
under this evidence owner with source/context and failed/interrupted boundaries preserved.


## Capture and reproduction boundaries

Separate resident/spooled processes captured the same completed statistics realization: all 26
relations, 322 facts and identical logical digest/row populations. Actual exporting database handles
were released before local DuckDB aggregation. Observed process peaks were 521,728 and 529,752 KiB,
respectively; these include imports, model/boundary preparation and other live state. The small
realization does not demonstrate lower process RSS for spooling, a hard memory cap, default-limit
capacity or a throughput improvement. PE-09's separate configured-bound refusal/success case remains
its own bounded evidence. Initial observer attempts used an unavailable NullPool counter and a
removed DuckDB relation fetchone method; their failed logs remain under `raw/operational/`. Corrected
observers use SQLAlchemy checkout/checkin events and a one-row Arrow aggregate. Production was not
changed to accommodate these observer failures.

Reproduce `probe_archive.py` with an explicit reader URL for `corpus_semantic_pivot_20261030` to
observe the same prior finalized archive. The default now names the fresh target. `probe_capture.py`
requires the explicit fresh-target reader URL and `--mode resident` or `--mode spooled`.
`probe_page.py` repeats the same production page calls and prints results without overwriting older
finalized evidence. Measurements above used the existing unprofiled route; its new output was
retained here and the prior finalized bytes restored. `probe_stdio.py` exercises current defaults
and drains its owned child. Existing operational consumer/reference scripts are reused with explicit
project/run/fixture arguments; historical selections are byte-identical before and after this work.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 2 current, 0 superseded.


**production-efficiency**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Bounded runtime work removal and completed-result capture](records/runtime.efficiency.json) | PE-11 | passed | — | 2026-10-30 |
| [Final runtime adoption and applicable required-union qualification](records/runtime.adoption.json) | PE-12 | passed | — | 2026-10-30 |
<!-- evidence-index:end -->


## Final binding and acceptance

**Required-union Tested, 2026-10-30.** Native 0040 retains the physical model and kernels while
binding final implementation bytes. Final statistics/transfer/frame runs 4, 5 and 6 completed
actual provider work and all CLI consumers. Completed replay selected each result without another
extraction; separate explicit native activation put active release and selected result in agreement
at generation 4. Earlier runs 1–3 and grades remain intact; `git archive 2869e6e` supplies their
read-only source with `python/corpus-structure/src`, `domains` and `ops/postgresql` under the same
locked environment. Its initial incomplete source snapshot refused for a missing extension manifest;
the complete snapshot read successfully. No old archive was rewritten or re-admitted as new code.
Final release derivation and `ci db check` passed against the actual deployment.

Final resident/spooled capture again matches all 26 relations and 322 facts. Initial source-bound
measurements above retain their original scope; `capture_completed.py --realization
result:production-efficiency:4 --mode resident|spooled` addresses the final result. Explicit reader
URLs remain required for database-specific reproduction. New source fingerprints create new owned
products; they do not relabel the initial results. Independent source-only reference operations
persisted final grades 3 and 4 without changing grades 1 and 2, still retaining zero matched claims.

The original full run recorded 2,425 passed/three failed, including a 176.9144-second passing
78-page reading oracle. Its failures remain failed in `raw/qualification/full`. The corrected
164-case receipt under `raw/qualification/affected` covers legacy missing-frame fixture construction,
current default names, recorded scheduling-effect decoding, archive/analytics and current-policy
refusal. `required-union.json` retains 2,429 required Python nodes, none unresolved; aggregate status
remains failed because the historical invocation remains failed. The owning plan explains final-source
applicability, current strict admission and style-only evidence reuse. Actual final production
journeys/derivation/native checks cover the refreshed binding. Empty Rust discovery is `not_run`
and supplies no functional coverage. Warning-inclusive typing and all remaining applicable hygiene
checks passed. No type/test campaign followed lint-only maintenance. Finalized records distinguish
these scoped observations from an analysis speedup or global design-completeness claim.

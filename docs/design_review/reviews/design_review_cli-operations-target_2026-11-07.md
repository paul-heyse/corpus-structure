# CLI operations target review

**2026-11-07 · design/target · Interface-checked.** Independent reviewer assessed the
CLI-00–08 target at `2272ff06e` with combined library and principle focus. Core 3.3,
heuristics 1.0, test assessment 1.2 and code intelligence 1.4 apply. Evidence was static
inspection of the settings, receipt, native publication, model and transport owners and
existing dated evidence. Product qualification was `not_run` in this review.

Typer owns syntax and presentation, `just` owns recipe execution, the supervisor owns test
settlement, and managed custody owns retention. Native operations continue to own domain
identity and effects. Scoped Rich progress can consume owner status. Stdlib file replacement,
the existing no-replace publisher and local flock provide a credible bounded physical route
when composed under one lock lifetime. AST and structural observations remain separate from
semantic impact. This supports A1–A4 at target strength subject to the corrections below.

| Finding | Correction and closure |
|---|---|
| F01 · CLI-02 lock identity and liveness | Coordinate all lease acquisition and retirement in one stable namespace. Lock release after process death establishes neither child settlement nor GC eligibility. Verify hold/GC/late-reader interleavings and unsettled ownership. FP-02/05, DP-19/20, G5. |
| F02 · CLI-04/05 approval and effect fences | Use a cooperating checkout writer boundary, verify exact bytes per write and verify native target/predecessor in the effect owner. Migrate callers from implicit activation or selection. Verify interruption, wrong predecessor and stale file behavior. FP-04/05, DP-04/18/19, G1/G4/G5. |
| F03 · CLI-03 actual qualification | Validate forwarded argv and inherited policy surfaces. Serialize nextest report production through capture and require authentic child settlement. Verify an attempted lane override, overlapping report writers and signal propagation. FP-02/05/07, DP-08/19/20/23, G3/G5/G7. |
| F04 · CLI-06 read authority | Resolve read purpose for MCP inspection separately from queue write purpose. Retain the stamped UTF-8 wire budget and verify fresh stdio, wrong run and role refusal. FP-01/04, DP-01/08/18, G1/G3. |

**Decision: Revise** the affected boundaries before their consumers rely on them. Accepted
CLI-RC01–03 cover these corrections. The [CLI plan](../../plans/cli-operations_2026-11-07.md)
owns dispositions and functional evidence.

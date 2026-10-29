# Status
_Updated 2026-10-29 under the [handoff skill](.claude/skills/handoff/SKILL.md); work is on `main`._

## Increment and slice

- **SP-00–SP-05 implemented within declared profiles.** The [pivot coordinator](docs/plans/semantic-model-pivot_2026-10-29.md)
  owns state and exact acceptance commands. [SP-04](docs/plans/semantic-model-pivot/queries-and-consumers.md)
  owns semantic reads/explanation; [SP-05](docs/plans/semantic-model-pivot/interchange-and-analytics.md)
  owns shared-snapshot Arrow/DuckDB operations and protected pgpq publication.
- **ADR-0024/0025/0026 accepted:** immutable LinkML semantic releases, one derived MetaData,
  protected PostgreSQL admission and one local DuckDB engine. Core selections and ADBC share a
  snapshot; release-bound decimal profiles default to DECIMAL(38,12), HALF_EVEN. Source values stay exact.
- Query handles/continuations bind release and realization revision; changed revisions refuse.
  Occurrence/fact/accepted projections retain qualifications, evidence, unknown coverage and unresolved references.
- Typed normalized Arrow packets, scoped DuckDB fusion/aliases/views and revision-fenced binary
  COPY are implemented. pgpq 0.12.0 was added exactly pinned; arbitrary `write_arrow` was retired.
- Full producer/consolidation/serving/evaluation migration and recursive inference remain later packages.
  Legacy selected models/default runtime remain unchanged. Existing finding ownership remains
  [phase 0 §11](docs/plans/phase-0_2026-10-28.md#11-findings-disposition).

## Last verified (2026-10-29; functional source `aac9aa6`)

| Command | Outcome and scope |
|---|---|
| Scoped `uv run pytest` union (exact command in coordinator §8) | `passed`: 917 semantic/core/schema/pool/settings tests, including native PostgreSQL/ADBC/COPY |
| Explicit dbc driver `test_columnar_journey.py` (required driver-path prefix in coordinator) | `passed`: 1 native PostgreSQL → Arrow → DuckDB → protected-publication journey |
| Scoped `uv run ruff check` / `uv run pyrefly check` (coordinator) | `passed`: 0 typing errors; 18 warnings |
| `just docs-check`, `just adr-lint`, `uv run python scripts/check_pins.py`, `just ready` | `passed`: 214 pages, decision links, pins and tools |
| `just turn-end` | `passed`; incidental unchanged pre-pivot formatting restored byte-for-byte |
| `just test-all`, `just hygiene` | `not_run`: SP-10 owns assembled-series qualification |

## Operational handoff and next

- Dedicated **`cs_semantic_20261029_0f70052`**, `18/corpus:5434`, is upgraded through `semantic_0005`.
  Exact analytical release archive/activation/offline reload passed. Project `semantic-pivot` is
  generation 2; empty active `columnar-foundation` is revision 0. `semantic-foundation` remains
  revision 0 on its original release. Both full release IDs are in the coordinator. Use explicit
  database URLs; default selection remains the old database until cutover.
- The bundled ADBC driver and explicitly configured dbc PostgreSQL 1.13.0 driver both passed.
  The system driver path is operational configuration, not a semantic release dependency.
- Direct explanation premises are available; recursive inference, selective business projections
  and full current consumer integration remain SP-07/SP-08. No performance claim is made.
- Corrected initial failures retain their boundaries in package acceptance. Upstream OAK/SSSOM
  warnings remain. No owned native-test databases remain. Implementation worktrees were integrated
  and removed; paused phase-0 worktrees remain untouched.
- Next: **SP-06** producer/orchestration binding; then SP-07/SP-08 business operations/consumers,
  SP-09 regeneration/cutover and SP-10 assembled qualification. The paused phase-0 run was not restarted.

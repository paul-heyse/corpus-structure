# Status
_Updated 2026-10-29 under the [handoff skill](.claude/skills/handoff/SKILL.md); work is on `main`._

## Increment and slice

- **New pivot plan series created:** [coordinator](docs/plans/semantic-model-pivot_2026-10-29.md)
  plus six supporting plans. O01–O06 are scheduled; RC01–RC04 were explicitly accepted for
  planning on 2026-10-29. Production execution has not started; ADR changes are scheduled.
- Target: immutable LinkML/ontology releases, a stable qualified-assertion/typed-value PostgreSQL
  core, protected publication, model-governed consumers and lossless Arrow/DuckDB execution.
  SQLAlchemy Core/MetaData is central; pglast, Alembic and Pydantic/Settings have explicit roles.
- **Source inputs:** [review](docs/functional_reviews/semantic-postgresql-model_2026-10-29.md)
  and [target](docs/functional_reviews/semantic-postgresql-model_2026-10-29_target-model.md), `5ba9a5c`.
  Current code already uses psycopg-pool with SQLAlchemy NullPool; the plan preserves it.
- **Production baseline:** `7855c4a` plus preserved dirty consolidation/packet/trace changes.
  Pending worktree changes were not integrated. No production changes or dependencies were made.
- **Existing plan scopes remain unchanged:** [design-phase](docs/plans/design-phase_2026-10-28.md),
  [spikes](docs/plans/design-spikes-s0-s1_2026-10-28.md),
  [phase 0](docs/plans/phase-0_2026-10-28.md) and [roadmap](docs/plans/roadmap-phases-1-5_2026-10-28.md).
  Accepted ADRs remain in force until the scheduled decision work changes them.

## Last verified (2026-10-29; plan documents only)

| Command | Outcome and scope |
|---|---|
| `uv run --no-project --offline --no-python-downloads python /tmp/check-semantic-pivot-plans.py` | `passed`: 7 plans, 51 local links/fragments, 11 unique package anchors and titles |
| `just docs-check` | `failed`: supplied `docs/semantic_postgresql_model.md` lacks title/H1; ADR and agent lint passed before publication stopped |
| `just turn-end` | `passed` exit status; existing lint diagnostics remain; incidental source formatting/fixes reverted to preserve paused work |
| `just test-all`, `just hygiene` | `not_run`: plan creation only; no production qualification claimed |

## Known failures, blocks and decisions

- The [phase 0 coordinator §11](docs/plans/phase-0_2026-10-28.md#11-findings-disposition)
  remains the existing finding-disposition owner; no old finding was closed or transferred.
- The pivot series owns its new packages only. Old execution inventories remain subject to
  reconciliation; this turn does not resume or complete their unfinished feature scope.
- Exact library compatibility and executable ontology/constraint coverage are SP-00/SP-01
  obligations; race-safe publication and qualified mappings require native package evidence.

## Next

- When production execution is authorized, start SP-00 at the new coordinator: architectural
  decisions, supported-profile contracts and exact library compatibility disposition.
- Follow the early SP-01 → SP-02 → SP-03 → SP-04 declaration/write/query journey before broad
  consumer migration. Clean regeneration, retirement and full qualification follow working scope.

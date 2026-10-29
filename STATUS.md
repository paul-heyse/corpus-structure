# Status
_Updated 2026-10-29 under the [handoff skill](.claude/skills/handoff/SKILL.md); work is on `main`._

## Increment and slice

- **Three active plans** ([plans index](docs/plans/README.md)):
  [design-phase](docs/plans/design-phase_2026-10-28.md),
  [spike series](docs/plans/design-spikes-s0-s1_2026-10-28.md) and
  [phase 0 series](docs/plans/phase-0_2026-10-28.md) (the build); a
  [roadmap](docs/plans/roadmap-phases-1-5_2026-10-28.md) for phases 1–5.
- **Build lane:** the phase 0 series' tiers 0–3 (the domain-model alignment review integrated).
  The coordinator's header and §7 list what is built.
  - **Built:** the one LinkML model with Stage A and Stage B generation (no hand-kept mirror), with key
    scheme 1 frozen; migration 0001, the store and the repository; packs, rules and registration;
    ingest and math as registered methods; orchestration (runs, tasks, leases, the seal, fates, commands);
    parse and the MCP agent interface; the golden split and agreement; consolidation; the pool and its
    two engines.
  - **Partly built:** O2 (policy loader only), P3 (bulk writer only) and C2 (`serve/` core only).
- **Process:** probes only for fundamental uncertainty (operator, 2026-10-28). PostgreSQL: cluster
  `18/corpus` (port 5434, D3 §13), no backups.
- **Decisions in force:** ADR-0010–0015, 0018–0023 accepted (0020 one model, 0021 authorities,
  0022 schema change, 0023 declared identity; 0016 and 0017 superseded).

## Last verified (2026-10-29)

| Command | Outcome and scope |
|---|---|
| `uv run ruff check python/`, `uv run ruff format --check python/` | `passed` |
| `uv run pyrefly check python/corpus-structure` | `passed` (0 errors) |
| `just model check` | `passed` (revision 0.3.0 `a59196c4a894`) |
| `uv run pytest python/corpus-structure/tests` | `passed` except `test_db_fixtures.py::test_sweep_honours_leases_and_template_age`, which failed while a stale run was being killed; rerun alone `passed` (12) |
| Workers' final targeted runs (A1 192, I2b 131, O2 195, C2 5, P3 and M5 suites) | `passed`, per their reports |
| `just test-all`, `just hygiene` | `not_run`: phase-end checks (AGENTS.md) |

## Known failures, blocks and decisions

- Open build findings are rows in the coordinator's
  [§11](docs/plans/phase-0_2026-10-28.md#11-findings-disposition):
  - **F2E-01:** what evidence a derived claim carries. It blocks `derived_from` links.
  - **C2-01:** the `ExternalReference` descriptor is not stored.
  - **O2-01:** `PolicyAction.limit` is required, but a policy entry may omit it.
  - **O2-02:** D6 §7.1 and orchestration §3.10 disagree on how confidence `caps` are keyed. The
    design owner decides.
  - **I2A-01:** the 78-page coverage test can hang, because it forks its process pool from a
    multi-threaded process.
  - Also open: I2B-01, A1-01, P3-01, F3-02, Q4-01, IR-13, IR-14 and X2-01.
- The `docs/libraries/pgevector.md` → `pgvector.md` rename is uncommitted (the operator's), so the D9
  and S7 links fail `docs-check`.
- Q-7's partial outputs (`results/q7/`) are uncommitted and unfinalized.

## Next

- **Build lane:** finish O2, then P3 and C2. The P3 and C2 remainders are in §11 rows P3-01 and C2-01
  and in the workers' scope.
  - **O2:** slices and scope, the agent barrier, the `complete`-run protocol and the run driver.
  - **P3:** `ci export` and the `referencing.Registry`.
  - **C2:** queries, `explain` and the CLI.
- **After those:** A2 (golden server), E2b (scoring), then A3, E3, C3 and C4. E2b replaces the
  `evaluate.score` stub.
- **Phase end:** `just test-all` and `just hygiene`, then a completion audit of the phase 0 scope.

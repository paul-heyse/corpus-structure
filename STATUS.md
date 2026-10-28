# Status

_Updated 2026-10-28 under the [handoff skill](.claude/skills/handoff/SKILL.md); work is on `main`._

## Increment and slice

- **Three active plans** ([plans index](docs/plans/README.md)):
  [design-phase](docs/plans/design-phase_2026-10-28.md) (design findings, OPEN dispositions),
  [spike series](docs/plans/design-spikes-s0-s1_2026-10-28.md) (spike execution) and
  [phase 0 series](docs/plans/phase-0_2026-10-28.md) (the build); a
  [roadmap](docs/plans/roadmap-phases-1-5_2026-10-28.md) for phases 1–5.
- **Spike lane, this tranche:**
  - E5 added the `not_run` record outcome; E4a built the CPU spike environment (`e4.env-cpu`).
  - I-R2 moved the instruments to token-form keys: every S0/S0-R2 figure is unchanged
    (`*-ir2` records).
  - S4 compiled schema v0 to every phase 0 consumer
    ([report](docs/design_review/evidence/2026-10-28_design-spikes/S4-report.md)).
  - S6 smoke-tested D3's DDL, BM25, vectors, queue and keys
    ([report](docs/design_review/evidence/2026-10-28_design-spikes/S6-report.md)).
  - Their fold-in into the design (X2) waits on the operator's review of the S4 and S6 reports.
- **Build lane:** P0-F-1, P0-F-2a, P0-I-0 and P0-F-2b are built in `python/corpus-structure/`.
  An implementation review's findings are fixed (coordinator §11, IR-01…12); IR-13…15 are open
  with owners.
- **PostgreSQL:** the dedicated cluster `18/corpus` (port 5434, D3 §13) runs from
  `ops/postgresql/` via `just db-provision`. No backups yet (operator: data is regenerable; revisit
  trigger in D3 §13). The interim local cluster is retired.
- **Decisions in force:** ADR-0010–0015 and ADR-0019 (accepted). ADR-0016 (PostgreSQL), ADR-0017
  (LinkML packs) and ADR-0018 (policy routing) are proposed; their evidence (S6, S4) now exists,
  so acceptance comes with X2 and the operator's review.

## Last verified (2026-10-28)

| Command | Outcome and scope |
|---|---|
| `just check` | `passed`: pytest 442 (incl. 377 package tests on `18/corpus`), nextest 0, at `c49df48` |
| `HYPOTHESIS_PROFILE=ci uv run pytest python/corpus-structure/tests` | `passed` (377) |
| `uv run ruff check python/`, `uv run pyrefly check python/corpus-structure` | `passed` (0 errors) |
| `just evidence` | `passed`: 77 records, 0 errors (warnings on superseded records and changed inputs, expected) |
| Spike `code/tests_instruments/run_all.py` | `passed`: 79 |
| `just db-status` | `passed`: PG 18.6; preload pg_textsearch, pg_stat_statements, auto_explain; checksums on |
| `just test-all`, `just hygiene` | `not_run`: phase-end checks (AGENTS.md) |

## Known failures, blocks and decisions

- S4/S6 design implications (D2 §3, §6, §7, §9; D3 DDL fixes, BM25 kind list, query
  corrections, naming join) are proposals in the reports until X2 folds them in.
- `docs/libraries/` holds operator overviews not yet committed (pgembed, hypothesis, jsonschema,
  html5lib, pgevector, ppi_py, vllm, postgresql-18-pg-textsearch).
- Plans and evidence are never deleted (AGENTS.md); EVID-01 and APPARATUS-01 wait on the operator's
  evidence-system design.

## Next

- **Operator:** review the S4 and S6 reports, then X2 (design fold-in; ADR-0016/0017/0018).
- **Spike lane:**
  - E4b environments as S5, S2, S3 and S7 start;
  - S5-A next, because `core/tex.py` freezes on `s5.keys-property` and the grammar port waits on it;
  - then C1, I-R3, S2, S3, S7.
- **Build lane:**
  - ready now: P0-F-3 (fixtures), P0-O-0 (method contract types) and P0-S-1 (pack, compilers,
    on S4);
  - after them: P0-F-4 (metadata, migration 0001 on S6's DDL fixes);
  - see coordinator §7.

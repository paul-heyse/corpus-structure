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
  - X2 for S4 and S6: the operator accepted both reports; D1–D6 and D8 amended (prefixed names in
    everything stored, local names in authored batches).
- **Build lane:** P0-F-1, P0-F-2a, P0-I-0 and P0-F-2b are built in `python/corpus-structure/`.
  An implementation review's findings are fixed (coordinator §11, IR-01…12, IR-15); IR-13, IR-14
  and X2-01 (authored→stored naming, P0-S-1) are open with owners.
- [Audit](docs/design_review/audit/README.md) at `024bb33`; [design review](docs/design_review/reviews/design_review_domain-model-alignment_2026-10-28.md) (Revise; RC01–RC19 open).
- **PostgreSQL:** cluster `18/corpus` (port 5434, `just db-provision`, D3 §13); no backups yet
  (operator: data is regenerable; revisit trigger in D3 §13).
- **Decisions in force:** ADR-0010–0019 accepted (0016 PostgreSQL and 0017 LinkML packs Tested;
  0018 policy routing Interface-checked).

## Last verified (2026-10-28)

| Command | Outcome and scope |
|---|---|
| `just check` | `passed`: pytest 453 (incl. 388 package tests on `18/corpus`), nextest 0, at `124473d` |
| `HYPOTHESIS_PROFILE=ci uv run pytest python/corpus-structure/tests` | `passed` (388) |
| `uv run ruff check python/`, `uv run pyrefly check python/corpus-structure` | `passed` (0 errors) |
| `just evidence` | `passed`: 77 records, 0 errors (warnings on superseded records and changed inputs, expected) |
| Spike `code/tests_instruments/run_all.py` | `passed`: 79 |
| `just db-status` | `passed`: PG 18.6; preload pg_textsearch, pg_stat_statements, auto_explain; checksums on |
| `just test-all`, `just hygiene` | `not_run`: phase-end checks (AGENTS.md) |

## Known failures, blocks and decisions

- S6 follow-ups (BM25 coverage on 78 pages, vector recall, two-branch claim at 10⁵ tasks, volume
  rerun on `18/corpus`) are listed in the S6 report.
- `docs/libraries/pgevector.md` → `pgvector.md` rename uncommitted: D9 and S7 links fail docs-check.
- EVID-01 and APPARATUS-01 wait on the operator's evidence-system design.

## Next

- **Spike lane:**
  - E4b environments as S5, S2, S3 and S7 start;
  - S5-A next, because `core/tex.py` freezes on `s5.keys-property` and the grammar port waits on it;
  - then C1, I-R3, S2, S3, S7.
- **Build lane** (phase 0 series revised for the alignment review, `b874e3e`; coordinator §7):
  - ready now: P0-D-1 (ADR-0020–0023, design routes), P0-F-2c, P0-F-5, probes Q-1–Q-5, P0-F-3, P0-O-0;
  - critical paths: D1 → M1 → F2d → F2e → S1, and M2 → M3 → M4 → F4 → S1b → O1.

# Status

_Updated 2026-10-28 under the [handoff skill](.claude/skills/handoff/SKILL.md); work is on `main`._

## Increment and slice

- **Design phase:** the proposed target design is written ([D0–D9 and the worked trace](docs/design/README.md),
  all Proposed, nothing in production). Two plans are active by operator choice:
  [design-phase](docs/plans/design-phase_2026-10-28.md) (governs where they differ) and the
  [spike plan series](docs/plans/design-spikes-s0-s1_2026-10-28.md).
- **Spikes S0 and S1 executed** (2026-10-28) in
  [the design-spikes evidence folder](docs/design_review/evidence/2026-10-28_design-spikes/README.md):
  [S1 report](docs/design_review/evidence/2026-10-28_design-spikes/S1-report.md) (D1 §3 fits;
  OPEN-D1-1 answered) and [S0 report](docs/design_review/evidence/2026-10-28_design-spikes/S0-report.md)
  (claim model fits; core 0.93 / full 0.63 between blind passes; adjudication not yet determinate;
  35 gaps). Both answer their OPEN items; dispositions wait for X1.
- **ADR-0009** (math read through one extended Lark grammar; source facts as profile data;
  offset-preserving quote location; spaCy patterns for binders): implemented in the spike
  instruments; amended D1 §6.2, D2 §12.1, D4 §4.3/M01/M09/M11/M13. SymPy 1.14.0 is a hold in
  [pins](docs/pins.md).
- **ADR-0010** (evidence records): finalized results are typed records (`records/<id>.json`);
  `just evidence` regenerates indexes, the DuckDB catalog (`build/evidence.duckdb`) and checks them;
  reports render from the catalog. 31 records (30 current) for the design spikes.
- Toolchain: Python 3.14.10; Rust unpinned (rustup nightly); dev tools at latest.
- Golden and annotation subagents run on Haiku 5.5 by operator direction; S0 shows Opus
  materially better as annotator (S0 report, design implication for D7 §3).

## Last verified (2026-10-28)

| Command | Outcome and scope |
|---|---|
| `uv run pytest` | `passed`: 59 tests (incl. 7 for `corpus_evidence`) |
| `just evidence` | `passed`: 31 records, 0 errors, 1 warning (superseded `s0.m13-probe`'s output changed, expected) |
| `just docs-check` | `passed` (before S0-G; generated READMEs and record links) |
| `just adr-lint`, `ruff check`, `pyrefly check` | `passed` on the new package |
| Spike instruments `code/tests_instruments/run_all.py` | `passed`: 75 tests (spike env) |
| `just test-all`, `just hygiene` | `not_run` since the evidence package landed; run at the next scope end |

## Known failures, blocks and decisions

- X1 (fold the S0/S1 design implications into D1/D2/D4/D7, apply trace corrections, dispose the
  OPEN items) is gated on the operator's review of both reports.
- Open choice for the operator: whether finalized evidence records should outlive their folder's
  retirement (would supersede ADR-0001's evidence clause; ADR-0010 revisit).
- `scripts/docs.py` has an uncommitted operator change; new library docs in `docs/libraries/`
  are untracked (operator's).

## Next

- Operator review of the S0 and S1 reports; then X1 with design-phase Q5.
- Spikes S2–S5 can start on the S0 reference and S1 renditions (S2/S3 score against
  `results/s0/reference`); new results are finalized as records (`just evidence finalize`).

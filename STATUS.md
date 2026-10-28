# Status

_Updated 2026-10-28 under the [handoff skill](.claude/skills/handoff/SKILL.md); work is on `main`._

## Increment and slice

- **Design phase:** the target design ([D0–D9 and the worked trace](docs/design/README.md)) is
  Proposed, with S0, S1 and S0-R2 folded in (labels mark what is Tested or Measured); nothing is
  in production. The active plan is [design-phase](docs/plans/design-phase_2026-10-28.md); the
  [S0/S1 spike plan series](docs/plans/design-spikes-s0-s1_2026-10-28.md) is **complete**, its
  file's disposition pending the operator's revised process.
- **Design authority:** the in-repo agent holds primary design authority (operator direction,
  2026-10-28); the project-conversation Claude reviews for missing design reasoning. Its S0/S1
  review is dispositioned
  ([response](docs/design_review/evidence/2026-10-28_design-spikes/design-authority-response-S0-S1.md)).
- **Decisions in force:**
  - ADR-0010: evidence records and catalog.
  - ADR-0011: Sonnet 5.5 is the golden author, working from guideline v1 (D2 §10), the
    schema-generated annotator reference and query-assembled context.
  - ADR-0012, superseding ADR-0009: one math grammar; keys from the token form; source facts as
    profile data; offset-preserving quote location.
- **Evidence** ([folder](docs/design_review/evidence/2026-10-28_design-spikes/README.md), 46
  records): S1, S0 and S0-R2 reports. Under inputs v1, full-tier agreement from packets is Sonnet
  0.77 and Haiku 0.68, against 0.37 and 0.35 before and 0.68 for the Opus v0 passes.
  html5lib renditions are content-identical to libxml2's on the seven reference pages.
- Toolchain: Python 3.14.10; Rust unpinned (rustup nightly); pylatexenc 3.0b2 and SymPy 1.14.0
  are holds in [pins](docs/pins.md).

## Last verified (2026-10-28)

| Command | Outcome and scope |
|---|---|
| `uv run pytest` | `passed`: 59 tests (incl. 7 for `corpus_evidence`) |
| `just evidence` | `passed`: 46 records, 0 errors, 4 warnings (all on superseded records, expected) |
| `just docs-check`, `just adr-lint` | `passed` (after the review disposition) |
| `just hygiene` | `passed` earlier on 2026-10-28; docs-only changes since |
| Spike instruments `code/tests_instruments/run_all.py` | `passed`: 75 tests (spike env) |
| `just test-all` | `not_run` since the evidence package landed; run at the next scope end |

## Known failures, blocks and decisions

- Plans and evidence are never deleted (operator direction; `AGENTS.md` overrides ADR-0001's
  retirement clause). The operator will propose the evidence system, including the reusable
  apparatus; findings rows EVID-01 and APPARATUS-01 wait on it.
- `scripts/docs.py` has an uncommitted operator change; new library docs in `docs/libraries/`
  are untracked (operator's).

## Next

- Spikes S2, S3 and S5 against the v1 reference (`results/s0r2/reference_v1`, libxml2 renditions);
  S4 and S6 alongside; S7 after S2 (briefs updated 2026-10-28).
- Open before or early in phase 0: OPEN-D1-5 (`extref`), STMT-01's key figures (S6), the
  property test for token keys (S5, P0.5b); guideline v2 and schema v0.2 rows OPEN-D2-7…20.
- Then the phase 0 build plan (design-phase Q9, D9 §5).

# Status

_Updated 2026-10-28 under the [handoff skill](.claude/skills/handoff/SKILL.md); work is on `main`._

## Increment and slice

- **Three active plans** (operator, 2026-10-28; [plans index](docs/plans/README.md)):
  [design-phase](docs/plans/design-phase_2026-10-28.md) owns design findings and OPEN dispositions;
  the [spike series](docs/plans/design-spikes-s0-s1_2026-10-28.md) owns spike execution (S0/S1
  done; S2–S7 planned, queue rows 23–34); the [phase 0 series](docs/plans/phase-0_2026-10-28.md)
  owns the build (coordinator plus seven documents in `docs/plans/phase-0/`; nothing built). A
  [roadmap](docs/plans/roadmap-phases-1-5_2026-10-28.md) sketches phases 1–5.
- **Design:** D0–D9 and the trace are Proposed. The phase 0 contract layer had a design/target
  review ([report](docs/design_review/reviews/design_review_phase0-contract-layer_2026-10-28.md),
  decision Revise); the operator confirmed all 14 rule changes, and they and the reconciliation of
  the seven documents' contract sheets are folded into D0–D9 (coordinator §9.1 lists routes).
- **Decisions in force:** ADR-0010 (evidence records); ADR-0011 (Sonnet golden author); ADR-0012
  (one math grammar, token-form keys); ADR-0013 claim model, ADR-0014 observations and per-run
  materialization, ADR-0015 agent work queue, ADR-0019 identity follows content (accepted).
  Proposed until their spikes report: ADR-0016 PostgreSQL (S6), ADR-0017 LinkML packs (S4),
  ADR-0018 policy routing (S4).
- **Phase 0 scope** (operator, 2026-10-28): Opus extracts the four spike pages whole plus the dev
  golden units by locator, about 234 packets
  ([evidence](docs/design_review/evidence/2026-10-28_phase0-golden-size/README.md)); the full first
  pass is phase 1. Lexical search is BM25 through pg_textsearch.
- **Library research** for the phase 0 plans: four notes in
  `docs/design_review/evidence/2026-10-28_library-*` (probes, no records).

## Last verified (2026-10-28)

| Command | Outcome and scope |
|---|---|
| `just docs-check` | `passed` (178 pages) at `bf66392` |
| `just adr-lint` | `passed`: 17 records |
| `just evidence` | `passed`: 46 records, 0 errors, 4 warnings (S0 report inputs changed since finalization) |
| `just turn-end` | `passed` |
| Phase 0 graph check (scratch script) | `passed`: 28 packages, acyclic, prerequisites match the documents |
| `uv run pytest`, `just test-all`, `just hygiene` | `not_run` this session: documentation only |

## Known failures, blocks and decisions

- **Operator setup before database work:** add `pg_textsearch` to `shared_preload_libraries`,
  restart PostgreSQL, and create it (and later `vector`) as `postgres` in the template database
  the project clones (D3 §3); S6 can use `pg_virtualenv` instead.
- **Untracked operator files:** seven new overviews in `docs/libraries/` (html5lib, hypothesis,
  jsonschema, pgevector, postgresql-18-pg-textsearch, ppi_py, vllm); committed design text links
  them. `scripts/docs.py` may still hold an operator change.
- Plans and evidence are never deleted (AGENTS.md); EVID-01 and APPARATUS-01 wait on the
  operator's evidence-system design.
- The four `just evidence` warnings are on S0 report inputs regenerated after finalization.

## Next

- Spike lane: E4 environments, I-R2 instrument revision, E5, C1 (contested items); then S4 and S6
  (phase 0's critical path), S5-A (grammar, token keys), then S2, S3, S7 (spike coordinator §5).
- Build lane, ready now: P0-F-1, then P0-F-2a and P0-I-0, then P0-F-2b and P0-O-0 (coordinator §7).
  P0-S-1/-2 are drafted against the schema-rules note and finalized on `s4.*`; P0-F-4 waits on
  `s6.*` and the operator setup; P0-I-2a waits on S5-A; `core/tex.py` freezes on
  `s5.keys-property`.

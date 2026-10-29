# Status
_Updated 2026-10-29 under the [handoff skill](.claude/skills/handoff/SKILL.md); work is on `main`._

## Current checkpoint

- **SP-06/SP-07 implemented and scoped Tested for their supported profile, including exclusions.**
  [Coordinator §11](docs/plans/semantic-model-pivot_2026-10-29.md#11-sp-06sp-07-remaining-scope-completion-2026-10-29)
  owns actual receipts and the package conclusion; the
  [completion audit](docs/plans/semantic-model-pivot/domain-operations.md#completion-audit-2026-10-29)
  records the reconciled original obligations, independent crossing reviews and evidence limits.
- Compiler 9 / semantic-domain-2 / analytical-4 and frozen semantic_0027 implement LinkML-owned
  identity exclusions, existing source/input assignments, native source/evidence/omission checks,
  deterministic label vetoes and atomic mandatory-key conflict refusal. Current automated MCP,
  snapshot/explanation, qualified RDF and Arrow/DuckDB paths adopt them. ADR-0029 owns the decision.
- SP-C01–SP-C05 remain implemented/scoped Tested. Coordinator §10 owns completeness opportunities;
  O07 retains later SP-08–SP-10 follow-through. This is not assembled-series qualification.
- No dependency versions moved, operational deployment/default cutover, regrading or paused
  phase-0 restart occurred. Grading/adjudication remain automated without human input.

## Verification (2026-10-29)

- **passed:** original 488-case semantic/Settings selection covered across passing unaffected and
  repaired selections. Initial run failed (4 failed/484 passed); no single final full rerun claimed.
- **passed:** 16 metadata/source/inherited-reader cases; final 31 affected native/proposal/source/
  explanation/graph/Arrow cases after repairs. Earlier failures remain recorded in coordinator §11.
- **passed:** `uv run --no-sync pyrefly check --summary=none`, zero whole-project errors before lint.
- **passed:** final `just turn-end`, `uv run --no-sync ruff check --output-format=concise`,
  and `just docs-check` (229 canonical pages; no publication/link errors). Earlier lint and
  ADR-reference publication failures were corrected. No tests/types repeated after lint.
- **not_run:** enclosing `just test-all` / `just hygiene`; SP-10 owns assembled qualification.
  Lint-only maintenance does not invalidate passing tests/types or require their repetition.

## Next boundary

- SP-08 adopts remaining consumers; SP-09 regenerates/deploys; SP-10 qualifies the combined union.
- Operational database cs_semantic_20261029_0f70052 at 18/corpus:5434 remains semantic_0005;
  only owned fresh test databases exercised semantic_0027. Existing findings remain with
  [phase 0 §11](docs/plans/phase-0_2026-10-28.md#11-findings-disposition).

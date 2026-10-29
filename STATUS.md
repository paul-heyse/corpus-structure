# Status
_Updated 2026-10-29 under the [handoff skill](.claude/skills/handoff/SKILL.md); work is on `main`._

## Current checkpoint

- **SP-08 implemented with scoped Tested evidence; SP-09 partially realized; SP-10 incomplete.**
  [Coordinator §12](docs/plans/semantic-model-pivot_2026-10-29.md#12-sp-08sp-10-implementation-checkpoint-2026-10-29)
  owns current disposition, verification and remaining obligations. Source baseline: `feeefad`.
- Semantic CLI/MCP serving, queries/explanations, selected-result bindings, protected independent
  references, qualified exports and archived-run regeneration are integrated under ADR-0030.
  Compiler 10 / semantic-domain-2 / analytical-4; native revisions through semantic_0030.
- New `corpus_semantic` deployment on 18/corpus:5434 has selected completed statistics run 1
  and transfer run 2. Real extraction, resumption, query and JSONL/Parquet exports completed.
  Independent reference grading executed automatically; its zero-match grade remains unchanged.
- Fresh MCP run 3 is sealed/consolidating without a result: a literal native `SourceStatement`
  guard rejects valid `ToySourceStatement`. The correction must consume the admitted release's
  `AgentStatementBinding.statement` range and hierarchy. No active/applied 0031 correction exists.
- SP-06/SP-07 and SP-C01–SP-C05 retain their supported-profile scoped evidence in coordinator
  §§10–11. O07 and assembled qualification remain open; no extraction-accuracy campaign is claimed.
- All worker contributions are integrated, owned worktrees removed and owned test processes/database
  cleaned up. The earlier operational database and existing MCP process remain untouched.
  Concurrent library-leverage recommendations retain their separate owner and are not adopted here.

## Verification (2026-10-29)

- **passed:** `just types`, zero whole-project Pyrefly errors/warnings, domain plug-ins included;
  all source/test/generator suppressions removed. `just ready` passed after exact typing-stub pins.
- **passed:** focused consumer/native/reference/CLI/source-frame checks and 143 model/source cases;
  exact scopes and retained outputs are in
  [the evidence folder](docs/design_review/evidence/2026-10-29_semantic-consumer-regeneration/README.md).
- **failed:** first `just test-all`, six Python collection errors, subsequently repaired.
  Revised `just test-all` is **incomplete, not passed**: an early failure marker, no completed
  assertion summary, exit 143. Existing scoped passes retain their credit.
- **not_run:** full `just hygiene`; assembled SP-10 acceptance remains open.
- **passed:** `just turn-end` (ADR index, formatting and safe fixes).
- **failed:** `uv run ruff check --output-format=concise`, 64 remaining lint diagnostics.
- **passed:** `just docs-check`, 268 canonical pages and zero publication/link errors.
- **failed:** global `just evidence`, five errors in older records (two unresolved dependencies
  and three missing hashes), plus 37 warnings. The new partial checkpoint record finalized.
  Maintenance does not invalidate passing types/tests; none were repeated after lint.

## Next boundary

- Review native model/guard coupling, implement the release-binding correction, complete the fresh
  frame journey and resolve applicable remaining functional/provider/nonfunctional qualification.
  [SP-09/SP-10](docs/plans/semantic-model-pivot/regeneration-and-acceptance.md) owns that boundary.
- Original phase-0 findings remain with [phase 0 §11](docs/plans/phase-0_2026-10-28.md#11-findings-disposition).

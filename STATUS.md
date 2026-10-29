# Status
_Updated 2026-10-29 under the [handoff skill](.claude/skills/handoff/SKILL.md); work is on `main`._

## Increment and slice

- **SP-00–SP-03 implemented within declared profiles.** The [pivot coordinator](docs/plans/semantic-model-pivot_2026-10-29.md)
  owns current state; the [PostgreSQL package](docs/plans/semantic-model-pivot/postgresql-and-publication.md)
  owns persistence, activation, protected COPY publication and explicit refusal limits.
- **ADR-0024/0025 accepted:** one immutable semantic release, one model-derived MetaData,
  separate frozen Alembic target, restricted authenticated roles and publisher-owned staging.
  Occurrences retain full report objects/qualifications while equal facts share meaning.
- Exact archives reload offline; parent+generation CAS preserves bound realizations. Publication
  verifies native identities/content, shape/accepted-value constraints, scopes and immutable value
  graphs. Selection replacement retains reports. One owner retries whole SERIALIZABLE transactions.
- Compiler profile is `2`; ontology sources are explicitly selected from exact dependencies.
  Pglast 8.7 moved to product dependencies without a version change. Existing pins remain.
- The selected legacy core/system model, generated metadata and default runtime remain unchanged.
  Old plan/finding ownership remains [phase 0 §11](docs/plans/phase-0_2026-10-28.md#11-findings-disposition).

## Last verified (2026-10-29; functional source `0f70052`)

| Command | Outcome and scope |
|---|---|
| `uv run pytest python/corpus-structure/tests/semantic python/corpus-structure/tests/core python/corpus-structure/tests/schema --tb=short` | `passed`: 858 tests, native package controls plus core/schema regressions |
| Scoped `uv run ruff check` and `uv run pyrefly check` (exact paths in coordinator) | `passed`: 0 typing errors; 14 warnings |
| `just docs-check`, `just adr-lint`, `uv run python scripts/check_pins.py`, `just ready` | `passed`: 213 pages, decision links, pins and tools |
| `just turn-end` | `passed`; incidental pre-pivot formatting restored byte-for-byte |
| `just test-all`, `just hygiene` | `not_run`: SP-10 owns assembled-series qualification |

## Operational handoff and next

- Fresh database **`cs_semantic_20261029_0f70052`**, dedicated `18/corpus:5434`, is bootstrapped
  through `semantic_0003`. Exact semantic core archive/activation/offline reload and actual
  `corpus_sem_writer`/`corpus_sem_reader` authentication passed. Project `semantic-pivot` generation
  1 binds active realization `semantic-foundation`, revision 0, no facts. Full release ID is in the
  coordinator. Use explicit database URLs; the default remains the old database until cutover.
- Profile refusals include occurrence/context grouping, regex, required graph integrity and float
  numeric bounds. Unsupported opaque/language storage and unused physical aliases refuse writes;
  core interval/expression/missing variants use typed records. No crash-durable ack is promised.
- Initial failures and fixes are retained in the package acceptance account. Upstream OAK/SSSOM
  deprecation and LinkML repeated-attribute diagnostics remain. No owned native-test DBs remain.
- Implementation worktrees were integrated and removed; paused phase-0 worktrees are untouched.
- Next is **SP-04**: declaration → qualified publication → semantic query/explain. SP-05 can
  develop lossless Arrow/DuckDB binding/loader work independently. Consumer cutover, regeneration
  and whole-series qualification remain open; the paused phase-0 run was not restarted.

# Status
_Updated 2026-10-29 under the [handoff skill](.claude/skills/handoff/SKILL.md); work is on `main`._

## Increment and slice

- **SP-00/SP-01 implemented:** [pivot coordinator](docs/plans/semantic-model-pivot_2026-10-29.md)
  owns current state; [semantic scope](docs/plans/semantic-model-pivot/semantic-model-and-releases.md)
  owns contracts. Explicit preparation produces immutable definitions, adapters, identities,
  logical registry/query products and JSON Schema/OWL/SHACL artifacts without DB activation.
- **ADR-0024 accepted:** replaces ADR-0013/0019/0020–0023's target clauses, carrying source fidelity,
  qualification, instance authority and staged-runtime guarantees forward. ADR-0014 policy remains.
- **Native ontology stack:** LinkML/runtime 1.12.1, RDFLib 7.6.0, PySHACL 0.40.1, OAK 0.7.4,
  Valuesets 0.4.2, Term Validator 0.4.5. Python remains 3.14.10; support range is 3.14.
  Only existing setuptools moved (84.2.1 → 81.0.0 for OAK); application pins were preserved.
- Selected legacy model, generated database metadata and runtime remain unchanged. No database
  deployment, release activation, migrated consumers or assembled pivot qualification is claimed.
- Existing plan scope/finding ownership remains unchanged; only one stale old-plan hyperlink was
  repaired. [Phase 0 §11](docs/plans/phase-0_2026-10-28.md#11-findings-disposition) still owns its findings.

## Last verified (2026-10-29; bounded foundation scope)

| Command | Outcome and scope |
|---|---|
| `just ready`, `uv run python scripts/check_pins.py` | `passed`: tools and exact dependency policy |
| `uv run pytest python/corpus-structure/tests/semantic` | `passed`: 50 final-source tests |
| `uv run pytest python/corpus-structure/tests/semantic python/corpus-structure/tests/core python/corpus-structure/tests/schema` | `passed`: 777 tests before final two semantic controls; final 50 semantic tests cover those corrections |
| `uv run ruff check python/corpus-structure/src/corpus_structure/semantic python/corpus-structure/tests/semantic` | `passed` |
| `uv run pyrefly check python/corpus-structure/src/corpus_structure/semantic python/corpus-structure/tests/semantic` | `passed`, 0 errors |
| `just docs-check` | `passed`: 212 pages after H1/stale-link repairs; earlier failed records retained |
| `just turn-end` | `passed`; incidental legacy formatting/fixes restored byte-for-byte |
| `just test-all`, `just hygiene` | `not_run`: SP-10 owns assembled-series qualification |

## Limits and next

- Prepared capabilities are requirements for later lowering, not database-enforced guarantees.
  Unsupported semantics and scope-weakening overrides refuse; unavailable/unchecked ontology
  metadata stays explicit. No historical readers, dual writes or compatibility upcasters added.
- Next is SP-02: persist/activate immutable releases and realize the stable schema via SQLAlchemy
  MetaData/Alembic. SP-03 implements protected transactional publication. Later packages migrate
  consumers, regenerate data and retire the selected legacy path.
- Continue from the new coordinator, not old phase 0 completion headers. Existing worktrees from
  the paused task are preserved; this scope does not integrate their unfinished work.

# Status

_Updated 2026-11-18. The owned stage and canonical development database run model-built N13. Development registered and read-verified 29 originals. Whole-book execution and DDO-12 qualification remain open._

## Current owners

- The [DDO coordinator](docs/plans/declared-data-operations_2026-11-12.md#generated-ddo-acquisition-settlement-and-inspection--2026-11-18) owns deployment, scoped failures and qualification. The [PostgreSQL companion](docs/plans/declared-data-operations/postgresql-realization-and-retirement.md#model-owned-sql-authoring) owns typed SQL authoring under [ADR-0131](docs/adr/0131-model-owned-postgresql-programs.md).
- N12 generated the protected PDF companion, observation, export, proof, identity and correspondence paths. N13 generates DDO compiler, acquisition, reads, settlement, external packet custody, grading and operation-event publication. The handwritten DDO operation bundle and its string fragment substitutions are retired.
- The [adoption companion](docs/plans/declared-data-operations/preservation-adoption-and-qualification.md#actual-preservation-basis) owns original custody and regeneration.

- [Library-discovery tooling](tooling/docs/plans/library-discovery-tooling_2026-11-17.md#current-state) (LDT series, [ADR-0132](docs/adr/0132-tooling-package.md)) is implemented for LDT-00–08: the `tooling library` commands `baseline`, `selection`, `metadata`, `inventory`, `census`, `compare` and `overview`, with the discovery guide and skill pointing to them. Verified 2026-11-17: `uv run ci test -- tooling/tests tests/scripts/test_test_receipts.py` passed (`8cd3bc5aa2b24d5a9e5d8d4c4a69270b`, 302 tests) and `uv run ci check` passed (`34811b452107403d90e5035f8a2e0550`); the full product suite is `not_run` for this series (no product change). Conditional LDT-C1–C3 are unstarted and wait for their triggers; the series owns known limits and next work.

## Last verified · 2026-11-18

- **Passed:** `ci model change` authored, registered and deployed N13 on stage OID 130661481 in `e9e7e3fde9394def9bbbc2c430899fd0`. Its separately admitted application passed `ci db check`, `ci release check` and activation at generation 14. The stage capture precedes the encoder and predicate fixes now in the development capture.
- **Passed:** `ci db init` and `ci db status --maintenance` confirmed canonical development OID 131763263 and N13. Dev application deployment `d6ea36869d794732811b89ee8d405eed`, `ci db check`, `ci project init --original-descriptors`, and the book project activation and release check passed. Independent reader readback verified every descriptor field and retained byte across 29 originals and nine projects. The old database remains fenced at its original OID 25921445.
- **Scoped:** 73 PDF controls passed at N12 (`f6544d5c3bee4cb5af0360c23596e8b8`). N13's integrated attempt `be66da57a0a44cf3b6aa420cb7e77c37` reported 135 passes and 13 failures. Its retained retries establish specific fixes and leave two binding refusal controls open. The E5 and NCE attempts reached later boundaries after production fixes, then exposed fixture acquisition and scope issues. The corrected fixtures await verification.
- **Passed:** 17 construction grammar controls, including the bounded production-region comparator. Its actual-book inputs and full comparison remain open.
- **Passed:** `uv run ci check --only types` (`e9fe0c43827c47e2a9cee897e5325e66`) and `uv run ci check --only lint` (`6dd3dda0b0a744c4a5dcd0925c0a22b4`).

## Next execution

- Verify the remaining binding refusal matrix and corrected E5 and NCE paths against the current source. Reacquire the latest stage application when current-source correspondence is required.
- Run the full 518-page book demand through committed progress, interruption, same-demand resume and repeat. Use its current source, formal and sentence products for PE-S33. Complete the required native, provider, public, fault and repository-check union for DDO-12. Chandra OCR remains excluded.

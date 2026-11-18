# Status

_Updated 2026-11-18. Model-built N17 and its matching application are active on the owned stage. Canonical development runs N13. Development adoption, whole-book execution and DDO-12 qualification remain open._

## Current owners

- The [DDO coordinator](docs/plans/declared-data-operations_2026-11-12.md#scoped-acquisition-and-native-authoring-integration--2026-11-18) owns deployment, scoped failures and qualification. The [PostgreSQL companion](docs/plans/declared-data-operations/postgresql-realization-and-retirement.md#model-owned-sql-authoring) owns typed SQL authoring under [ADR-0131](docs/adr/0131-model-owned-postgresql-programs.md).
- N12 generated the protected PDF companion, observation, export, proof, identity and correspondence paths. N13 generates DDO compiler, acquisition, reads, settlement, external packet custody, grading and operation-event publication. The handwritten DDO operation bundle and its string fragment substitutions are retired.
- N14–N16 added explicit producer dependencies, typed guards and event replies, stable kind schemas, immutable public cuts, per-output evidence, and discovery readiness. N17 converted companion envelopes and catalog checks. N18 source removes the last maintained standalone SQL template and repairs public projection and dossier source eligibility. The PostgreSQL companion owns remaining inline authoring.
- The [adoption companion](docs/plans/declared-data-operations/preservation-adoption-and-qualification.md#actual-preservation-basis) owns original custody and regeneration.
- The [test-domain coordinator](docs/plans/test-domain-model-and-execution_2026-11-17.md#implementation-evidence) owns TDM implementation, observed native results and qualification. Model-bound fixtures, deployment identity, sealed capture, PDF and executor protocols, and `ci test review` are integrated. The registered TDM PDF native successor supplies the test head.
- The [test audit refresh](docs/design_review/test-audit/README.md#tdm-refresh-2026-11-18) records the scope inspected against the integrated source. The coordinator owns the outstanding composition and rich admission results.

- [Library-discovery tooling](tooling/docs/plans/library-discovery-tooling_2026-11-17.md#current-state) (LDT series, [ADR-0132](docs/adr/0132-tooling-package.md)) is implemented for LDT-00–08: the `tooling library` commands `baseline`, `selection`, `metadata`, `inventory`, `census`, `compare` and `overview`, with the discovery guide and skill pointing to them. Verified 2026-11-17: `uv run ci test -- tooling/tests tests/scripts/test_test_receipts.py` passed (`8cd3bc5aa2b24d5a9e5d8d4c4a69270b`, 302 tests) and `uv run ci check` passed (`34811b452107403d90e5035f8a2e0550`); the full product suite is `not_run` for this series (no product change). Conditional LDT-C1–C3 are unstarted and wait for their triggers; the series owns known limits and next work.

## Last verified · 2026-11-18

- **Passed:** `ci model change candidate`, `register` and `deploy` for N17 on stage OID 130661481 (`3ce79909810c4a609c818aa51c10d517`, `885fedcf388d49db956807878e6df1ec`, `03f6aabfc24743808b27a091cab90637`). Sixteen native transitions replayed. Application deployment `7f819310fe094688a1c093cd21fdb7b8`, `ci db check`, and `ci release check` passed. `ci release activate` moved the bounded stage project to generation 16.
- **Passed:** `ci db init` and `ci db status --maintenance` confirmed canonical development OID 131763263 and N13. Dev application deployment `d6ea36869d794732811b89ee8d405eed`, `ci db check`, `ci project init --original-descriptors`, and the book project activation and release check passed. Independent reader readback verified every descriptor field and retained byte across 29 originals and nine projects. The old database remains fenced at its original OID 25921445.
- **Scoped:** 73 PDF controls passed at N12 (`f6544d5c3bee4cb5af0360c23596e8b8`). N13's integrated attempt `be66da57a0a44cf3b6aa420cb7e77c37` reported 135 passes and 13 failures. Its retained retries establish specific fixes and leave two binding refusal controls open. The E5 and NCE attempts reached later boundaries after production fixes, then exposed fixture acquisition and scope issues. The corrected fixtures await verification.
- **Passed:** 17 construction grammar controls, including the bounded production-region comparator. Its actual-book inputs and full comparison remain open.
- **Passed:** `uv run ci check --only types` (`b93ef3f01de949a1b3696297f3e7aed4`) and `uv run ci check --only lint` (`390d08dabdc04bea95c5ab13f0d1a9c3`). Actual encoder and CUDA GLiNER panels passed all ten selected cases (`f9915746efeb4acab5b282585a0db218`).

- **Passed:** TDM `uv run ci test collect` selected 8,824 identities (`4df04e0f488641be913bfdded8b03c2b`). `uv run ci check` passed (`3b9a6705cafb44a4a3232d36e3fb0d20`), including pyrefly and Ruff.
- **Passed:** TDM installed deployment-key and certification controls, 45 tests (`976fbbba198c4e2f96731d3af1840f20`), prepared-batch native computation, adoption and detached export (`118f4565f6524642950d0e2add0b3667`), and the real Docling provider spool-resume test (`5fc23c205c7f406599ba81df4c1c1a26`). Source-discovery and cursor controls passed in a [mixed receipt](docs/plans/test-domain-model-and-execution_2026-11-17.md#implementation-evidence).
- **Scoped:** Real two-region PM2 passed at N14 (`03f8d4609b994202886c65f991716e0f`). All three real E5 cases passed at N16 (`618981d23eba4b4588d79257c8597065`). N17's mixed result `c4b4bb09147a44efa2b1a86a097c4803` passed composition and companion reads. Its dossier, event and rich journeys remain open under the DDO coordinator. TDM-18 remains open.

## Next execution

- Resolve the native consumer prerequisites recorded by TDM, then reconcile the qualification union with `ci test review`. See the [TDM closeout](docs/plans/test-domain-model-and-execution_2026-11-17.md#tdm-18).
- Replay N18 on the owned stage. Verify its matching application and the dossier, event and rich native journeys before canonical development adoption.
- Run the full 518-page book demand through committed progress, interruption, same-demand resume and repeat. Use its current source, formal and sentence products for PE-S33. Complete the required native, provider, public, fault and repository-check union for DDO-12. Chandra OCR remains excluded.

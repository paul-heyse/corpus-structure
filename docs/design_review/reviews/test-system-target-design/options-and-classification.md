# Options and classification — supporting the test system target design

**Supporting document to the [design review of the test system target design](../design_review_test-system-target-design_2026-11-13.md),
2026-11-13.** Written by the same delegated reviewer.

**Role.** Two bounded aids for plan creation. Part A records what becomes of every option and
recorded idea of the superseded
[2026-11-12 efficiency opportunities](../test-architecture-and-efficiency/efficiency-opportunities.md).
Part B carries the per-family and per-module classification leads that a plan author needs to apply
the isolation classes, seeds, DDO support and cutover rule. This document carries no verdict, no
finding identities of its own and no disposition ledger: the principal review owns the judgment, the
finding identities, the rule impacts RC01–RC04 and the Deferred rows.

**Baseline and consumed context.** `main` `a5ea7c4dc`; test audit publication `28b4a53db`; the four
audit contributor reports and the four input reports prepared for this review. Paths follow the
principal review's convention. Source facts are **Interface-checked by source inspection,
2026-11-13**, where I read them; classifications attributed to a contributor are that contributor's
reading (AST heuristic, call listing, or full read, as marked) and are **planning leads**, not
verified dispositions. Every option is **Proposed**.

---

## Part A — What becomes of the 2026-11-12 options

| Old ID | Old opportunity | New disposition | Reason | Designed in |
|---|---|---|---|---|
| D1 | One head deployment per run, controller-owned cleanup | **Replaced** | A content-keyed deployment gives one build per run as a special case, removes the focused-run floor, and needs no controller hooks or run-end owner | Principal §4.1, DTA-024 |
| D2 | Rollback-only refusal families share one committed scenario | **Retained** as the rollback class on a seed family clone | Unchanged in substance; now one of four named classes, gated on DTA-001's contract | §4.2, DTA-025 |
| D3 | Pure SQL-function checks on a read-only rung | **Retained, refined** as the read class | Permission refusals and in-transaction DDL go to the rollback class instead: `25006` would mask `42501`, and DDL is refused under `READ ONLY` | §4.2 |
| D4 | One maintenance session per clone acquisition | **Withdrawn** | The other maintenance connections measure about 0.02 s per clone (contributor, `e332a3ef…`); only observation noise would go | §11 |
| D5 | Sealed scenario seeds cloned per committing consumer | **Retained, generalized** | One seed operation for every recipe meeting the seed premises, including the DDO kernels | §4.1, F03, DTA-031 |
| D6 | Serving-seed clone validation without duplicates | **Folded in** | The serving seed migrates to the common seed operation; per-clone revalidation reduces to what seal and lease do not guarantee | §4.1 |
| D7 | Seeds shared across a run's workers | **Candidate**, unchanged | Revisit when full-run receipts show per-worker seed builds as a material share of setup | §4.1 |
| D8 | One sweep per run | **Not pursued** | The sweep measured cheap (contributor); F04's skip-and-report matters more than its frequency | §6.3 |
| D9 | Head reused across runs under a content key | **Selected** | The only option that removes the focused-run floor; key computed over the chain and its import closure; qualification builds run-private heads | §4.1, RC01 |
| G1 | Fixture-closure groups for expensive module/session preparation | **Retained**, keyed by preparation value | Measured per-worker repetition (F02) | §4.7 |
| G3 | Dispatch structurally long tests first | **Candidate**, low | Removes only idle tail in full runs | — |
| S1 | Staged builders; consumers stop at the stage they read | **Retained** | Also defines the seed's claim boundary and the cutover's re-pointing unit | §4.3 |
| S2 | Memoized input assembly by recipe value | **Retained** | Rides on recipe values | §4.1 |
| S3 | Load the controlled PDF builder once per process | **Candidate**, low | Small per call | — |
| W1 | Workers sized to explicit node-id selections | **Retained, refined** | One node id runs with `-n 0`, which also removes xdist's gateway shutdown | §4.7, F05, RC02 |
| W2 | Lazy CLI import in the package conftest | **Candidate**, low | Removes an import from every worker of a non-CLI focused run | §4.7 |
| W3 | Screen managed arguments without a second interpreter | **Candidate**, low | The ADR-0069 custody premise is still unestablished | §4.7 |
| P1 | Independent cold-process children run concurrently | **Candidate**, low | Premise: no shared writable files between children | — |
| T1 | CPU lifecycle controls use short grace and pin the value | **Retained**, seam corrected | The factory seam is the module-global `ProcessPoolExecutor`; no production change | §6.4, DTA-026 |
| C1 | Defer collection-time file loads | **Candidate**, low | Small | — |
| — | Hypothesis: no change | **Retained** | DTA-032, not the example count, is the lever for the dominant property | §4.7 |

**Recorded, not developed in 2026-11-12, reconsidered:**

| Idea | Now |
|---|---|
| Asynchronous or deferred clone drops | Still not developed. Concurrent drop checkpoints may merge, but deferral holds disk and the direction of the effect is not established; fewer clones (read and rollback classes) is the safe lever |
| Non-durable cluster settings | Unchanged: cluster-wide, an operator decision outside test scope |
| `FILE_COPY` with `file_copy_method = clone` | Unchanged: two forced checkpoints per creation; ext4 has no reflinks |
| Fewer Hypothesis examples | Unchanged: rejected; focused and qualification runs should explore the same derandomized examples |
| Subtests in place of parametrized refusal cases | Unchanged: rejected; merges case identities |
| In-process substitutes for installed `ci` or nested pytest | Unchanged: rejected; replaces the boundary the claim names |
| Disabling plugin autoload | Unchanged: rejected |
| One shared source for the structural-replay texts | Unchanged: rejected; the scenarios genuinely differ |
| A disk cache of prepared releases | Rejected for now: its key must include the whole product implementation, so it would rarely hit during implementation; the archive reader is noted as a candidate route for seed consumers that only read |
| Coordinating math and CPU pools with xdist's worker count | Unchanged: a real DP-20 concern needing measurement |
| Fewer workers for full runs | Unchanged: direction not established structurally |
| Shipping page content to the coverage worker | Unchanged: changes the reading path the control exercises |
| Reusing a receipt's selection for retry | Unchanged: unsafe after source edits |
| The legacy `python/corpus-structure/alembic/` chain | Unchanged: outside test scope |

---

## Part B — Classification leads for planning

### B.1 Isolation classes and seeds by family

"Class" is the class the family's claim needs by the principal review's §4.2; "Seed" names the recipe
seed it would clone. Basis: **R** read by me at the cited lines, **C** contributor full read, **H**
contributor AST heuristic plus call listing. A plan confirms each row against the membership
criterion in §6.1 of the principal review before moving the family.

| Family or module | Cases | Today | Class | Seed | Basis |
|---|---|---|---|---|---|
| `semantic/test_private_records.py:131–176` forged custody | 12 | `private_source` per case | rollback | default `private_source`, pre-claim stage | 2026-11-12 review R; C |
| `semantic/test_runtime_bindings_native.py:100–148` altered bindings | 8 | `prepare_operation_scenario` per case | rollback | operation scenario | 2026-11-12 review R |
| `semantic/test_local_semantic_admission_native.py:505–660` forged judged rows | 10 | `judged_source` per case | rollback once `judged_source`'s provider patches are declared in its recipe; else commit from a seed | judged source (several variants) | C |
| `semantic/test_local_admission_native.py` witness refusals | 7 | `private_source` + per-case `local_cut` | rollback; `local_cut` moves into the seed | private source + local cut | 2026-11-12 review R |
| `semantic/test_contextual_enrichment_native.py:83–157` | 13 | `private_source` + per-case `curated_case` | rollback; `curated_case` into the seed | contextual private source | 2026-11-12 review R; H |
| `semantic/test_arrow_publication.py:445–495` | 6 | inference fixture | rollback | inference fixture | 2026-11-12 review R |
| `semantic/test_identity_exclusions_native.py:21–52` tampering | 18 | `exclusion_result` in body | rollback, `SERIALIZABLE` per case | two `exclusion_result` recipes | C |
| `semantic/test_imported_declaration_membership.py:231–291` | 6 (5 refuse) | builder in body | rollback for refusals; commit for "valid" | imported-declaration case | H |
| `semantic/test_occurrence_context.py:143–199` | 8 | builder in body | rollback | occurrence-context source | H |
| `semantic/test_domain_operations.py:867–992` | 6 (5 refuse) | `build_domain_case` in body | rollback for refusals; commit for "valid" | membership-lineage domain case | H |
| `semantic/test_witnessed_applicability_native.py:172–197` | 2+ | commits run, task and claim per case | commit from seed unless pre-steps move inside the case transaction | completed relationship case | 2026-11-12 review R |
| `semantic/test_structural_native_replay.py:147–217` | 14 | distinct text per case | commit; per-case recipe parameter | none (scenarios differ) | 2026-11-12 review R |
| `semantic/test_local_semantic_admission.py:121–147` | 17 | clone per case | read | none | 2026-11-12 review R |
| `semantic/test_contextual_workflow_native.py:29–87,104–135` | 10 | clone per case | read | none | 2026-11-12 review R |
| Permission refusals on an empty clone (`test_identity_exclusions_native.py:240`, `test_domain_operations.py:246,254`, `test_occurrence_context.py:315`) | 4 | fresh clone | rollback with principal connections; pin `42501` | none | C |
| `tests/db/test_lifetime_native.py:162–164` | 1 | commits DDL to the shared clone | commit | none | R |
| `semantic/test_release_compatibility.py:91–123` | 1 | chain replay for a second database | commit: two clones of the head | none | R |
| `semantic/test_domain_operations.py` (other 24 tests) | 35 | `build_domain_case` in body, 21 argument sets | commit; seed only shared prefixes | release-and-views stage keyed by schema options | H; dominant stage unknown |
| `semantic/test_runtime_entrypoints.py` stdio journeys | 13 | resubmission case per mode | commit | default and composed resubmission | H |
| `evaluate/test_record_policy_native.py:15–47` | 2 | full `private_source` | commit or rollback on a persisted-release stage | release-only stage | 2026-11-12 review R |

### B.2 DDO modules: what each needs in the target

Basis: the DDO support input report (AST pass and partial reads at `28b4a53db`), checked against the
importer list at `a5ea7c4dc`.

| Module | Today | Target class | Target support |
|---|---|---|---|
| `semantic/test_data_operation_storage.py` | Defines `_declaration` and five variants, `kernel`, `attach`, `claim`, `retain`, `publish`, `cancel_demand`; about 43 tests | commit from the storage kernel seed; `:738` and `:2150` read | Everything it defines moves to DDO support; lease expiry through `expire_lease` except one real-clock control |
| `semantic/test_data_operation_service.py` | Imports `ddo_kernel_engine`, `kernel`; one double below the wire | commit from storage seed; pure for the routing test | `WireCheckedStorage` |
| `semantic/test_data_operation_population_native.py` | Own kernel; imports storage helpers | commit from population seed | Population `KernelRecipe` |
| `semantic/test_data_operation_consumer_native.py` | Four releases; admission written out at `:365–368` | commit from four consumer seeds | Four `KernelRecipe` values |
| `orchestrate/test_data_operation_execution.py` | Relative import from storage; uuid module name | commit from execution seed | Fixed module name; canonical import |
| `orchestrate/test_data_operation_claim_source_native.py` | Relative import from storage (new since the audit) | commit from a kernel seed | Canonical import |
| `semantic/test_data_operation_original_native.py` | `private_source` rows plus storage `_declaration` | commit from two original-profile seeds | Pre-claim private-source stage plus DDO profile |
| `semantic/test_data_operation_binding_native.py` | `binding_native_connection` installs functions in a rolled-back transaction on a clone | rollback | Binding case table; connection fixture in support |
| `semantic/test_data_operation_population_selection.py`, `…_parameters.py` | Import the binding connection and helpers | rollback | From support |
| `semantic/test_data_operation_source_native.py` | Source-builder connection, rolled back | rollback | From support |
| `semantic/test_data_operation_identity_native.py` | Literal vectors on a clone, rolled back | read | Contextual identity vectors added (DTA-033) |
| `semantic/test_data_operation_subjects.py` | Pure; imports the native storage module for one dictionary | pure | Declaration builder from support |
| `semantic/test_data_operation_bindings.py`, `…_consumer_bindings.py` | Compiled bindings on SQLite | rollback on PostgreSQL | Binding case table (DTA-034) |
| `semantic/test_data_operation_demands.py` | Double below the wire | pure | `WireCheckedStorage` |
| `orchestrate/test_data_operation_batch_activity.py` | Lazy relative imports of CPU and ports helpers | pure | Canonical imports from support |
| Compilation, identity, wire, ports, CPU, member, preparation, runtime, artifacts, source sets, consumers, execution evidence, python operation sources, the four product modules, `tests/test_cli_demands.py` | Pure | pure | Declaration and subject-context builders from support where they share them |

The six base-declaration families (storage `_declaration`, compilation `contract()`, demands
`operation()`, bindings `declaration()`, production `claim_source_item…`, parameters' own) differ in
subject kind, coverage, outcomes, ownership and boundary. For native tests those differences reach the
kernel; for compile-only tests whether the vocabulary is closed was not checked. Support merges them
where they model the same declaration and keeps intentional differences as explicit recipe fields.

### B.3 Cutover leads (DTA-035)

Per-test dispositions below are a contributor's, mostly by token match; the rows marked **read** were
read by that contributor. They are inputs for each retiring DDO package, not decisions.

| File | Mechanism-only (delete with named commit) | Mixed (re-express on the surviving surface) | Surviving-surface counterpart cited |
|---|---|---|---|
| `semantic/test_operations.py` | Reuse status and `reused_task_id` (`:415`, read), nine forged-reuse cases (`:562`, read), freshness as invocation salt (part of `:827`) | Terminal fence, exact replay, sealed cut (`:30`); wrong attempt (`:126`); cancel drains claims (`:897`); stale lease (`:950`) | Storage `:393`, `:460`, `:814`, `:840`, `:1144`, `:1330`, `:1453` |
| `semantic/test_runtime_bindings_native.py` | Reuse part of `:180` (read) | Runtime-change fence part of `:180`; altered bindings (`:113`); immutability; changed runtime cannot claim | Storage `:638`, `:1692`, `:2016`; binding native `:471` |
| `semantic/test_source_jit_native.py` | `ops.task_dependency` assertions (`:342`, `:432`, `:636`) | Stale completion refused after reclaim | `population_native:446` (partial); none for source-view batching |
| `orchestrate/test_characterization_recovery.py` | Anchor, run-option link, freshness seed (`:45`, `:89`, `:128`, `:172`, `:185`; read) | Capacity-policy change, receipt failure, provider identity | None found |
| `orchestrate/test_source_progress.py` | Reused-count assertion (`:151`) | About eight readiness tests through `projection()` (`:71`) | None found |
| `orchestrate/test_ready_coordination.py` | Stage-cap parameter only | Claim and byte-budget behavior | `orchestrate/test_data_operation_batch_activity.py` (partial) |
| `semantic/test_characterization_native.py` | Mechanism inputs at `:873`, `:1414`, `:1904` | Publication, sealing, size limits (20 of 22 need re-fixturing) | None |
| `semantic/test_domain_operations.py` | None | One cyclic-reference expectation (`:498`) tied to the classification DDO-08 repairs | — |
| `semantic/test_retained_source_reuse_native.py` | All seven by `reused_task_id` | Re-express as selection of exact pins and refusal of mismatches | DDO selection in population and consumer native tests |
| Further files with fixture use (`test_source_views.py`, `test_coverage_comparison.py`, `test_retained_source_budgets.py`, `evaluate/test_operation_assessment.py`, `methods/test_m1_readings.py`, `acceptance/test_regeneration.py`, `orchestrate/test_execution_preparation.py`, `core/test_execution_policy.py`) | Field-only uses in several | Mostly keep, minus the retired field | Per file at the owning package |

Return to the [principal review](../design_review_test-system-target-design_2026-11-13.md) for the
judgment, the finding identities, the rule impacts and the dispositions.

# Adoption and validation of the PostgreSQL leverage series

**Proposed execution target, 2026-11-01.** [Coordinator](../postgresql-capability-leverage_2026-11-01.md) owns PG-00/11/12 and the combined completion claim. This owner explains their evidence and transitions. None of the following runtime checks was run during plan authoring.

## PG-00 — Deliberate current baseline and dependency move

At execution start record actual source, relevant dirty changes, database realization and supported consumer contracts. Treat concurrent PDF state as external context, not an inherited queue. Check actual files and receipts rather than relying on old planned labels. Required baseline publication/reader capabilities that are unavailable stay explicitly blocked at their owner; independent PostgreSQL packages can proceed.

Update declared PostgreSQL integration dependencies to latest stable, exactly pinned, with deliberate lockfile-family changes and no wholesale re-resolution. The operator excluded **alembic-utils**; do not add it directly or indirectly as the lifecycle solution. No version-discovery campaign is a prerequisite to design; resolve exact available releases when making the dependency change. Interpreter/toolchain rules remain those of the repository.

Exercise the actual Identity/default comparison case before removing `semantic/alembic_defaults.py`. An unrelated upstream identity ALTER fix does not settle it. Run affected pool-return, SQL construction/admission, native comparison, COPY fidelity and ADBC capture regressions, plus `just ready` after the environment change. Keep original failed attempts; passing the focused dependency union does not qualify the whole new series.

## PG-11 — Adopt only this series' changes

For each changed contract migrate its actual producers, validators, storage/admission products and consumers together. This includes failure/refusal reports, typed projection consumers, native forward authoring and public export/description surfaces. Retire replaced generic mechanics when all affected callers use the selected route; retain only paths with a concrete consumer or historical evidence purpose. Do not preserve misleading compatibility aliases by default.

Schedule only the new series' own forward model/native/schema/data changes. Choose source-shaped transition mechanics: native set operation for resident rows, compatible batch replay for Arrow/Parquet, or existing streamed-envelope parsing where that representation is truly an input. Do not implement the former PDF plan's deployment/adoption or reproduce its unfinished packages as prerequisites owned here.

Target selection can break interfaces, representations and compatibility as needed. Explain changed meaning, activation and affected consumers. Existing decisions remain authority until the corresponding successor/owner update, if required, is actually accepted and made; approval of a generic breaking-change envelope does not silently rewrite semantic authority. Historical receipts are not updated or erased. Ordinary routine version moves do not need ADRs.

For own data migration, compare fresh creation and populated retained-fixture transition with independent expected values/privileges. Separate “migration ran,” “native admission passed,” “consumer uses new contract” and “operational target selected.” Do not use `stamp` or head revision alone as a schema/data verification. Explicit restart/refusal is preferable to hidden replay under changed identity. Any exceptional concurrent index/autocommit work is outside a claimed atomic document transaction.

## PG-12 — Final-source qualification

During implementation use targeted compile/type/functional checks and real provider cases for the changed capability. Run substantial typing/lint diagnostics at coherent endpoints, not every edit. Root final maintenance precedes qualification; later source/harness/configuration changes require affected evidence reassessment.

After all functional scope is implemented, run the repository's final `just test-all` and applicable `just hygiene` routes for the same source/context, or account explicitly for the required union through its native receipts. Preserve actual PostgreSQL/ADBC/provider outcomes, independent expected values and unavailable obligations. Tests with mocked providers do not qualify live interoperability. Rust results, if applicable, record `rustc --version`; zero listed Rust tests establish no Rust coverage.

Required scope includes:

| Journey | Independent result and failure distinction |
|---|---|
| Publication and resource ownership | Native cause plus operation phase yields correct retry/refusal/receipt action; cancellation settles the actual borrower; timeout/pressure/closure differ |
| Prepared model and transfer | Different bindings reuse structure without stale results; changed profile invalidates; exact null/numeric/layout and encoder restart cases |
| Native extension lifecycle | Actual owned candidate objects, no-change diff, changed property, caller rollback, unowned preservation and intentional wrong-native-contract refusal |
| Companion analytical consumer | Authorized PostgreSQL batches → Parquet → DuckDB inventory/comparison with correct pin/rows/types and no staging leakage |
| Database description | Actual CLI scoped metadata/query shape with exact versus estimate/unknown labels and no query effects |
| Selected-source consumer | One intact section streamed with necessary context, original addresses and explicit omissions into actual scientific/extraction input preparation |
| Own adoption | All changed callers migrated, new realization verified, replaced mechanisms removed or retained for named consumers |

Required shared guarantees include ordering/multiplicity, scoped evidence reachability, source/selection pins, role/grant boundaries, raw-versus-logical identity, truthful partial/unknown outcomes and rollback/recovery. Use independent analytic fixtures/native catalog observations where producer/consumer share the same model/compiler. Production validators can test their consumers but cannot generate both actual and expected semantic results for themselves.

Full PDF recognition, whole-book publication, existing grading, remote attachment and other plans' unrealized acceptance are not automatically required. A newly changed external tool contract does require its own actual attachment/use journey when that is the supported delivery surface; choose the surface and provider obligation explicitly rather than relabel a component test as assembled acceptance.

## Benefit claims and ongoing operation

Structural improvements can be judged from removed repeated definitions/conversions, clearer operation ownership and actual consumer use. No speedup, capacity or hard deadline is claimed without measurement. If a package makes a quantitative promise, record a representative baseline, command, input and conditions before claiming Measured. No benchmark campaign, cost model or new telemetry framework follows merely from FP-07.

Native operational settings/metrics must answer a real operator question. The coordinator defers rotation/wakeups/idle tuning until their trigger; those deferrals do not weaken demanded cancellation, useful failure reporting or delivered description capability. Diagnostics should not copy full payloads or become a second workflow authority.

## Plan-authoring verification

**Authoring date:** 2026-11-01. **Implemented product scope:** none by this series. **not_run:** runtime probes, dependency updates, database migration, provider/consumer journeys and product qualification. Source inspection and library documentation inform Proposed design only. Scoped links, package references and maintenance/publication results are recorded at final authoring closeout below. Other series and their progress remain unchanged.


**Authoring checks (2026-11-01):** **passed:** scoped Python use of existing `scripts/docs.py::rewrite_links` for all six new documents and explicit source/package/investigation anchor checks (O01–15, PG-00–12, PG-I01–03). Focused independent reading found and corrected a family-set mismatch and stale companion wording; no new review workflow was initiated. **failed:** `just docs-check` stops at unrelated ADR-0043 missing its DESIGN §B4 Decision link; receipt `build/postgresql-plan-docs-check.log`. This does not establish full publication. Source refresh through `2e24f8c0` inspected newly added modeled publication contracts; no runtime result is inherited from that concurrent commit. The root uses ADR-only turn-end maintenance to avoid formatting active concurrent product validation: `just --set turn_end_steps adr-index turn-end`. Product formatting, runtime checks and implementation remain outside this authoring scope.

**passed (2026-11-01):** the ADR-only turn-end command above completed; receipt `build/postgresql-plan-turn-end.log`. Full formatter execution was deliberately **not_run** to preserve active concurrent validation.

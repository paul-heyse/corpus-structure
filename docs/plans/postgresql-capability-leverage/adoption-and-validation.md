# Adoption and validation of the PostgreSQL leverage series

**Implemented and targeted Tested,2026-11-01.** [Coordinator](../postgresql-capability-leverage_2026-11-01.md) owns PG-00/11/12 and the combined completion claim. This owner explains their evidence and transitions. None of the following runtime checks was run during plan authoring.

## PG-00 — Deliberate current baseline and dependency move

At execution start record actual source, relevant dirty changes, database realization and supported consumer contracts. Treat concurrent PDF state as external context, not an inherited queue. Check actual files and receipts rather than relying on old planned labels. Required baseline publication/reader capabilities that are unavailable stay explicitly blocked at their owner; independent PostgreSQL packages can proceed.

Update declared PostgreSQL integration dependencies to latest stable, exactly pinned, with deliberate lockfile-family changes and no wholesale re-resolution. The operator excluded **alembic-utils**; do not add it directly or indirectly as the lifecycle solution. No version-discovery campaign is a prerequisite to design; resolve exact available releases when making the dependency change. Interpreter/toolchain rules remain those of the repository.

Exercise the actual Identity/default comparison case before removing `semantic/alembic_defaults.py`. An unrelated upstream identity ALTER fix does not settle it. Run affected pool-return, SQL construction/admission, native comparison, COPY fidelity and ADBC capture regressions, plus `just ready` after the environment change. Keep original failed attempts; passing the focused dependency union does not qualify the whole new series.

## PG-11 — Adopt only this series' changes

For each changed contract migrate its actual producers, validators, storage/admission products and consumers together. This includes failure/refusal reports, typed projection consumers, native forward authoring and public export/description surfaces. Retire replaced generic mechanics when all affected callers use the selected route; retain only paths with a concrete consumer or historical evidence purpose. Do not preserve misleading compatibility aliases by default.

Schedule only the new series' own forward model/native/schema/data changes. Choose source-shaped transition mechanics: native set operation for resident rows, compatible batch replay for Arrow/Parquet, or existing streamed-envelope parsing where that representation is truly an input. Do not implement the former PDF plan's deployment/adoption or reproduce its unfinished packages as prerequisites owned here.

Target selection can break interfaces, representations and compatibility as needed. Explain changed meaning, activation and affected consumers. Existing decisions remain authority until the corresponding successor/owner update, if required, is actually accepted and made; approval of a generic breaking-change envelope does not silently rewrite semantic authority. Historical receipts are not updated or erased. Ordinary routine version moves do not need ADRs.

Design-phase execution constraint (operator, 2026-11-01): all data can be regenerated; prioritize the target without historical support. This is temporary execution guidance, not a permanent product compatibility policy. Validate fresh current database creation and regenerated releases/data with independent expected values/privileges. Historical execution reads and retained-data upgrades are not required. Refuse obsolete execution products with an explicit regeneration requirement rather than introducing compatibility readers. Preserve frozen revisions and evidence as inert history; a fresh bootstrap may execute the existing revision chain. Separate “migration ran,” “native admission passed,” “consumer uses new contract” and “operational target selected.” Do not use `stamp` or head revision alone as a schema/data verification. Explicit restart/refusal is preferable to hidden replay under changed identity. Any exceptional concurrent index/autocommit work is outside a claimed atomic document transaction.

## PG-12 — Final-source qualification

**Execution scope clarification (operator,2026-11-01):** the concurrent PDF baseline was not
fully passing when its implementation paused for review. Completion of this series requires
its complete functional scope and targeted tests of its changed responsibilities and actual
consumers. A wholly green repository suite is not a migration prerequisite. Do not repair
unrelated existing PDF, historical-reader, corpus-fixture or host-provisioning tests to obtain
that result. Preserve the interrupted broad run and its failures without acceptance credit;
qualify the selected PostgreSQL scope with an explicitly identified final-source native union.
The final receipt/selection is recorded in the coordinator, not in a second execution register.


During implementation use targeted compile/type/functional checks and real provider cases for the changed capability. Run substantial typing/lint diagnostics at coherent endpoints, not every edit. Root final maintenance precedes qualification; later source/harness/configuration changes require affected evidence reassessment.

After all functional scope is implemented, account for the required targeted union through its native receipts and relevant hygiene checks for the same source/context. `just test-all` and `just hygiene` remain available broad routes, but a full-repository pass is not required by the clarified execution scope. Preserve actual PostgreSQL/ADBC/provider outcomes, independent expected values and unavailable obligations. Tests with mocked providers do not qualify live interoperability. Rust results, if applicable, record `rustc --version`; zero listed Rust tests establish no Rust coverage.

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

**Expanded authoring baseline, 2026-11-01:** `cfa009b2` plus relevant dirty PostgreSQL references and PDF sources. The initial integrated review remains `09d3125e1570df7c94ca357962107155cfdb939b`. All PG packages remain planned. Source/installed-interface inspection, Context7 and primary-source reading support Proposed design only. No dependency manifest, product code, migration, existing plan series or diagnostic audit document was changed by this expansion.

A focused independent consistency reading identified and corrected three design gaps: diagnostics now describe the owning invocation's process-local Store; v1 analytical endpoints retain the current required resolved occurrence identity; query description accepts parameter-free admitted SELECTs because current admission does not accept parameter nodes. Offline formula preparation explicitly consumes an already admitted retained interpretation context. These are authoring corrections, not implementation or a formal audit conclusion.

**passed:** scoped inline Python invoking existing `scripts/docs.py::rewrite_links` and explicit local-anchor checks resolved six documents/68 local references; package/opportunity checks retain PG-00–12, PG-I01–03 and O01–15. **passed:** `git diff --check -- docs/plans/postgresql-capability-leverage_2026-11-01.md docs/plans/postgresql-capability-leverage STATUS.md`.

**failed:** `just docs-check` remains blocked by unrelated `DESIGN.md §B4` missing the Decision link naming ADR-0043; receipt `build/postgresql-plan-expansion-docs-check.log`. This does not establish full publication and is not repaired in this authoring scope. **not_run:** product tests, probes, dependency updates, database deployment, live provider/consumer journeys and product qualification, because the authorized deliverable is the plan expansion.

Root maintenance uses `just --set turn_end_steps adr-index turn-end` to preserve active concurrent PDF product validation; the full formatter is deliberately not_run. **passed (2026-11-01):** the ADR-only maintenance command completed; receipt `build/postgresql-plan-expansion-turn-end.log`. The handoff points to this series; implementation starts with PG-00 and independently ready contract work.

## Executable adoption route — PG-00/11

**Proposed, 2026-11-01.** Execute the dependency move before exercising new public extension interfaces. Change only the seven PostgreSQL integration distributions and the dependency closure required by those changes. Keep exact manifest pins and inspect the lock diff. No blanket environment upgrade is selected. Treat the documented capabilities as available design inputs; exact latest-stable releases are resolved when executing PG-00. Relevant library source references belong beside each mechanism in the supporting plans, not in a second version inventory.

Capture the failing Identity/callable-default case independently of the current `alembic_defaults.py` adapter. Run it once through native upstream comparison after the family move, then remove the adapter/registration only if that exact case succeeds. If it still fails, preserve a narrowly scoped adapter with the reproduced case and its removal condition; a successful unrelated autogenerate example is insufficient. Use the public Plugin dispatch where residual customization is necessary. This is a workaround decision within PG-00, not permission to preserve private hooks indefinitely.

### Available capabilities and coordinated transitions

| Intermediate state | Usable capability | Adoption obligation before proceeding |
|---|---|---|
| Latest dependencies and PG-02 integrated | Existing publication/read operations have truthful failure context | Store, publication and refusal renderers all consume the new meanings; no mixed flat retry classifier |
| PG-03/04 integrated | Existing Arrow writers share prepared profiles and fresh encoders | Migrate ordinary Arrow publication and private PDF staging together with their independent admission checks; row COPY retains its real consumer |
| PG-05 integrated | Existing operation owners settle their own borrowers and renewal | All active long-operation/iterator owners use cancellation scopes; diagnostics retain unknown fields |
| PG-01 native extension demonstrated | PG-08 has a concrete operation/payload/renderer contract | Representative family covers properties, privileges, frozen current-operation replay and caller rollback before migrating further families |
| PG-06 complete | Detached companion Parquet export and DuckDB comparison | Public service and CLI use authorized family projections and one manifest meaning |
| PG-07 complete | Scoped physical/query description | CLI and shared service render the same observation/estimate contract; no guessed semantic schema |
| PG-10 complete | Selected-source package consumed incrementally | Source export request, native query and scientific input-preparation reader share selection/context meaning |
| PG-08/09/11 complete | Current forward object authoring and diagnostics use the selected route | Retire replaced current mechanics; frozen migrations remain reproducible |

The first four states enable subsequent work but are not a deployment train. PG-07 can integrate independently of the object-lifecycle extension. PG-06 needs actual authorized projections, but may obtain them through the existing forward authoring route before PG-08 migrates that machinery. PG-10 needs the working cancellation/reader lifetime and selected-context query; it does not wait for DuckDB comparison. Agreeing an interface enables dependent design, while a working admitted producer is required for dependent live acceptance.

### Consumer migration scope

The representative examples in supporting plans establish mechanisms; PG-11 must also account for the whole current caller set. Use symbol searches at execution because the PDF baseline is still moving. Follow the old error classifier/refusal wrapper, encoder constructors, projection compilation, active native inventory generation, native-source request dispatch and scoped source input preparation into their actual entry points. Record the migrated scope in the existing package explanation, rather than adding a permanent caller register.

For each public change update the executable request/result declaration and the application/CLI consumer together. New error meanings do not need old misleading aliases. New export formats use explicit format/projection versions; do not reinterpret old native-complete bytes or manifests under new defaults. Existing native JSON export and small Core reads remain because they serve different consumers. Retain original SQL and frozen historical operation inputs for reproducing old revisions; remove only replaced current generator paths once no current caller remains.

When PG-08 changes native products, make a forward revision from the current execution baseline; do not assume today's untracked0065 will be the immediately preceding revision. Fresh database construction must lead to independently admitted current objects; no populated historical transition is an acceptance obligation. Keep authoring discovery scope, runtime role and migration role explicit. A changed grant/security property blocks consumer activation even if body SQL and revision head match. Candidate rendering is review input; admission is a separate observation of the deployed target.

Select ordinary transactional DDL and server-side transformations for resident relational data. If an actual change needs `postgresql_using`, express the complete conversion and independent expected retained values in that revision. Use `NOT VALID`/`VALIDATE CONSTRAINT` only when the selected transition needs separate existing-row validation. `autocommit_block` commits earlier work, so concurrent index work needs its own restart/refusal boundary and invalid-index handling; do not include it in an atomic publication claim. These mechanisms are conditional tools for this series' actual changes, not additional online-migration requirements. See [Alembic operation references](https://alembic.sqlalchemy.org/en/latest/ops.html) and [autocommit transaction semantics](https://alembic.sqlalchemy.org/en/latest/api/runtime.html#alembic.runtime.migration.MigrationContext.autocommit_block).

For export adoption, write under an operation-owned temporary destination, finalize only after all required files/records close and pass their bound checks, then expose the manifest/completion result. A partial family file or absent JSONL completion record remains incomplete. Retry creates a fresh owned output and preserves the original failed attempt's diagnostics. Cleanup never removes an unrelated preexisting destination. Long local DuckDB work begins after database snapshots/readers have been released.

## Acceptance design by package — PG-12

The following are required verification meanings, not commands already run. Add cases to existing scope-appropriate test modules rather than creating a parallel qualification harness. Reuse production validators at consumer boundaries; manually specify independent expected identity, values, memberships and catalog facts for tests of those validators.

| Packages | Revealing fixture/scenario | Independent assertion and evidence boundary |
|---|---|---|
| PG-00 | Identity/callable default, normal table diff, regular pool/Core borrow-return after upgrade | Actual upstream path preserves the intended default semantics and same physical inventory; matching lock/manifest family and `just ready` establish the changed environment only |
| PG-02 | Full pool, checkout deadline, closed Store; successful write with controlled lost commit acknowledgement | No pre-checkout receipt lookup; original durable receipt resolves uncertain acknowledgement; wrong duplicate bytes refuse |
| PG-03 | Two pins share one stable query shape, then a changed model/profile; static wrong-column access | Rows follow each binding, changed dependency invalidates affected preparation, typing rejects wrong static access; object identity of a cache alone is insufficient |
| PG-04 | Same-typed columns swapped, changed schema metadata, JSON null versus SQL NULL, exact numeric values, encoding fails after prior batch | Correct rows or explicit refusal by declared profile; rollback has no partially public rows, retry uses fresh encoder; compare against manually declared values |
| PG-05 | Slow query/COPY, cancellation racing borrower return, renewal blocked on a lock, early reader abandonment | Actual running backend settles or is discarded; next borrower is clean; renewal owner exits without leaving a detached worker; unavailable diagnostics remain absent |
| PG-01/08 | Function overload with OUT/TABLE fields, changed security/search_path/grant, dependency replacement, injected failure inside caller transaction | Actual catalogs satisfy declared identity/protection, rollback preserves prior state, unowned object remains; no-change candidate is not by itself native admission |
| PG-09 | Unicode source, comments/statement slices, nested CTE name shadowing, mutation then fresh render | Independently expected original location and reference inventory; mutable AST/render state does not change another consumer's source-qualified facts |
| PG-06 | Two revisions of one source with repeated relation endpoints, partial coverage and exact lexical values | PostgreSQL → Parquet → DuckDB service/CLI produces independently expected inventory and comparable differences, preserving multiplicity and unknown outcomes |
| PG-07 | Literal relation containing wildcard characters, hidden/nonexistent relation, known column schema, unsupported/approximate estimates, rejected effectful query | Filter semantics and visible-scope report are truthful; query refusal precedes effects; estimates are never asserted equal to fixture row counts |
| PG-10 | Intact section with formula/table, outside endpoint, repeated occurrence, coarse/unknown geometry, failed sink | Original addresses and declared direct context survive incremental consumption; omissions are explicit, no successful completion on failed output |
| PG-11 | Fresh current realization, regenerated data and consumer activation | Native admission, migrated callers and obsolete-path retirement established separately; revision head/stamp is not accepted as current-contract verification |

### One assembled route per selected consumer

For PG-06 run the public export operation and CLI with a real read principal, the admitted PostgreSQL family functions, actual ADBC driver and Parquet files; run DuckDB over those detached files after closing database resources. Verify rejection of a hidden staging product, wrong pin/project, mismatched file binding and incomparable projection version. Count equality cannot replace endpoint/multiplicity checks.

For PG-07 exercise the installed PostgreSQL metadata implementation through the shared service and Typer command. A driver-manager method's existence does not prove that the PostgreSQL backend supports every mode. Compare known column observations independently, retain unsupported fields, and ensure JSON/human forms express the same meaning. Query schema preparation may parse/plan and acquire locks even when it does not return rows; it must remain within the admitted read boundary and owned read-only transaction.

For PG-10 run native ordered selection → streamed JSONL sink → incremental source/packet input preparation. Verify that the consumer can resolve the selected formula/table and required evidence without materializing the full native document. The test can use a small deliberately rich published fixture; it does not require restarting whole-book inference. If a supported MCP surface is changed, include actual attachment/use for that changed contract; the selected CLI/service delivery alone does not imply an MCP change.

After all functional packages and own adoption finish, run final-source `just turn-end`, the applicable targeted functional/provider/nonfunctional union and relevant hygiene checks (`just test-all`/`just hygiene` remain broad routes). Scope-controlled authoring checks below are not credit toward those product obligations. Retain failures/interruption and name missing external prerequisites. A performance measurement is required only for a numerical claim made by this implementation; the planned structural benefits remain Proposed until actual migrated behavior establishes them.

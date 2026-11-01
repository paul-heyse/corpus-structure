# Adoption and validation of the PostgreSQL leverage series

**Implemented and targeted Tested, 2026-11-01.** [Coordinator](../postgresql-capability-leverage_2026-11-01.md) owns PG-00/11/12 and the combined completion claim. This owner records the delivered adoption route and acceptance mapping. The final selected 319-case run passed; the coordinator owns its exact receipt, limitations and completion state. The original authoring-only checks do not substitute for that runtime evidence.

## PG-00 — Deliberate current baseline and dependency move

Execution started from `0878ba1b` in an isolated worktree and private PostgreSQL18 instance, with concurrent PDF scope kept separate. Main documentation changes through `72970e40` were integrated before the approved merge at `7b39e1b0`. The merged PG production/test snapshot matched qualified source `c5394eaa`; the temporary worktree and private server are now removed/stopped. Main database rebuilding/cutover remains with PDF RC12.

PG-00 moved exact pins to SQLAlchemy 2.1.6 and Alembic 1.20.1 in commit `3a0365a4`; selected Psycopg 3.3.6, psycopg-pool 3.3.3, pglast 8.7, pgpq 0.12.0 and ADBC PostgreSQL 1.13.0 were already current. The lockfile change was deliberate rather than a wholesale upgrade. Dependency checks and `just ready` passed. **alembic-utils** was excluded and was not added.

The actual Identity/callable-default case still reproduces the upstream comparison defect on Alembic 1.20.1. `semantic/alembic_defaults.py` therefore retains a narrow Plugin-based adapter, covered by `test_identity_callable_default_upstream_defect_and_retained_adapter` in `test_alembic_native.py`. Its removal condition remains success of that exact upstream case. The final selected union also covers ordinary physical comparison, pool/Core return, syntax/admission and both transfer paths.

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

## Implemented adoption and verification record

The authoring baseline was `cfa009b2`, informed by review `09d3125e1570df7c94ca357962107155cfdb939b`.
Those authoring-only checks are historical input, not the current implementation status. Final
acceptance is the passed319-case/32-file run at
`build/test-receipts/qualification/pg-series-final-c5394eaa`; its `invocation.json`, collection
events and JUnit XML retain the exact selected command, source and outcomes. Earlier scoped
and failed/interrupted receipts remain under `build/postgresql-capability-leverage/` or their
standard qualification paths, as mapped in the coordinator.

| Delivered boundary | Concrete implementation and consumer adoption |
|---|---|
| Native transition and current admission | [0066 revision](../../../python/corpus-structure/semantic_alembic/versions/0066_postgresql_capability_leverage.py) installs head `semantic_pg_20261101` after `semantic_0065`. Both frozen artifacts are SHA-256 checked before effects; operations dispatch through `NativeTransitionOp`/Alembic `Operations` on the caller Connection, followed by `admit_native`. No mutable generator is imported into the revision. |
| Ten managed functions | Frozen state includes the current record-shape guard, context-row selector, six-part companion pin guard, four typed family readers, selected-source event reader, execution descriptor and release guard. The descriptor/guard trust hashes in [execution_admission.py](../../../python/corpus-structure/src/corpus_structure/semantic/execution_admission.py) match the frozen witness. |
| Current release binding | [contracts.py](../../../python/corpus-structure/src/corpus_structure/semantic/contracts.py) uses execution compiler18 and declares the new model/implementation source inputs. Obsolete composed execution products require regeneration; no old-version analytical bridge was retained. The explicit current pure base-preparation API remains distinct from historical support. |
| Current caller migration | Store/publication/refusals/CLI share cause/phase/effect handling; PDF/COPY/read/renewal owners hold cancellation through settlement. Ordinary Arrow publication and PDF staging share profiles/fresh encoders. Analytics and companion capture use reusable typed preparation; source services/CLI share the delivered exports and descriptions. Supporting owners identify their actual symbols. |
| New consumer and correction coverage | Actual CLI/service tests exercise four-family PostgreSQL→ADBC→Parquet→DuckDB capture, bounded metadata/query description, and selected native events→offline scientific preparation. Side-qualified cross-product deltas, original nested/ancestor coverage and lossless recognition descriptors were corrected and independently reassessed. |
| Operational boundary | Fresh private head construction, regenerated-data publication, wrong protection/stale-state refusal, caller rollback, unowned preservation and recurring no-change/changed-property authoring passed. This proves the selected implementation; it does not claim deployment into the shared PDF database. |

Ruff, Pyrefly, dependency-family checks, readiness and root maintenance passed for the implemented
source. The broad exploratory suite was stopped normally under the operator's scope clarification;
its unrelated baseline failures remain outside this series. Global `docs-check` still reports
pre-existing/out-of-scope publication targets; scoped checks of all six plan documents resolved 89 local references and 20 Markdown anchors
with zero errors (`build/postgresql-capability-leverage/pg-plan-doc-closeout-links.json`). This
documentation-only reconciliation does not rerun or replace product qualification. No benchmark, whole-book/provider grading, Rust functional
coverage or shared-database cutover is asserted.

## Executable adoption route — PG-00/11

**Completed route, 2026-11-01.** The deliberate dependency move preceded the selected extension and consumer acceptance. Only SQLAlchemy/Alembic and their required lock closure changed; all selected packages remain exactly pinned. The following transition contracts describe the completed integration and remain useful for future changes, rather than forming an open deployment queue.

The reproduced Identity/callable-default defect and retained adapter decision are recorded above. Public Plugin dispatch is used for that residual customization. A successful unrelated autogenerate example remains insufficient grounds to remove the adapter.

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

All intermediate states above were reached. PG-07 integrated independently of native authoring; the final frozen head supplies the admitted companion/context/selected-source producers used by live acceptance. Cancellation and reader ownership were integrated into the actual consumers before final qualification.

### Consumer migration scope

PG-11 followed changed mechanisms into their maintained consumers: publication/refusal and CLI boundaries; PDF operation/reader/renewal owners; both Arrow writers; analytical preparation; native candidate/inventory authoring; source dispatch and offline formula preparation. These callers use the shared implementations described in the supporting documents. Future PDF payload consumers extend these owners under PDF-27/28 rather than requiring this completed series to absorb that unfinished scope.

For each public change update the executable request/result declaration and the application/CLI consumer together. New error meanings do not need old misleading aliases. New export formats use explicit format/projection versions; do not reinterpret old native-complete bytes or manifests under new defaults. Existing native JSON export and small Core reads remain because they serve different consumers. Retain original SQL and frozen historical operation inputs for reproducing old revisions; remove only replaced current generator paths once no current caller remains.

PG-08/11 added the committed forward revision `semantic_pg_20261101` after the inherited frozen `semantic_0065`; no old revision was rewritten. Fresh database construction must lead to independently admitted current objects; no populated historical transition is an acceptance obligation. Keep authoring discovery scope, runtime role and migration role explicit. A changed grant/security property blocks consumer activation even if body SQL and revision head match. Candidate rendering is review input; admission is a separate observation of the deployed target.

Select ordinary transactional DDL and server-side transformations for resident relational data. If an actual change needs `postgresql_using`, express the complete conversion and independent expected retained values in that revision. Use `NOT VALID`/`VALIDATE CONSTRAINT` only when the selected transition needs separate existing-row validation. `autocommit_block` commits earlier work, so concurrent index work needs its own restart/refusal boundary and invalid-index handling; do not include it in an atomic publication claim. These mechanisms are conditional tools for this series' actual changes, not additional online-migration requirements. See [Alembic operation references](https://alembic.sqlalchemy.org/en/latest/ops.html) and [autocommit transaction semantics](https://alembic.sqlalchemy.org/en/latest/api/runtime.html#alembic.runtime.migration.MigrationContext.autocommit_block).

For export adoption, write under an operation-owned temporary destination, finalize only after all required files/records close and pass their bound checks, then expose the manifest/completion result. A partial family file or absent JSONL completion record remains incomplete. Retry creates a fresh owned output and preserves the original failed attempt's diagnostics. Cleanup never removes an unrelated preexisting destination. Long local DuckDB work begins after database snapshots/readers have been released.

## Acceptance design by package — PG-12

The following are the acceptance meanings exercised by the final selected union. Concrete test groups are mapped below; the coordinator retains the single exact receipt/selection. Production validators enforce consumer boundaries, while independent expected identities, values, memberships and catalog facts challenge the validators themselves.

| Packages | Revealing fixture/scenario | Independent assertion and evidence boundary |
|---|---|---|
| PG-00 | Identity/callable default, normal table diff, regular pool/Core borrow-return after upgrade | Exact upstream defect is reproduced and the retained narrow adapter preserves default semantics; ordinary physical comparison and actual borrow-return are verified. Matching lock/manifest family and `just ready` establish the changed environment only |
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

### Concrete targeted test mapping

All paths below are relative to `python/corpus-structure/tests/` unless a root `tests/` path
is stated; bare filenames in a cell share its preceding directory. This is navigation into the recorded32-file selection, not a second completion ledger.

| Packages | Representative actual test modules |
|---|---|
| PG-00/01/08/11 | `semantic/test_alembic_native.py`, `test_native_closure.py`, `test_native_candidate_cli.py`, `test_postgresql_capability_adoption.py` |
| PG-02/05 | `db/test_outcomes.py`, `test_store.py`, `test_lifetime.py`, `test_lifetime_native.py`, `test_adbc_lifetime.py`; `semantic/test_cli_failures.py`, `test_pdf_lifetimes.py`, `test_read_contracts.py`; `orchestrate/test_pdf_cancellation_native.py`, `test_pdf_private_execution.py`, `test_pdf_published_execution.py`; root `tests/test_native_retained_reads.py` |
| PG-03/04 | `semantic/test_typed_realization.py`, `test_arrow_transfer.py`, `test_arrow_publication.py`, `test_pdf_staging.py`, `test_capture_policy.py`, `test_contracts.py`, `test_analysis_contracts.py` |
| PG-06 | `semantic/test_companion_export.py`, `test_companion_export_native.py` |
| PG-07 | `semantic/test_database_description.py` |
| PG-09 | `semantic/test_prepared_sql.py`, `test_native_inventory.py` and authored/native consumers in `test_native_closure.py` |
| PG-10 | `semantic/test_selected_source.py`, `test_selected_source_native.py`, `test_pdf_record_context.py`, `test_pdf_record_reader.py` |

### One assembled route per selected consumer

PG-06 acceptance ran the public export service and CLI with a real read principal, admitted PostgreSQL family functions, actual ADBC and Parquet, followed by detached DuckDB analysis after database resources closed. Verify rejection of a hidden staging product, wrong pin/project, mismatched file binding and incomparable projection version. Count equality cannot replace endpoint/multiplicity checks.

PG-07 acceptance exercised the installed PostgreSQL metadata implementation through the shared service and Typer command. A driver-manager method's existence does not prove that the PostgreSQL backend supports every mode. Compare known column observations independently, retain unsupported fields, and ensure JSON/human forms express the same meaning. Query schema preparation may parse/plan and acquire locks even when it does not return rows; it must remain within the admitted read boundary and owned read-only transaction.

PG-10 acceptance exercised native ordered selection → streamed JSONL sink → offline incremental formula input preparation. Verify that the consumer can resolve the selected formula/table and required evidence without materializing the full native document. The test can use a small deliberately rich published fixture; it does not require restarting whole-book inference. If a supported MCP surface is changed, include actual attachment/use for that changed contract; the selected CLI/service delivery alone does not imply an MCP change.

Final-source `just turn-end` preceded the319-case selected run and relevant hygiene checks; no PG product/test byte changed during integration/main merge. Subsequent PDF working-tree changes are separately owned and outside that receipt. The isolated scoped implementation and migrated consumers are Tested. Earlier failed/interrupted records remain preserved, and numerical speed/capacity/deadline benefits remain unmeasured. There is no remaining PG-12 test or shared-database deployment prerequisite hidden behind the old authoring-only record.

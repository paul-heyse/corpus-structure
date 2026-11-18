# Production seams and the capture-workspace binding: focused design advice

Baseline: frozen snapshot of `50827eb9f` (`snap3/`). Paths below are relative to
`snap3/python/corpus-structure/` unless they start with `scripts/` or `docs/`. Read-only. Nothing was
run. **[S]** means the source establishes it. **[I]** means it is inferred and the note says what
would confirm it. The review cites lines from an older commit. Its stream-protocol range `pdf_worker.py:80–131` is
now `:82–133`, and its `pdf_capture.py:92–98` is now `:86–104` (with `"directory"` at `:98`).

---

## Seam 1: the PDF stream protocol

**What source shows.**
- The child's stream branch (`src/corpus_structure/ingest/pdf_worker.py:82–133`) does these steps in order. It builds the payload family from
  `request.payload_schema`, builds `PdfStreamSpool(spool_root, on_page=ack, payload_family, recovery_pages)`, and runs
  `StreamingPdfProducer.run`. Then it writes record batches, acknowledges `completion.jsonl`, runs `certify_native_stream`, and builds the
  9‑field `PdfStreamReply`. **[S]**
- Writing the preparation entry is *not* in the child body. `StreamingPdfProducer.run`
  (`ingest/pdf_streaming.py:653–668`) writes `native-preparation.json` and checks it against the recovered
  pages' identity. It acknowledges the entry **before** conversion starts, and pages are acknowledged during conversion. **[S]**
- Recovery derives page identity from that entry (`ingest/pdf_build_spool.py:304–312`), so writing preparation first is a premise of resuming
  a spool. **[S]**
- In production the reply's `effective_options` and the preparation file are the *same bytes*:
  `converter.prepared_options_report` (`ingest/pdf_streaming.py:657–685`). The test helper writes different, invalid bytes to
  both (`tests/semantic/current_pdf_source_support.py:204–210, 274`). **[S]**

**Consequence for the seam's shape.** A function that takes "a converted result and a request" cannot own
the protocol, because preparation must be acknowledged before conversion begins. The smallest coherent owner is a
production function that takes **the request, a producer and the acknowledgement callback** and drives the whole sequence:
1. Prepare the payload family from `request.payload_schema` and build the spool from the request, including its recovery pages.
2. Call `producer.prepare()` to get the preparation report. Check it with `native_preparation_identity`, which refuses an invalid report. Write it
   atomically, check it against the recovered pages' identity, and acknowledge it.
3. Call `producer.convert(source, spool, page_range)`, which returns the document, status, errors and formula outcomes. The producer may acknowledge pages through the spool while it runs.
4. Write record batches, acknowledge the completion entry, certify, and return the reply. The reply's `effective_options` must be the preparation report from step 2, never a separate value.

Producer protocol: two methods, `prepare() -> bytes` and `convert(...)`, plus the recipe bytes. Its only
production implementation is `StreamingPdfProducer`, reshaped so that run() is split into these two halves. Two smaller fixes fit here:
`StreamingPdfResult` stops carrying a separate `effective_options`, and the record writer returns the completion entry's
reference itself. Today the child recomputes it with `_ref(record_root/"completion.jsonl")`, a filename convention shared between two
modules (`pdf_worker.py:112–116`, `ingest/pdf_streaming.py:529`).

**Where the process boundary sits.** Entirely outside the seam. The function knows nothing about IPC and receives `on_replay` as a callback.
- In the child, `on_replay` is the existing acknowledgement (send `PdfReplayReady`, wait for `True`). `_native_child` reduces to one
  call.
- Parent-side exchange checks remain in `PdfWorker._exchange` (`:221–254`): per-replay `verify()`, reply type, and teardown on a non-success result.
- To stop the test double from restating how the request is built, make `PdfWorker.stream` take a `PdfStreamRequest`.
  The only production caller (`orchestrate/pdf_streaming.py:493–505`) already holds every field. The double that replaces
  `PdfWorker.stream` then calls the seam function in the same process with the parent's `on_replay`, and builds no request of its own.

**What the controlled converter supplies.** The authored document (plus status, errors and formula outcomes, defaulting to success
and empty) and the recipe of the worker it stands in for. The preparation report comes from production:
- Run `PdfConverter._prepare()` once per worker, in-process, with the scripted Docling provider already used by
  `tests/orchestrate/test_pdf_streaming_integration.py:21–92`, and memoize the bytes. `test_resumed_pipeline…` at `:212–223` shows this
  runs without models.
- The report is therefore valid by construction and identical to the contract control's report, apart from fields that do not determine
  identity.
- A hand-written report is the fallback. It is legal, because the seam's identity check rejects a malformed one, but it restates the 8-key shape and drifts.
- The controlled converter acknowledges no pages, which is today's behaviour. Consumers that need page or raster custody use the real child.

**What the parent still verifies** (unchanged, and it runs for both routes because the double passes the parent's `retain_replay`):
- the family allowlist and confinement to the spool root (`orchestrate/pdf_streaming.py:411–444`, `pdf_build_spool.py:704–731`);
- `spool.complete` (`pdf_build_spool.py:741–788`): exactly one preparation and one completion entry, recipe digest equal to the premises, and every reply replay acknowledged;
- certification present and verified, of kind `native`, with the same `lowering_identity` (`orchestrate/pdf_streaming.py:529–548`);
- adoption-time `verify()` (`:450–455`);
- on recovery, `complete_reply` checks the completion header and `ready_pages` checks the preparation identity (`pdf_build_spool.py:347–406, 304–312`).

The in-process route skips only `_exchange`. That loop is covered by the real-child tests.

**Rejected alternatives.**
- A function for the post-conversion half only. It leaves preparation with the double, which recreates today's defect.
- Running every consumer through the spawned child. That costs a process per scenario; the review keeps it for the contract control only.
- An in-process mode inside `PdfWorker`. That would be a production path that exists only for tests.
- Sharing the scripted Docling provider in every consumer. It reaches into Docling internals (`object.__new__` pipeline,
  `_release_page_resources`), so that coupling stays in one support owner used by the control and by report derivation.

**Consumers.**
- Production callers: `pdf_worker._native_child` and `orchestrate/pdf_streaming.py:493`.
- Test sites: `tests/semantic/current_pdf_source_support.py` (`_certified_controlled_reply`, `_controlled_stream`, `_section_stream`).
- Candidates from searching for files that use both "PdfWorker" and "stream": `tests/pdf_process_support.py`, `tests/evaluate/declared_record_native_support.py`,
  `tests/semantic/{test_pdf_materialization_native, test_pdf_transform_demand_native, test_actual_pdf_spool_resume,
  current_pdf_integration_support, current_artifact_support}.py`, `tests/ingest/test_pdf_streaming.py`,
  `tests/orchestrate/{test_pdf_streaming_integration, test_pdf_private_execution}.py`. Each needs confirming as a stream patch site.
- `tests/semantic/test_current_pdf_source_inputs.py:58–68` needs re-pointing.

**Acceptance evidence.**
- No test imports `_atomic_bytes` or `_ref`, and no test restates the order (search).
- **Contract control:** one authored document goes through (R) the spawned child with `_child_target` running the scripted provider and (C) the controlled
  route. Compare:
  - (i) the ordered sequence of acknowledged families, with page-capture families (`page`, `candidate_payload`, `native-raster`) filtered out;
  - (ii) the preparation identity, which must be equal;
  - (iii) a projection that does not depend on the build. The publication `logical_digest` is the candidate; confirm it excludes build ids, because record rows carry
    `product_id=build_id`. Otherwise compare record rows with the build columns removed;
  - (iv) the parent accepts the certification in both routes.

  The control fails if the double drops or reorders a step, or mishandles the document, formula outcomes or report. It **cannot** catch a
  defect in the seam itself, because both routes share it. The existing real-child integration test, `test_actual_pdf_spool_resume.py` and the parent's refusals cover that.
- A seam unit case with a malformed report expects the identity refusal before any acknowledgement.
- A seam unit case with a payload schema perturbed from the default expects encoding under the request's schema. Pick an observable before planning (`[I]`: candidates are the companion encoding header or the certification contract). The contract control cannot see this, because both routes use the request.

---

## Seam 2: native I/O of the demand executor

**Native interactions the executor performs** (`src/corpus_structure/orchestrate/data_operations.py`), all **[S]**:

| # | Interaction | Site | Nature |
|---|---|---|---|
| 1 | Demand page resume and obligations; final resume | `:1966–2000`, `:2062` | `DemandPlanner(model, DataOperationStorage(conn))` |
| 2 | Ready set for a page | `_prepare_page :1663–1683` | Planner; runs compiled binding SQL through `storage.connection` (`semantic/data_operation_demands.py:747, 888, 991`) |
| 3 | Rebuilding the original generation | `_generation_ready :844–888` | `read_demand_result` (wire) plus `bound_requests` (planner) |
| 4 | Claim set, with hydration in the **same transaction**, one savepoint per member | `_claim_many :1125–1225` | `claim_data_requests` (wire); `begin_nested`; `_hydrate → hydrate_consumer_selection → admitted_data_read` (relational SQL, `semantic/data_operation_consumers.py:105–150`) |
| 5 | Lease renewal | `maintained_claims(self.engine, …, renew=self._renew) :1956`; `renew_data_request :912–919` | Claim owner on the engine (`semantic/claim_lifetime.py:255`) |
| 6 | Settlement through claim-owner callbacks that receive a connection | `retain_data_completion_intent :1081`, `publish_data_derivation :1259`, `adopt_data_completion_intent :1277`, `release_data_attempt :1356`, `retain_external_data_packet :1399` | wire |
| 7 | Port admission and cached recheck | `acquire_prepared_execution :720`, `acquire_python_execution :766`, `recheck_cached_execution :808` on `admission_engine` | Pure identity plus native inspection (`semantic/data_operation_admission.py:268–310`) |
| 8 | Acquiring the basis for another release or runtime | `host.acquire_basis(engine, conn, …) :823` | Already behind the public `execution_host` parameter |

Outside the seam: `_RequestExecution` hands `engine` to port execution owners (`:299`, which effect ports such as PDF capture use).
That I/O belongs to the ports.

**Smallest coherent seam.** One collaborator, passed to the constructor, becomes the executor's only route to native state. Its default is built from
`engine` and `admission_engine` and preserves today's behaviour. It has three surfaces:
- **unit of work**: a transaction context that exposes wire calls as a `DataOperationCalls`, a savepoint, hydration
  (rows 3 and 4), and a planner bound to that unit (rows 1–3). This preserves the claim-and-hydrate transactional grouping that
  `test_data_operation_execution_basis.py:390–465` asserts (begin, claim, savepoint, hydrate, release or rollback, commit, then renew). Every
  `with self.engine.begin(): DataOperationStorage(conn)` site moves onto this surface.
- **claim lifetime**: the claim owner (row 5). Settlement callbacks (row 6) receive the unit's `DataOperationCalls` rather than a raw
  connection, so a double runs them unchanged.
- **admission**: rows 7a, 7b and 7c return the admission record (identity, authorize, custody). Prefer splitting production so that the
  *pure* identity (`python_port_identity` and so on) stays outside the seam and only the native inspection (`require_data_operation_native`,
  `_inspect_execution_identity`) is replaced. The double then authorizes production's identity and invents no refusals (DTA‑045).

**What the constructor needs, and the cheap source for each:**
- `prepared`, `runtime` and `sources`: from a memoized prepared-kernel recipe, which is pure preparation with no database (§4.2's bounded memo).
  It must declare the test operations: a scalar and a batch Python operation whose source is the admission kernel.
  `RuntimeBinding(prepared.release_id, runtime_id, manifest, archive)` must list those sources if production's pure admission checks run.
- `database_capacity`: give it explicitly. `_database_capacity` accepts any engine without `_corpus_store` (`:614–628`). Capacity 4 with
  `max_provider_jobs ≥ 2` gives today's `port_workers = 2`.
- `policy` (authored), `execution_host=ProcessExecutionHost()` and `host_run=token` (public parameters, `:651–653`).
- `engine`: a **sentinel that raises on any use**, so any I/O that bypasses the seam fails the test.

Tests read `executor.reservation`, which is already public. One case pins the formula with literals: packet 65536 and reply 4096 give
143360, and `max_owned_bytes = 143359` must raise "exceed owned capacity" (`:686–689`). Tests drive the public `advance`
or `run` (`:1885`, `:1907`) with one authored page, instead of setting `executor._physical` and calling `_drive_sweep`.

**Can the existing wire-checked double serve?**
- Partly. `WireCheckedStorage` (`tests/semantic/data_operation_binding_support.py:236–254`) subclasses
  `DataOperationCalls` and validates both directions with `validate_native_wire`.
- It can serve as the unit's wire-call surface for rows 3, 4, 5 and 6 after one extension: replies may be callables of the validated payload,
  or sequences, because claim replies echo the request ids.
- It cannot serve the planner, hydration or admission, which are relational or inspection reads and not wire calls. Their double replies are authored typed values:
  `ReadyDataRequest` items, page dictionaries, hydrated selections, and admissions built from production's pure identity.
- Today's replies include `trust_snapshot={}` in claim results (`test_data_operation_execution_basis.py:72, 418`). Wire validation will
  decide whether that is legal. Expect some authored replies to need correcting.

**Rejected alternatives.**
- Keep `__new__` and import the formula. Eighteen private assignments remain.
- Keep monkeypatching the module names `DataOperationStorage` and `DemandPlanner`. That is the same private coupling, and the replies stay unchecked.
- A fake SQLAlchemy engine. It couples tests to call shapes, and the planner and hydration still need SQL meaning.
- Real PostgreSQL for these tests. The native suites already cover that, but they cannot script races, refusals or capacity windows.
- A per-call factory for `DataOperationCalls` only. Planner, hydration and admission would stay private stubs, so `__new__` would remain.

**Consumers.**
- Construction bypass with `__new__`: `tests/orchestrate/test_data_operation_byte_admission.py:69–181`;
  `test_data_operation_execution_basis.py:47, 109, 396, 465`; `tests/semantic/test_d1_limitation.py:292`.
- Users of `controlled_executor`: `tests/orchestrate/test_execution_host.py:163–244, 369–384`.
- Fault injection on the real database by patching `_publish` or `_retain_answer`: `tests/semantic/test_prepared_authority_batch_native.py:98`, `test_pm2_parser_stage_native.py:174–195`,
  `current_pdf_integration_support.py:440–510`. These may move to wrapping the default collaborator's calls; this is optional and not required.

**Acceptance evidence.**
- A search finds no `__new__(…NativeDemandExecutor)` and no `setattr(data_operations, "DataOperationStorage"|"DemandPlanner")`.
- The sentinel engine stays untouched in every seam-based test.
- The literal reservation pin fails if the formula changes.
- A malformed authored claim reply (with `lease_until` removed) fails with the wire validation error, which proves the double checks replies.
- The transaction-order test passes against the unit double's event log.
- Native suites on the default collaborator still pass (`test_data_operation_external_native`, `test_prepared_authority_batch_native`,
  `test_characterization_native`).

---

## Seam 3: comparing the native host's startup profile

**What source shows.**
- `NativeHost._validate_startup` (`src/corpus_structure/methods/native_host.py:196–213`, private static, called at `:184–185`) compares 11 observation
  fields with the selection's profile:
  - plain equality: `provider`, `profile` (the fingerprint, which covers the whole profile content, so `parameters` and `version` included), `runtime_identity`, `assets`, `backend` and `matmul_precision`;
  - `device` compared on its prefix before ":";
  - `dtype` compared as "torch."+dtype;
  - `cudnn_allow_tf32` compared by identity (`is not`);
  - `native_threads.intra_op` and `native_threads.inter_op` compared under the nested key.

  It raises `Pm2WorkerError`. The population check (`set(metadata) != set(expected)`, `:182–183`) sits apart from it. **[S]**
- On failure the host closes with `grace_seconds=0` and escalates to `NativeRetirementUncertain` only if cleanup fails (`:187–194`). **[S]**
- The child adapters independently refuse a mismatch in runtime identity, artifacts, backend, cache or asset custody before they report (`native_host_adapters.py:17–74`).
  The peer runs none of them. **[S]**

**Design.**
- One public production comparison takes `(selection, observation)` and reports which declared fields mismatch, by name. Either it
  returns the names or it raises `Pm2WorkerError` with the field named. Its compared fields are **declared as data**: observation path to expected
  projection of the profile, with the three projections above kept exact.
- `NativeHost` calls it; the private static method is removed.
- Preserve:
  - a non-dict observation refuses;
  - an absent key is a mismatch;
  - `cuda:N` matches `cuda`;
  - a non-bool `cudnn_allow_tf32` mismatches;
  - the population check and the retirement path stay as they are.

**(a) Perturbation by field (unit, no process).**
- Author by hand a profile and the matching observation, without calling the projection.
- Parametrize over a **hand-written** list of the 11 fields. For each, perturb one value and expect a refusal naming that field.
- Add one hit case, absence cases, and `device="cuda:1"` accepted.
- Add one completeness case: the hand-written list equals the declared field set (§4.4 item 4). Drop this case if the operator reads it as an alignment check.

**(b) Reach control (real process).**
- Add a peer mode, `tests/methods/native_host_cases.py`, selected by argv in the way `startup-hang` already is. It reports one named field perturbed, for example `backend`.
- Start a real `NativeHost` with that command. Expect a `Pm2WorkerError` naming the field, no `NativeRetirementUncertain`, `host.startup == {}`, and the process
  retired.
- The existing echoing peer remains the hit case.
- Remove the invented "frozen selection" refusal in the `Group.startup` double (`tests/methods/test_characterization_resources.py:59–61`). The test at `:243–252` either becomes "`ProviderExecution` propagates a refusal raised by the group" with a scripted refusal, renamed to match, or it is deleted.

**Rejected alternatives.**
- Testing the private method directly. That is the coupling being removed.
- A peer that reads the expected profile back. Circular.
- Making the peer run the real adapters. That needs GPU assets and belongs to provider-backed tests.

**Acceptance evidence.**
- Removing any one comparison from production fails exactly that row and the completeness case.
- Changing the `device` prefix rule fails the `cuda:1` row.
- The reach control fails if `NativeHost` stops calling the comparison, or calls it on anything other than the parsed ready metadata.

**Side observation (route to the coordinator).** `admitted_startup_matches` (`methods/native_profiles.py:165–198`) has **no
consumer in `src/`**; it was searched with grep over `snap3/python` (`.py`) and `snap3` (`.md`). Only `tests/methods/test_native_host.py:617–677` uses it. Either a consumer is pending, or it is superseded machinery to delete
together with its tests. It is a different contract (observed versus admitted startup records) and is not part of this seam.

---

## Question 4: the capture workspace as a binding

**Facts about where the workspace sits.**
- `pdf_capture_custody` puts `str(Path(directory).resolve())` and `assets.root.resolve()` into the
  `pdf-capture/execution-custody` artifact (`semantic/pdf_capture.py:62–104`). That artifact is a boundary contract of the capture sources (`:142–152`).
- At runtime the workspace is read back from custody (`:439–455`). Each claim uses `workspace/sha256(request_id)/generation` and calls `mkdir(parents, exist_ok)`
  (`:257–260`). The submitted original is then written with mode `"xb"` (`orchestrate/pdf_streaming.py:997–1000`), and the build spool lives under
  `…/producer` (`:1008`).
- The PDF transforms (organized, enriched and integrated) write into the **same** workspace: `mkdir` plus `mkdtemp` per request and generation
  (`semantic/pdf_transforms.py:704–710`; bound at `semantic/data_operation_preparation.py:436–507`).
- `current_pdf_recipe` binds the asset root to `tmp_path` and the workspace to `tmp_path/"owned"`
  (`tests/semantic/current_pdf_source_support.py:50–60`). It includes no transforms (`:71–77`).

**(a) After a sealed, read-only per-worker seed workspace, can a clone consumer reach reuse or recovery, or write into the directory?**
- `produce_published_pdf_records` calls `finish_existing_pdf_product` first. For a build that is already **published**, it returns the
  publication without touching the filesystem (`orchestrate/pdf_streaming.py:983–996, 613–632`). **[S]**
- Spool recovery (`verify_spool_recovery`, `:266–273`) is reached only inside `run_private_native_pdf_build`, and only when no
  published, open or frozen build exists. **[S]**
- After a completed capture, reads go through the database (`PublishedPdfReader`, `semantic/pdf_capture.py:277–296`). Searching `src/` for
  later readers of the workspace (`["directory"]`, `.directory`, `manifest.jsonl`, `native-raster`) found only the capture path, the
  transform effect and the spool or recovery code. So **nothing reads the workspace after a completed capture**. **[S within that search; I beyond it]**
- **Writes** happen only when a capture or transform claim actually executes: a new request or generation, a successor task, or any
  transform. On a frozen tree they fail with `PermissionError` at `mkdir`, `mkdtemp` or `open("xb")`. Recovery also opens `WRITER` with `O_RDWR`, which fails the same way.
- An existing directory does not fail: pathlib's `mkdir(exist_ok=True)` tolerates `OSError` when the target is an existing directory. **[I: Python stdlib behaviour, not re-read]**
- Result: a read-only workspace **fails closed**. A consumer can reach neither silent reuse nor recovery. A misclassified consumer
  fails loudly. Whether a re-registered demand over a seeded completed capture reuses the derivation, and so never claims, is **[I]**. If it does claim, it fails loudly rather than passing wrongly.
- Contrast: a shared *writable* per-worker workspace is unsafe. Sequential clones would see earlier files. If request or build ids repeat
  across clones (**[I]**, unverified), `open("xb")` collides, or recovery under the same `build_id` finds the previous test's spool.

**(b) Identity of clones.**
- The workspace path is in the custody artifact. Dependency digests enter the release manifest (`semantic/authored_sql.py:364–379`). The review states that the release
  identity therefore depends on the path. **[S for the manifest; the hash into `release_id` was not re-traced]**
- The seed directory comes from the registry's per-seed allocator (`scripts/native_scenario_seeds.py:213`), so the identity is **stable for every clone
  of one seed within a worker, and different across workers and sessions**.
- Nothing compares it across processes: seeds are per worker (ADR‑0102), the head key covers migrations only, and the PDF child receives
  `release_id` from its own parent in the request. **[I: absence from targeted reading, not an exhaustive search]**
- One **in-process** comparison does matter. §4.2's bounded memo keyed by recipe content would return a prepared release that is bound to
  *another* location, unless the memo key includes the binding.

**(c) What the recipe/binding split must guarantee for RC08 to be sound without a production change.**
1. The recipe value carries no location. The builder calls the capture-source composer with the binding at build time.
   `recipe_id` is computed over the value without the binding.
2. Every cache of a product that depends on the binding (seed, prepared-kernel memo) is keyed by **(recipe, binding)**. Equivalently, a per-worker
   binding is a pure function of the seed, one directory per seed, and a per-consumer binding is never memoized or sealed.
3. Scenario content that changes the produced state is recipe content: the authored document and section rows of the controlled
   converter, and the kind of converter.
4. Both bound locations, workspace and asset root, lie inside the seed directory, so `_freeze_tree` (`native_scenario_seeds.py:168–175`) and
   the ownership check on `seed_files` (`:237–243`) cover them.
5. **Binding class by consumer.** Any consumer whose claims execute a workspace-writing operation, meaning capture itself or any PDF transform, uses a
   per-consumer binding: built in its own clone and never sealed. This includes today's `_current_pdf_source`, which runs capture in each clone (`current_pdf_source_support.py:371–378`). So the
   admitted-release stage of a PDF recipe is *not* seedable without a production change. Only post-capture state is.
6. `validate_clone` checks that the bound workspace exists and is read-only, and that the seeded state has no unfinished task or lease.

If production later binds the workspace (and the asset root) at run time instead of in release custody, several things become simpler or unnecessary:
- Releases become location-free, so the admitted-release stage is seedable for **all** PDF consumers, including those that capture.
- Each execution gets a per-test workspace through the execution basis. The executor and the basis already carry `runtime_locations`; whether they can host this is **[I]**.
- The per-consumer binding class, the (recipe, binding) memo key and the read-only constraint on consumers all disappear.
- Release identity becomes equal across machines and workers.
- F06's seed would not need workspace contents at all, since nothing reads them after capture.

Whether the path is deliberately part of custody's authority is the production owner's decision (§15). It is not this plan's.

**(d) Smallest safe F06.** It is safe without a production change, in this form:
- A second stage of a **per-worker-bound** PDF recipe: the admitted release plus project initialization, the registered original, and the registered and executed demand through capture
  and discovery, sealed with the workspace inside the seed directory and frozen.
- The **seed builder** installs the controlled converter, using the Seam 1 double. It cannot rely on a test's monkeypatch, because the build runs outside any test. The
  converter's content is in the recipe.
- The original's temporary file is removed before sealing, since custody keeps the bytes in the database.
- Eligible consumers: claims start after capture **and** execute neither capture nor any transform. Capture, retry and multi-document consumers use the per-consumer class.
- Why it is safe:
  - published capture short-circuits before any filesystem access;
  - recovery is unreachable for a published build;
  - no later reader of the workspace was found;
  - any write fails closed on the frozen tree.
- Residual unknowns: whether demand reuse avoids a capture claim for consumers that register new demands (**[I]**; if not, the failure is loud), and whether a consumer of `current_pdf_source` depends on page or candidate custody (the controlled path has never supplied it).

---

## Cross-cutting notes for the plan

- Seam 1's double feeds F06's builder, and F06 depends on RC08's binding split. Schedule Seam 1 → RC08 split → F06.
- Seam 2 depends on a small, memoized prepared-kernel recipe that declares the admission-test operations (§4.2 memo).
- Seam 3 is independent.
- Unverified premises to settle before planning:
  - whether publication `logical_digest` is independent of the build (Seam 1 control);
  - where the payload schema becomes observable (Seam 1 unit case);
  - whether today's authored claim replies pass wire validation (Seam 2);
  - whether demand reuse avoids a capture claim (F06).

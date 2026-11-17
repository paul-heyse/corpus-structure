# Design review: production efficiency, first-principles pass · 2026-11-17

**Kind:** principle-focused diagnostic review (FP-07/A4 and the efficient-architecture heuristics
H1–H28), standalone, at the operator's direction. It finds avoidable work in production code and
gives a lead for each finding. It does not compare remedy designs, revise a plan, change a rule
or certify alignment. Findings are cited as `review#Fnn`.

## 1. Baseline, method and limits

- **Source:** commit `fc73d2c8c36c5443eb038d12a83a5d8cccfdba6f`, read from a frozen export.
  Standard: core 3.3, heuristics 1.0, binding. Every statement below is dated 2026-11-17.
- **Scope:** production code under `python/corpus-structure/src/corpus_structure/` (about 270k
  lines), the current PL/pgSQL bodies in `semantic/sql/` and the head migration, `services/`,
  `ops/postgresql/`, and the `ci` command's own orchestration. Tests, fixtures, test support,
  `tools/evidence`, process scripts and Chandra OCR (`ingest/pdf_chandra.py`) are out of scope.
- **Method:** static source reading only. Two operation maps and a mechanical site census
  supplied leads. Six lane reviewers read the decisive source per subsystem. The coordinator
  re-read the source behind the headline findings, and an independent reviewer then opened the
  cited source for every finding (section 8). No test, database, provider, EXPLAIN, benchmark
  or probe was run.
- **Not an input:** the living audit, earlier reviews, plan-improvement reviews and plan
  finding tables were not read while findings were formed. The binding's audit-refresh
  prerequisite was deliberately not applied (operator direction, 2026-11-17). Sections 9 and 10
  relate the findings to existing owners after the fact.
- **Claim strength (§D):** each finding describes **Implemented** code as read at the baseline.
  Each lead is **Proposed**. Nothing here is Tested or Measured. A finding states work the
  source shows is repeated or amplified, and what it grows with. It never states a speedup.
- **In flux:** 810 production files changed in the five days before the baseline, including
  almost every declared-data-operation, serving, CLI and model-method file. Findings marked
  *(in flux)* must be re-checked against the current tree before anyone acts on them.
- **Paths:** `P/` = `python/corpus-structure/src/corpus_structure/`; `sql/` = `P/semantic/sql/`.

**Workload premise.** One operator, one workstation, a local GPU and a dedicated PostgreSQL 18
cluster. The benchmark input is one 518-page book; the target is multi-document corpora in any
domain. Consumers are the `ci` CLI, typed queries and exports, and an agent tier calling MCP
tools. Growth dimensions used below: pages per document, items, pieces and sentences per source
view, obligations and requests per demand, documents per corpus, MCP requests per session, and
`ci` invocations per session.

## 2. Structural causes

Most findings are instances of six causes. Correcting a cause once addresses several findings.

1. **Immutable things lose their established status** (F03, F04, F09; parts of F18 and F29).
   Releases, captured sources, validated payloads, model weights and retained products are
   immutable, yet each layer and step re-derives, re-hashes or re-validates them. H19 asks for
   an established property to be carried while its premises hold; H18 places enforcement where
   uncertainty enters.
2. **Bytes-backed snapshots are decoded on every read** (F01). Immutability is enforced by
   keeping canonical bytes and parsing or deep-copying on each property access, inside
   per-item loops (H15, H16).
3. **Access paths are missing for the keys actually probed** (F02, F08, F15). Sorted or keyed
   collections are scanned linearly, tables are filtered on unindexed columns, and search text
   is rebuilt per request (H9).
4. **Validity is recomputed on read from whole-demand state** (F05, F06, F07). Support
   validity, binding and pinned-read checks are evaluated per row and per call over the entire
   demand, with no memo within a statement (H5, H10).
5. **The semantic unit became the physical unit** (F10, F12, F13; the per-scalar part of F14).
   One obligation, row, occurrence, question or page gets its own native call, transaction,
   process hand-off or model exchange, although the layers underneath accept sets (H2, H8).
6. **Preparation is scoped to a call when its inputs are stable for a session or release**
   (F16–F24). Pools, caches, indexes, grammars and worker processes are rebuilt per request,
   per page or per invocation (H12).

F11 is a separate capacity-model coupling (H21). F25, F26 and F28 concern PDF stage movement
and recovery units (H16, H20, H24).

## 3. A4 judgments per operation

These are qualitative judgments at **Proposed** strength from static evidence.

| Operation | A4 | Basis |
|---|---|---|
| PDF capture and stage publication | violated | Page bytes adopted twice; whole-product copy, read-back and re-validation per stage (F25, F26) |
| Whole-document PDF reads (detach, recognition inventory) | violated | Per-scalar point reads, each executed twice under a budget (F14) |
| PDF same-demand resume | violated | The retry unit is the whole conversion, or a recorded worker failure, transient or not, that is reused under the same recipe (F28) |
| Recognition (Nemotron) | violated for per-page preparation; satisfied for provider admission | F20 |
| Declared data operation: register, bind, attach, execute, publish | violated | Each obligation binds over the whole demand (F06) with an unmemoized validity walk per candidate (F05) and no index on the probed predicates (F08) |
| Repeat run of an unchanged demand | violated | One native round trip per graph node, paged two at a time (F10, F11) |
| Enrichment: model methods | violated | Scalar model calls; whole-view state rebuilt per block (F01, F13) |
| Semantic product derivation | violated for the larger-document target | Per-source work quadratic in view size (F01, F02) |
| Rich rule and relation evaluation | unresolved | Repetition shown; materiality depends on claims per document (F02, F09) |
| Grading a question population | violated | Reference side re-bound per candidate (F29) |
| MCP read session | violated | Per-request pool, release re-derivation, replayed paging (F03, F16, F17) |
| Source search (`find`) | violated | Whole selected population re-read and re-tokenized per request (F15) |
| External packet cycle | violated at `submit` and `located`; lifecycle otherwise sound | F03, F18 |
| Companion export | satisfied | One snapshot, streamed ADBC batches, vectorized checks; the comparison verb verifies twice (F31) |
| `ci` working loop | unresolved | Eager registry import is shown; its cost is unmeasured (F22, F23) |
| `ci model` change cycle | unresolved | Three compiles per change; frequency unmeasured (F24) |
| Connection plumbing for CLI and executor | satisfied | One psycopg pool lent through `NullPool` is sound delegation (H4) |

## 4. Findings

Ordered by §E's sequence: remove unnecessary work, then algorithms and access paths, then
placement and reuse, then concurrency. Value and burden are qualitative.

### Tier 1 — repeated work on immutable inputs, and missing access paths

**F01 — Source views held as bytes are decoded or deep-copied on every property read, inside per-item loops** *(partly in flux)*
- Principles: H16, H15, H19, H9; FP-07, DP-10.
- Work: `ConstructionSource.value/text/pieces/items/projection` each run `json.loads` on the
  whole source per access. `ConstructionLayer.occurrence` reads them several times per call and
  scans all pieces; it is called per syntax node, term, cue and frame. In the contextual kernel
  `DeclaredNativeFrameSource.pieces/items/ancestors` deep-copy the whole column per access, and
  a fresh `ContextualLayer` per block iterates every item of the whole view while reading the
  pieces column once per item. `quotations()` scans every protected extent per character.
  `FrozenNativeSource.value` and `DemandResult.cut` follow the same pattern. Work grows with
  (occurrences + blocks) × view size; in the contextual kernel with blocks × items × pieces.
- Cause: immutability is enforced by re-decoding owned bytes instead of freezing a decoded form
  once; block-local builders take whole-view inputs with no shared view-level index.
- Evidence: `P/semantic/constructions/layers.py:28-50, 83-115`;
  `P/semantic/declared_record_sources.py:216-219, 262-277`;
  `P/semantic/contextual_native_products.py:81-94`;
  `P/semantic/contextual_characterization.py:219-277, 413-431, 589-640, 651-702`;
  `P/semantic/model_characterization.py:96-112`; `P/semantic/source_products.py:399-428`;
  `P/semantic/constructions/retained_rules.py:2056-2184`; `P/semantic/demand_results.py:84-114`.
- Preserve: snapshot immutability, exact occurrence identities, block-local inference scope.
  `PreparedNativeSource` (`P/semantic/source_contexts.py:230-270`) already builds an immutable
  once-per-source index with bisectable ends; these kernels do not use it.
- Lead: decode once per kernel call into an immutable prepared view (text, frozen pieces with a
  sorted starts array, items and ancestors by `self_ref`, per-layer id maps and interval
  indexes) and pass it read-only to every block and helper.
- Open premise: items, pieces and blocks per source view for the benchmark book.
- Value high / burden low-medium.

**F02 — Keyed and ordered lookups are done by linear scans inside per-unit loops** *(partly in flux)*
- Principles: H9, H10, H7; FP-07.
- Work: `_requested_regions` runs `all()` over all pieces per extending piece; regions are
  clipped against every sentence boundary; `source_layout` scans pieces forward and back per
  block; `FormalSourceReadings` rebuilds occurrence and annotation dicts over the whole product
  on every query and is queried per passage, span and family; the formal and interpreted
  product validators scan every piece for every extent. Procedure readings, formula windows,
  rich-rule alternatives, `is_a`, enrichment coverage and the hierarchy sibling search have the
  same shape. Most inputs are already sorted by offset or keyed by id.
- Evidence: `P/semantic/construction_products.py:261-284, 349-354, 431-506, 634-642`;
  `P/semantic/constructions/retained_rules.py:44-81, 1865`;
  `P/semantic/constructions/navigation.py:907-915`;
  `P/semantic/formal_readings.py:116-120, 196-201, 262-317`;
  `P/semantic/formal_products.py:277-283`; `P/methods/scoped_relations.py:216-293`;
  `P/methods/source_preparation.py:831-877`; `P/semantic/rich_rule_evaluation.py:549-556, 769-773`;
  `P/semantic/rich_rules.py:334-344`; `P/ingest/pdf_selected_enrichment.py:106-143`;
  `P/semantic/source_hierarchy_graph.py:76-80`.
- Preserve: output order and multiplicity, the non-native-gap merge rule, nearest-heading
  selection, completeness semantics of formal readings.
- Lead: one ordered sweep or `bisect` over the sorted collection, and maps built once per
  product. `FormalSourceReadings` is already named as the index owner.
- Value medium-high for large views / burden low.

**F03 — Read and external paths fully re-derive the release instead of opening the admitted archive** *(in flux)*
- Principles: H18, H19, H12, H20; FP-07, DP-09.
- Work: `load_release_inputs` re-reads and re-hashes every input, re-runs release preparation,
  rebuilds and byte-compares the archive, then issues one SELECT per projection relation and
  compares both sides. It runs per `query_knowledge` page, per composite read scope, per
  external `submit` and `located`, and per selected-source read. On read and external paths
  the work grows with requests × release size. On execution it is a fixed cost per run: once at
  registration and once per (release, runtime) basis, which the executor caches.
- Cause: the verification-boundary loader is also the general loader. The owner states the
  split: `open_release` "Open immutable archived products for reading"; `verify_release`
  "Fully rederive at explicit verification/admission boundaries".
- Evidence: `P/semantic/releases.py:414-515, 280-293`; read callers `P/serve/rich_knowledge.py:100`,
  `P/serve/selected_contributions.py:363`, `P/serve/interpretation_authoring.py:174, 308`,
  `P/serve/selected_source.py:412`, `P/semantic/data_operation_external.py:237, 330`.
  Execution: `P/orchestrate/data_operations.py:670-681` (cached basis),
  `P/semantic/data_operation_service.py:174-207` (consumes bundle and dependencies),
  `P/semantic/data_operation_execution_context.py:38` ("Reverify archived meaning once at the
  execution boundary").
- Preserve: full re-derivation at admission, activation and explicit verification commands;
  archive digest checks; §B5.
- Lead: move read and external consumers to `open_release`. Whether execution remains a
  verification boundary is an owner decision, not a reroute: it needs inputs `open_release`
  does not return, and its code documents the re-verification as deliberate.
- Open premise: the reconstructed `PreparedRelease` carries every field the read consumers use.
- Value high / burden low-medium.

**F04 — Each native call rebuilds the wire protocol document three times and validates input and output twice each** *(in flux)*
- Principles: H12, H19, H20, H26; DP-10.
- Work: `_invoke` calls `validate_native_wire` (input), `wire_role_kind` and
  `validate_native_wire` (output). Each calls the uncached `_protocol_content(None)`, which
  reads and YAML-parses the protocol file, rebuilds the ambient extension schemas
  (execution evidence, visual read, record-policy grade, operation-event frame, original
  support reference) and canonicalizes the document; only the steps after it are cached, and
  they hash the fresh bytes again. PostgreSQL's generated wrapper validates the same payload on
  input and on its own output, re-evaluating a large inline contract constant per call. Work
  grows with native calls: several per executed request, plus one per bound obligation and per
  expanded member.
- The Python and SQL checks are not one check repeated. Python validates against the on-disk
  protocol; SQL validates against the captured contract installed with the release. The Python
  output check therefore also detects a client/native contract mismatch.
- Evidence: `P/semantic/data_operation_storage.py:779-806, 557-573`;
  `P/semantic/data_operation_wire.py:35-148, 191-192, 334-369`; `sql/data_operation_wire.sql:1-15`.
- Preserve: validation at the security-definer boundary (§B4); the captured-sources path used
  when installing or inspecting a captured release; exact-JSON encodability.
- Lead: memoize the ambient protocol bytes, per-operation schemas and role kinds once per
  process. That part changes no guarantee. Dropping a Python or SQL check is sound only where
  native admission pins the equality of the two contracts for the process; treat that as a
  separate decision.
- Open premise: whether pg_jsonschema builds a validator per call.
- Value high / burden low for the memo.

**F05 — Support validity is an unmemoized recursive walk re-run at every lifecycle step and for every candidate row** *(in flux)*
- Principles: H10, H19, H13, H9; FP-07, DP-09.
- Work: `ddo_support_valid` recurses over support edges with no visited set, so shared
  ancestors are re-checked once per path. `ddo_use_valid` runs the direct check and then
  `ddo_support_valid`, which repeats it. `ddo_direct_support_valid` calls seven per-kind
  dependency validators unconditionally. The walk runs per admitted use in binding rows, at
  attach, claim, renew, retain, adopt and publish, per row of a read page, and per PDF
  companion row through the stage-owner check. The edge lookup itself is indexed (the support
  table's primary key starts with `derivation_id`).
- Evidence: `sql/data_operations.sql:226-312, 406-452`; callers
  `P/semantic/data_operation_projections.py:586, 1574`,
  `sql/data_operations.sql:930-986, 1038, 1080, 1269, 1303, 1506`,
  `P/semantic/pdf_staging_native.py:94`.
- Preserve: revocation of a derivation, recipe, runtime, product or original admission must
  invalidate dependents; population supersession; kernel-digest change. Validity is relative
  to the read boundary (`ddo_read_visible`), so the visibility part stays per read.
- Lead: evaluate validity set-wise once per statement over the distinct reachable episodes and
  dispatch per-kind checks by operation family. A maintained invalidation record can cover only
  the boundary-independent part (revocations and derivation outcome).
- Open premise: paths versus distinct nodes in the benchmark support graph.
- Value high / burden medium.

**F06 — The binding for one obligation is derived several times, each over the whole demand** *(in flux)*
- Principles: H5, H7, H12, H19, H20; FP-07, DP-08, DP-10.
- Work: Python binds each obligation in `ready()`. `_generation_ready` re-reads the frontier
  from the start in pages of 1000, re-binds and byte-compares. Hydration re-evaluates the same
  binding-row base. `attach_data_request` re-interprets the binding expression in PL/pgSQL.
  Each pass materializes every fulfilled use of the whole demand with F05 validity applied
  before filtering by role, kind and subject. Obligations still waiting on inputs are re-bound
  every round, and failed requests are filtered only after binding.
- Evidence: `P/orchestrate/data_operations.py:687-777, 1222-1234`;
  `P/semantic/data_operation_demands.py:711-731, 958-983`;
  `P/semantic/data_operation_projections.py:549-596, 640-722`;
  `P/semantic/data_operation_consumers.py:136-149`; `sql/data_operation_bindings.sql:723-823`;
  `sql/data_operations.sql:2106-2131`.
- Preserve: database authority over the binding (§B4, §B5); quantified operators need the full
  universe; frozen-binding semantics for generations adopted from another demand or read; late
  hydration, which avoids moving bodies for reused obligations.
- Lead: reuse the `ReadyDataRequest` binding when the claimed generation is the one just
  attached under the same read; push role, kind and subject reduction ahead of validity; keep
  one authoritative binding evaluator and make the other a differential test; skip re-binding
  an obligation whose prerequisites have no newer publication.
- Value high / burden medium.

**F07 — Every pinned read, including limit-1 pin re-acquisitions, recomputes whole-demand closure and authorization, and writes** *(in flux)*
- Principles: H5, H10, H12; FP-07.
- Work: `read_demand_result` computes the recursive support-scope closure over all uses of the
  demand, inserts and share-locks each scope, and authorizes every use, independent of `limit`.
  `admitted_data_read` calls it with `limit: 1` before each binding projection and hydration.
- Evidence: `sql/data_operations.sql:1642-1690`; `P/semantic/data_operation_storage.py:1320-1331`;
  `P/semantic/data_operation_projections.py:339-354`.
- Preserve: a pinned read fails if a scope epoch changed since acquisition; the caller is
  authorized on every call.
- Lead: store the complete scope list on the read row at acquisition and add a narrow check
  that locks and compares those rows and authorizes the caller over the distinct kind
  universes; reuse a pin within one transaction.
- Open premise: the visible closure under a fixed boundary cannot gain scopes.
- Value high / burden low-medium.

**F08 — The most-probed declared-operation tables declare no index for their predicates** *(in flux)*
- Principles: H9, H10; FP-07.
- Work: `ops.demand_use` is filtered by `demand_id`, `(request_id, generation)`,
  `(obligation_id, created_at, id)` and `derivation_id`; `ops.data_derivation` by
  `(request_id, generation)`; `ops.data_obligation` by `demand_id ORDER BY id`. The physical
  model declares only a primary key for each (plus `unique(intent_id)` on derivation), indexes
  are created only from `ph:indexes`, and no migration creates another index on these tables.
  An `OR exact_pin` predicate in the binding universe would defeat an index in any case. These
  tables accumulate across demands and generations.
- Evidence: `P/model/semantic/data-operation-physical.yaml:104-117, 355-371, 441-460` (four
  `ph:indexes` entries at 193, 495, 526 and 564, none on these tables);
  `P/schema/relational.py:256-278`; predicates at
  `sql/data_operations.sql:497-500, 957, 1012-1015, 1042-1045, 1572`,
  `P/semantic/data_operation_projections.py:279-286, 557-581`. The live catalog was not checked.
- Lead: declare the composite indexes for these predicates and rewrite the `OR` as a union.
- Value high / burden low.

**F09 — Other established properties re-established without a change in premise** *(in flux)*
- Principles: H19, H18, H20, H12; DP-10.
- **(a) Captured Python sources.** A CPU call ships every captured source in its packet and
  re-authenticates them (re-read, `ast.parse`, `compile`) before the call, inside each
  `submit()` attempt while slots are full, after the reply and again in the worker. Stream
  items and coroutine turns add more; M1 verifies before and after every GLiNER question.
  `P/semantic/data_operation_cpu.py:74-234`; `P/semantic/data_operation_ports.py:639-655, 1193-1340`;
  `P/semantic/data_operation_stream.py:252-290`; `P/semantic/data_operation_prepared_products.py:68-110`;
  `P/core/work.py:139-145`. Preserve detection of on-disk change and rebinding, which is real
  in a tree edited concurrently. Lead: authenticate at port acquisition and worker import, and
  keep constant-time identity and file-stat checks per call.
- **(b) Release facts inside SQL.** Release artifacts are parsed and re-hashed inside expand,
  attach, publish and each dependency validator; `require_pdf_operation` parses the PDF
  contract four times with four hashes, per companion row.
  `sql/data_operations.sql:335-350`; `sql/data_operation_bindings.sql:723-735`;
  `P/semantic/pdf_domain_native.py:11-60`. Lead: lower these facts into typed rows at release
  admission.
- **(c) Retain then publish.** `publish_data_derivation` re-runs the completion battery and
  witness check on the immutable intent that `retain_data_completion_intent` inserted after
  the same battery passed. `sql/data_operations.sql:1265-1287, 1510-1532`. Publish is also the
  reconciliation and adoption path: it can run under a different holder, after a native
  upgrade, and includes caller authorization. Lead: record on the intent a kernel digest that
  covers every completion-validator body; at publish check that digest, the mutable premises
  and caller authorization. Open premise: which validators read mutable state.
- **(d) Retained products at consumers.** Each consuming request re-validates formal,
  annotation and construction inputs that were validated at production; rich consolidation
  validates its own in-process graph three times and recompiles the release-stable rule policy
  per document. `P/semantic/characterization_ports.py:604-627, 740-775`;
  `P/semantic/rich_consolidation.py:204-223, 322, 438-446`. Open premise: the trust model for
  retained bodies on read.
- **(e) Python ingress and egress.** `TypeAdapter` is constructed inline at about a dozen sites
  per call, role and field; the parent fully validates arguments only to serialize them for a
  stricter worker validation; each output scans every model kind and edge.
  `P/semantic/data_operation_ports.py:294-381, 508-899`. Lead: prepare adapters and member
  contracts once per port.
- **(f) Model assets.** Every native host start re-hashes all resident weight files and runtime
  inventories; each capture and enrichment child re-hashes the Docling bundle.
  `P/methods/pm2_native.py:41-66, 174-199`; `P/methods/gliner.py:178-197`;
  `P/ingest/pdf_assets.py:29-41`. The contextual encoder already hashes once and then compares
  stat tuples (`P/methods/contextual_embeddings.py:328-378`).
- **(g) Serving implementation identity.** Each rich or composite request re-hashes 31 to 66
  source files and scans `sys.modules` twice. `P/serve/rich_queries.py:60-97`;
  `P/_query_custody.py:139-209`. Re-hashing disk per request is what lets a long-lived server
  refuse when its loaded code differs from the current files. Using the digests recorded at
  import would change the guarantee from "running code equals current disk" to "identity names
  the running code". That trade is the decision; a stat comparison keeps drift detection at
  lower cost.
- Value high for (a)–(c), medium for the rest / burden low to medium each.

### Tier 2 — interfaces that force item-by-item work, and capacity coupling

**F10 — The native facade offers only single-item calls, so the obligation graph costs one round trip per node** *(in flux)*
- Principles: H8, H2, H13; DP-10.
- Work: one `expand_data_obligation` per root × operation and per member × closure operation,
  one `attach` per obligation, one `claim` per request and per batch member. `seen_discovered`
  is local to one run, so a repeat run of an unchanged demand re-issues every expansion, and
  each re-expansion marks progress and forces another round. Every call carries F04.
- Evidence: `P/semantic/data_operation_wire.py:715-732`;
  `P/semantic/data_operation_demands.py:534-592, 645-683`;
  `P/orchestrate/data_operations.py:1105-1123, 1366-1433`; `sql/data_operations.sql:687-716`.
- Preserve: per-item fates, receipts and fences; idempotent obligation identity; per-member
  failure isolation.
- Lead: generate set-form operations that return per-item results; skip expansion when the
  snapshot shows the population closed and expanded; let an unchanged repeat run return after
  one frontier read.
- Value high / burden high (paired native functions).

**F11 — One worst-case byte reservation fixes in-flight requests, frontier page size and batch size at about two** *(in flux)*
- Principles: H21, H22, H8, H11; DP-20.
- Work: `reservation = 2 × max_packet_bytes + 3 × max_reply_bytes` is 704 MiB at the defaults
  against a 2 GiB budget, so `capacity` is 2, and 1 when preparation bytes exceed 640 MiB. The
  frontier is read with `limit = min(limit, capacity)`, so every two obligations pay a full
  page cycle and wait on the page's slowest request before the next page is bound. A batch-form
  call is cut to two members.
- Evidence: `P/core/execution_policy.py:15-28`; `P/orchestrate/data_operations.py:555, 1312-1317, 1384`.
- Preserve: the bound on combined live memory; per-request fences; a batch is not exempt from
  byte bounds.
- Lead: separate the logical page size from memory admission; size the reservation from a
  bound closer to the operation's actual payload; charge a batch once per physical call; keep
  a ready queue so binding overlaps compute. Raising the page size exposes per-page linear
  searches in the driver (`P/semantic/data_operation_demands.py:649-659`,
  `P/orchestrate/data_operations.py:1394-1398`) that are harmless at two.
- Open premise: whether the operator overrides the policy.
- Value high / burden medium.

**F12 — Row-at-a-time native writes where a set path exists** *(partly in flux)*
- Principles: H2, H8, H10; FP-07.
- Work: PDF companion rows go through one `ops.adopt_pdf_companion` call per row, and each row
  re-runs the build-owner fence (support validity included) and the contract check; the
  payload family is re-prepared per page; rows cross five representations on the way; formula
  outcomes take one transaction each. Product publication inserts members one at a time,
  re-extracts the container's members array per member and runs three schema checks per member.
- Evidence: `P/semantic/native_call_generation.py:843-856`; `P/semantic/_pdf_native_calls.py:464-495`;
  `P/semantic/pdf_publication_native.py:534-660`; `P/semantic/pdf_staging_native.py:71-125`;
  `P/semantic/pdf_publication.py:256-261`; `P/orchestrate/pdf_streaming.py:298-327, 415-439`;
  `sql/data_operations.sql:1345-1400`.
- Preserve: per-row identity, order and replay checks; idempotent conflict detection.
  `adopt_pdf_batch` already shows the set-wise shape (scratch table, COPY, one adopt call).
- Lead: stage companions through the COPY path with one fence per call; insert members and
  family rows with one set-wise statement each.
- Value high for companions, medium for members / burden medium.

**F13 — Model calls are issued one input at a time and awaited serially** *(in flux)*
- Principles: H2, H8, H12, H22; DP-10.
- Work: the contextual encoder runs one declared request per occurrence or target, parses the
  whole native context each time and encodes one input. Characterization operations declare
  the scalar form, so the existing batch path is unused. GLiNER questions carry one input and
  run in sequence, each with an admission exchange and an extraction exchange. HanLP uses two
  exchanges per group of sentences. Learned primary waits on each block before the next.
- Evidence: `P/methods/contextual_encoding.py:12-111`; `P/semantic/contextual_encoder.py:468-623`;
  `P/methods/m1_source.py:616-807`; `P/methods/characterization_resources.py:369-410`;
  `P/methods/native_host_adapters.py:95-196`; `P/semantic/hanlp_products.py:366-420`;
  `P/semantic/learned_primary.py:511-703`. `P/semantic/definition_model_products.py:224-270`
  already sends multi-input batches with per-member receipts.
- Preserve: one observation per vector or question (§B2); per-input admission outcomes and
  receipts; D1 stage order within a block; HanLP's GPU-memory bounds; the declared numerics.
- Burden: native admission requires the scalar form and one CPU receipt per completion for
  contextual retrieval, operation events, definitions and structural admission
  (`P/semantic/contextual_admission_native.py:43`, `P/semantic/operation_event_native.py:21`,
  `P/semantic/definition_admission_native.py:53`). A batch form changes those native contracts.
- Lead: make "all requested occurrences of one view" the physical unit for the encoders; emit
  one multi-input question per pack; merge admission and extraction into one host exchange;
  process stages across blocks where no dependency orders them.
- Open premise: results are invariant to batch composition within the declared policy.
- Value high / burden medium-high.

**F14 — Whole-document reads are assembled from per-scalar point reads, each executed twice under a budget** *(in flux)*
- Principles: H8, H20, H5; DP-10.
- Work: whole-product detach issues several statements per externalized scalar; with a read
  budget each page is preceded by a preflight that re-executes the same statement wrapped in
  `octet_length`. Recognition hydrates the whole document only to read the page inventory and
  health. Integration loads every observation into memory, writes it to Arrow and sorts it back
  with DuckDB.
- Evidence: `P/semantic/pdf_record_reader.py:50-92, 287-418, 748-787, 1408-1468`;
  `P/semantic/pdf_transforms.py:447, 515-596, 863-867`.
- Preserve: pin and digest verification of each stream; refusal of over-budget products.
- Lead: within an admitted whole-product read, rely on the single materialization bound and
  read scalars in one ordered stream; give recognition a narrow page-inventory read; read
  observations in canonical order from the database.
- Value medium-high / burden medium.

**F15 — `find` rebuilds the searchable text of every selected document per request** *(in flux)*
- Principles: H5, H7, H9, H12, H15; FP-07.
- Work: per request and per continuation page, one native read per section, Python assembly of
  all section text, upload as a `VALUES` list and `to_tsvector` at query time with no index.
- Evidence: `P/serve/source_search.py:94-178`; `P/ingest/pdf_section_views.py:81-110`.
- Preserve: the pinned selection scope, projection digests on hits, cursor stability.
- Lead: a per-publication search projection with a stored `tsvector` and index, prepared at
  publication or on first search; hydrate only returned rows.
- Value high / burden medium.

### Tier 3 — preparation scoped to a call instead of a session or release

**F16 — Every MCP read tool opens and closes its own pool and engine, which also empties the release cache** *(in flux)*
- Principles: H12, H14, H21; FP-07.
- Work: per tool call, a psycopg pool, a new backend, the extension check, dialect
  initialization and the principal check, then disposal. A fresh backend also starts with cold
  function caches. The archived-release cache is keyed on the engine, so it starts empty on
  every request.
- Evidence: `P/intervene/demand_read_tools.py:37-51`; `P/intervene/semantic_server.py:60-104`;
  `P/intervene/native_render_tools.py:51-54`; `P/semantic/archive_reader.py:28-31, 373, 401`.
  The external server already holds one lazily opened engine for the session
  (`P/intervene/external_server.py:40-66`).
- Preserve: per-purpose principals, per-call transaction and snapshot, cancellation. The cache
  is keyed on the engine on purpose ("Engine lifetime bounds database authority").
- Lead: hold one read engine per purpose in the server lifespan. The engine-keyed cache then
  persists for the session; do not re-key it.
- Value high / burden low.

**F17 — Continuation pages rebuild every derived structure and replay rows from the start** *(in flux)*
- Principles: H12, H10, H14; FP-07.
- Work: each page re-reads the pinned closure, rebuilds a temporary SQLite witness index row by
  row, re-validates and re-indexes the rich graph, then regenerates every row before the
  cursor. Bounded pages also serialize the whole envelope once per accepted row. Demand export
  fetches each frontier page's support closure separately and deduplicates on the client.
- Evidence: `P/semantic/demand_results.py:117-170, 267-372`;
  `P/semantic/data_operation_read_index.py:50-95`; `P/semantic/rich_queries.py:594-605`;
  `P/semantic/demand_queries.py:94-200`; `P/serve/rich_queries.py:184-263`;
  `P/serve/demand_export.py:172-218`.
- Preserve: the per-page native trust recheck, cut identity on cursors, byte budgets.
  `P/serve/contribution_facets.py:297-309` already sizes pages by accumulating row widths.
- Lead: keep the per-page reacquisition; hold the validated graph or witness index in a small
  process cache keyed on cut identity; store a position in the cursor; accumulate row widths.
- Value high / burden medium.

**F18 — `submit_result` repeats the packet read and the release re-derivation per packet** *(in flux)*
- Principles: H12, H18, H20.
- Evidence: `P/semantic/data_operation_external.py:185-252, 319-331`.
- Preserve: the server never trusts agent-supplied packet bytes; fence and trust checks at
  admission; §B3.
- Lead: keep the packet bytes read under the same fence in the session, falling back to the
  native read on a miss; open the release through F03's route.
- Open premise: the second read adds no guarantee beyond native admission.
- Value medium / burden low.

**F19 — Execution resources live for one invocation** *(in flux)*
- Principles: H12, H21, H25; DP-20.
- Work: the spawn process pool, worker imports, shared-memory release capsule and native model
  host are created and torn down per `advance`, so an MCP render with uncached work pays
  process start, imports and model load for one request. Claim, hydrate, retain and publish
  are separate transactions.
- Evidence: `P/orchestrate/data_operations.py:345-483, 758-777, 913-983, 1369-1376`;
  `P/semantic/cpu_execution.py:632-745`; `P/semantic/claim_lifetime.py:134-213`.
- Preserve: physical-retirement proof before releasing failed attempts; the retained intent as
  the recovery point; no connection held across compute.
- Lead: in long-lived processes hold process-scoped execution resources and let a run borrow
  slots; combine claim with hydrate, and retain with publish behind a savepoint.
- Value medium / burden medium-high.

**F20 — Recognition pays process start, service admission and a document open per page** *(in flux)*
- Principles: H12, H21, H26.
- Work: per page, a new `RecognitionWorker`, an HTTP admission call, a fresh PDFium document
  open (pages load lazily) and a new Python process that imports the client and checks package
  versions. Per request, the release's PDF context is re-resolved and page-level files are
  re-sent and compared, in a separate transaction.
- Evidence: `P/ingest/pdf_recognition.py:470-490, 663-735`; `services/nemotron-parse/worker.py:19-149`;
  `P/semantic/pdf_integrated.py:587-617`; `P/semantic/pdf_transforms.py:888-911, 1136-1211`.
- Preserve: per-page cancellation, durable evidence around each provider call, generation
  pinning. Provider admission (four page workers against four server sequences) is coordinated.
- Lead: one long-lived worker per concurrency slot; resolve the context once per claimed
  operation; publish a page's requests in one transaction.
- Value medium / burden medium.

**F21 — A new Lark Earley grammar is built for every parsed region** *(stable file)*
- Principles: H12, H14.
- Work: `prepared_parser` reads and hashes the grammar file per call and builds a parser whose
  terminals embed the region's absolute offsets. The cache is keyed on region text, so it hits
  only for identical regions.
- Evidence: `P/semantic/constructions/forest.py:59-116`.
- Preserve: ambiguous lexical categories, protected atoms, forest output, time and size bounds.
  The per-call file hash keeps the cache key honest about grammar edits in a long-lived
  process; hoisting it is fine only if the grammar is treated as pinned per process.
- Lead: prepare the grammar once and supply each region's terminals as data, if the pinned
  Lark supports a pre-lexed ambiguous lattice.
- Open premise: that Lark capability; documentation did not settle it.
- Value medium / burden medium-high.

**F22 — Every `ci` invocation imports the whole command registry** *(in flux)*
- Principles: H12, H27, H26.
- Work: `cli/__init__.py` imports all 18 command modules at module level, including
  `cli/model.py`, which pulls the model-change toolchain. Query-custody modules are compiled
  from source in each process because bytecode caching is disabled for them. A lane's static
  import closure counted 123 first-party modules; that count was not independently
  re-established, and the startup time it adds is unmeasured.
- Evidence: `P/cli/__init__.py:9-28`; `P/cli/app.py:62-82`; `P/cli/model.py:40-49`;
  `P/_query_custody.py:137-150`.
- Preserve: the explicit registry contract; `ci reference` generation; source custody. The
  custody list covers about 75 files including core modules most commands import, so narrowing
  custody is a broader change than it sounds.
- Lead: resolve command groups lazily on dispatch and move result types to light leaf modules.
- Value medium-high / burden medium.

**F23 — Test reading verbs re-classify settled receipts in a fresh process each time** *(in flux)*
- Principles: H12, H19, H26.
- Evidence: `P/cli/testing.py:644-698, 756-773`; `scripts/test_receipts.py:744-760, 1153-1160, 2126-2142`.
- Lead: compose projections from the persisted per-lane classification for settled receipts;
  call the supervisor with `--no-sync`; validate pytest arguments inside the lane run.
- Open premise: whether `classification.json` holds enough per-node data.
- Value medium / burden low-medium.

**F24 — `ci model` preview, candidate and deploy each re-prepare the release; each revision stores a full native catalog** *(in flux)*
- Principles: H12, H27, H25.
- Work: three semantic compiles per change with no shared result. There are 285 revisions and
  the versions directory is 1.8 GB; the largest state files are 14.4 MB and 12.5 MB. Admission
  per acquisition is stat-only with cached identities, so that part is cheap.
- Evidence: `P/cli/model.py:1381-1415, 1537, 1875-1890, 2108-2117`;
  `P/semantic/execution_admission.py:247-260`; `semantic_alembic/versions/`.
- Preserve: deploy must refuse when declared sources changed since the candidate; predecessor
  verification of the head; frozen revisions are not rewritten.
- Lead: retain the prepared archive digests with the candidate and recompile only on mismatch.
  Reducing stored history is an operator decision about frozen revisions.
- Value low-medium / burden medium.

### Tier 4 — PDF stage movement and recovery units

**F25 — Every page's assembly, raster and candidate bytes are adopted twice** *(mostly stable files)*
- Principles: H6, H16, H19, H26; DP-10.
- Work: the parent adopts each page's assembly and raster during conversion. After conversion
  `write_record_batches` re-sends every spooled page under the same stream ids, together with
  the candidates, and the database accepts a duplicate only after transfer and comparison. The
  conversion child waits on each page's database writes. No reader of the
  `page/{n}/raster|assembly|candidates` streams was found in Python or head SQL; replay reads
  the local spool.
- Evidence: `P/orchestrate/pdf_streaming.py:224-297, 328-344`;
  `P/ingest/pdf_streaming.py:177-238, 505-527`; `P/ingest/pdf_worker.py:81-84, 143-150`.
- Preserve: page memory release only after durable spool custody; the queryable candidate
  companion.
- Lead: adopt each page artifact once; store candidates once; have the owner decide whether
  rasters and assemblies need database custody, given no reader was found.
- Value high / burden low-medium.

**F26 — Each stage publishes a complete copy of the document, then re-validates it by reading it back into a spawned interpreter** *(in flux)*
- Principles: H2, H16, H20, H19; DP-10, DP-23.
- Work: organize changes only hierarchy but re-shreds, re-copies and re-validates every record
  of the book; enrich and integrate do the same. Each publication reads all frozen rows back,
  rebuilds the document through a SQLite store in a new interpreter and re-runs callbacks,
  although the producer validated the same document. Stages also carry the document through
  repeated JSON and pydantic round trips, and the lowering validates each subtree once per
  union choice.
- Evidence: `P/semantic/pdf_publication.py:398-620, 677-914`;
  `P/semantic/pdf_transforms.py:340-493, 1040-1065`;
  `P/orchestrate/pdf_streaming.py:562-626, 636, 737, 896`; `P/semantic/pdf_records.py:118-144, 376`;
  `P/semantic/pdf_contracts.py:197-198`; `P/ingest/pdf_hierarchy.py:140-156`.
- Preserve: freeze the content being certified (DP-19); immutable per-stage publications with
  their own identity; database-side inventory checks. A round-trip check of the lowering has
  real value (DP-23), so this needs an owner decision.
- Lead: derive the access projection and run callbacks in the producer; certify persistence by
  the server-computed frozen digest; keep reconstruct-from-rows as a qualification check or run
  it when the lowering code changes. For stage copies, compare shared content-addressed
  records against running private intermediate stages in one workspace.
- Open premises: whether a per-publication independent oracle is required; which intermediate
  products have consumers other than the next stage.
- Value high / burden medium-high to high.

**F27 — withdrawn.** It restated F20 and F12. The per-page payload-family re-preparation is
folded into F12; the `store_pdf_original` re-resolution happens once per document.

**F28 — Recovery units are too coarse or not repeatable** *(in flux)*
- Principles: H24, H11; DP-19.
- Work: resuming an interrupted capture redoes the whole Docling conversion in a fresh
  directory and succeeds only if every recomputed batch is byte-identical to what was adopted;
  the retained spool is not consulted. Draft stages recompute the draft and then raise when the
  existing build is frozen or published. Recognition republishes every completed page in full
  on resume. Interrupted pages and worker crashes without a result file are retried, but any
  failure the worker records in `result.json`, including a transient HTTP or service error, is
  reused under the same receipts root and recipe (`reuse_failures=True`); the
  repetition-recovery path retries one failure class under an alternate recipe.
- Evidence: `P/orchestrate/pdf_streaming.py:507-522, 679-731`; `P/ingest/pdf_streaming.py:177-238`;
  `P/semantic/pdf_transforms.py:974-1001`; `P/ingest/pdf_recognition.py:678-700`;
  `services/nemotron-parse/worker.py:166-197`.
- Preserve: build fencing and receipts; a frozen build cannot be replaced by different
  content; no silent substitution of a published observation.
- Lead: inspect the build before computing and finish a frozen one through the native path;
  classify recognition failures and reuse only terminal ones; consider the page as the capture
  resume unit using the existing spool restore.
- Open premises: whether GPU output is bit-identical across processes; the intended recovery
  route for recorded transient failures.
- Value high / burden low for the draft-stage and recognition parts, high for page-level
  capture resume.

### Tier 5 — evaluation and remaining items

**F29 — Grading re-binds the whole reference set twice per candidate** *(in flux)*
- Principles: H12, H19, H9, H10; FP-07.
- Work: `whole_reading_correct` calls `align_records` twice per candidate with the full
  reference rows; each call re-validates record declarations, recomputes the reference
  contract and re-binds every reference record. The grade plan scans a whole index relation
  per selection although an indexed `rows_for` exists, and re-acquires the same native source
  per question. Native reference scoring re-authenticates the whole annotation product per case.
- Evidence: `P/evaluate/record_alignment.py:228-256, 449-499, 655-668`;
  `P/evaluate/declared_record_policy.py:1224-1311, 1423-1436, 1988-2018`;
  `P/evaluate/selected_references.py:256-402, 647-684`.
- Preserve: refusal of an invalid candidate; one-to-one accounting; independence of the three
  reference passes; every custody check.
- Lead: split alignment into a reference stage computed once per question and a candidate
  stage; use the indexed lookup; acquire each source once per plan.
- Value high / burden medium.

**F30 — Trust-scope rows are locked exclusively by every settlement** *(in flux)*
- Principles: H23, H25.
- Work: settlement and completion take `FOR UPDATE` on each scope of the closure; renewal
  deliberately takes `FOR SHARE`. The exclusive lock blocks pinned readers on the same
  (project, source) scope as well as other settlements.
- Evidence: `sql/data_operations.sql:180-225, 1617-1631`.
- Lead: settlements take a share lock; only revocation takes the exclusive lock.
- Open premise: whether exclusivity among settlements protects a reader-cut invariant.
- Value low-medium now / burden low.

**F31 — General opportunities (no principle violation claimed)**
- Unreferenced production code: `P/orchestrate/liveness.py` and `P/evaluate/task_semantics.py`
  have no importer (dynamic use not excluded); `gliner_extract` is reached only from
  `gliner_extract_members`, which has no caller. `HostedPipeline.pipe` has static callers but
  production uses the native-docs path.
- `read_packet` returns each input in two forms.
  `P/semantic/data_operation_external.py:202-221`. Returning `exact_json` as text beside
  structured content is the MCP compatibility practice and is not counted here.
- `describe_database` opens two engines plus a third connection for one request;
  `compare_companion_exports` verifies each export twice.
  `P/serve/database_description.py:173-191`; `P/serve/companion_export.py:490-507`.
- Two lane observations were not independently checked: static staging metadata rebuilt per
  page and batch (`P/semantic/pdf_staging.py:54-126`), and repeated encode, parse and digest
  per native transport exchange (`P/methods/characterization_resources.py:345-361, 574-649`).

## 5. Suggested order of attention

A ranking of leads by value against burden. It is not a plan.

1. **Low burden, high value, local:** F08 (indexes), F04 memo, F16 (session engine), F03 read
   paths, F01 (prepared view), F02, F25 (single adoption), the draft-stage and recognition
   parts of F28.
2. **Medium burden, high value:** F05–F07 (validity, binding, pinned read), F11 (capacity
   coupling), F29 (grading), F09 (a)–(c), F12, F15, F17.
3. **Needs an owner decision first:** F13 (batch form against native scalar contracts), F26
   (where publication assurance sits; stage copies), F10 (set-form native interface), F19
   (process-scoped execution resources), F28 capture resume, F03 execution boundary.
4. **Operator loop:** F22, F23, F24.

## 6. Considered and rejected

Kept so later reviews do not re-raise them: per-CLI-process engine creation; settlement round
trips taken alone; `check_connection` on pool checkout; SQLAlchemy `NullPool` over the psycopg
pool; the renewal thread's dedicated connection; late hydration and the retain→publish split
taken alone (a real recovery point); `check_active` call volume; `canonical_bytes` call volume
taken alone; grading as one CPU call per population; `compile_data_operations` (once per
release, memoized); manifest rewrites per managed operation; `ci check` running steps in
sequence; companion export's shape; `RichRelationKernel`; recognition provider admission;
model and tokenizer load lifetime within a host generation; the math grammar cache; HanLP's
sentence cap; `corpus.conf` settings; `exact_json` mirrored as text.

## 7. Coverage and open premises

| Lane | Read closely | Not inspected |
|---|---|---|
| Database and SQL | `core/db/store.py`, `semantic/runtime.py`, release loading, the support, binding, attach, claim, retain, publish and read functions, PDF owner fence, MCP engine factories, physical model | bodies of the rich, structural, contextual, record-fit and operation-event validators; PDF validation SQL; `record_publication.sql`, `closure.sql`; `target_installation.py`, `model_deployment.py` |
| Declared operations | executor, demand planner, storage invoke, wire assembly, binding heads, hydration, claim lifetime, CPU and stream paths, ports | `data_operation_projections.py` and a dozen smaller `data_operation_*` modules, `declared_*.py`, `python_operation_sources.py` body, `core/keys.py` body |
| PDF pipeline | streaming, worker, recognition, transforms, publication, record reader, staging, capture | Docling internals, `organize`, most reconciliation matching, `archive_*`, `artifact_*`, most `source_*` and `visual_*` |
| Model methods | native host, lanes and coalescing, GLiNER, M1, learned primary runner, contextual encoder and layer, HanLP, CPU execution | `methods/math/*` except the parser cache, `methods/llm/*`, PM2 dispatch and result bodies, `methods/learned_primary.py` bodies, structural and predicate kernels |
| Products and evaluation | construction kernel and layers, formal readings, record alignment and policy, selected references, rich rule evaluation and consolidation | `constructions/evaluation.py`, `math_scope`, `named*`, formal, scientific, structural and definition kernel bodies, most of `evaluate/` beyond alignment and policy |
| Serving, core, `ci` | MCP servers and tools, rich and demand reads, exports, source search, external session, `ci` registry, managed results, test orchestration | `schema/*` bodies, core codecs, `cli/output.py`, `status.py`, `result_inspection.py` bodies |

Open premises that set magnitude or decide a lead. None was probed.

1. Items, pieces, blocks and sentences per source view for the benchmark book (F01, F02).
2. Paths versus distinct nodes in the support graph, and planner behaviour in the binding
   universe (F05, F06).
3. Whether the operator overrides the execution policy defaults (F11).
4. Batch-composition invariance of GLiNER and the sentence encoder (F13).
5. Trust model for retained product bodies read back by consumers (F09 d).
6. Whether a per-publication reconstruct-from-rows oracle is required assurance (F26).
7. GPU determinism of Docling output across processes (F28).
8. Whether Lark's Earley parser accepts a pre-lexed ambiguous lattice (F21).
9. Whether `open_release` serves every current `load_release` read consumer (F03).

## 8. Independent challenge

A fresh design reviewer opened the cited source for every finding at the same baseline, with
the brief to refute. Result: none refuted; 22 confirmed as written; 15 confirmed with a
correction; 2 weakened; 2 general items not checked. The text above incorporates every
correction. The material ones:

- **F03:** the execution path re-derives once per run and documents that as a deliberate
  boundary; the finding now targets read and external paths.
- **F04:** Python and SQL validate against different authorities, so the checks are not one
  check repeated; unsupported counts and sizes removed; the lead is reduced to the memo, with
  check removal a separate decision.
- **F05:** validity is boundary-relative, which limits what a maintained record can cover.
- **F07:** caller authorization added to what must be preserved; the read also writes.
- **F13:** native admission pins the scalar form, raising the burden.
- **F16:** re-keying the release cache was withdrawn as unsafe; a session engine suffices.
- **F09 (g), F21:** the per-request and per-call hashing has a drift-detection purpose, now
  stated.
- **F28:** "can never be retried" corrected to the failure classes that are reused.
- **F27:** withdrawn. **F31:** the `exact_json` duplicate withdrawn.
- Section 2 was regrouped into six causes, and the A4 table gained three rows and lost two
  overstatements.

Checked by the coordinator directly, before the challenge: F01, F03, F04, F05, F08, F11, F16,
F21, F22, F25, F28, F29 and F09 (c).

## 9. Relation to existing owners

Cross-referenced after the findings were fixed, for annotation only. Matches are mostly by
concept: the function and table names above appear in almost no document. ADR status is taken
from each record's frontmatter; `docs/adr/README.md` lists several of the same records as
Proposed, and that disagreement was not resolved here.

| Finding | Existing owner or diagnosis |
|---|---|
| F01, F02 | DA-043 describes the same cause class in consolidation; production-efficiency plan F04–F06 cover indexed source resolution in other kernels. The sites named here have no owner. |
| F03, F18 | DA-042; book-efficiency plan O01 and RC03; production-efficiency plan F09 (PE-11). ADR-0083 scopes verified preparation to one invocation. |
| F04 | ADR-0106 owns wire validation. DDO-SI-29 memoizes a related immutable model while keeping per-call validation. No owner for the uncached protocol assembly. |
| F05, F06, F07 | ADR-0093 and ADR-0110 own support validity and trust scopes. DDO-SI-23 and the STATUS checkpoint record a narrower statement-local improvement, with broader consumers open. |
| F08 | The DDO products-and-support design states that indexes cover these access patterns, and the 2026-11-12 DDO review judged A4 satisfied "via indexed set operations". No finding records the gap. |
| F09 | (d) DA-033; (e) DA-004; (f) DA-058 for one provider; (g) DA-028 states the custody guarantee. (b) has no owner. |
| F10, F12, F14, F15, F20, F23, F25 | No existing owner found. |
| F11 | ADR-0084 and D6 ("admission precedes hydration"); DDO-CA-13 and book-efficiency O03 touch the same arithmetic. |
| F13 | ADR-0084, ADR-0085 and ADR-0114; book-efficiency O05 and BEP-06. |
| F16 | D9 states that the MCP lifespan holds its purpose pools; the read tools at this baseline do not. PE-11 keys the release cache by engine. |
| F17 | DA-035 loosely. No owner for the per-page index rebuild. |
| F19 | ADR-0083 (invocation scope), ADR-0094. |
| F21 | Production-efficiency plan F01 is open on the same recognizer cost. |
| F22 | Production-efficiency plan F10 is recorded as closed for PE-11/12, and the test-system plan W2/TS-06 describes the same eager import. At this baseline the registry import is eager, so that closure and this finding disagree. |
| F24 | The DDO plan forbids rewriting frozen predecessors. No owner for the three compiles. |
| F26 | ADR-0045 and the D3 frozen-receipt identity own validation over stored bytes. |
| F28 | ADR-0094, ADR-0099; DDO-SI-26; the PDF pipeline plans state that failures are reused distinctly. DA-058. |
| F29 | DDO-SI-24 covers reference authoring; `align_records` has no owner. |
| F30 | ADR-0093. |
| F31 | A plan-improvement review already records `liveness.py` for retirement. |

## 10. Rules a lead would change

Listed per the binding; each changes only after the operator confirms it in plan creation.

- `review#RC01` — F04, if a validation check is removed: ADR-0106 (authoritative schema
  validation at native admission).
- `review#RC02` — F05, F07, F30: ADR-0093 and ADR-0110 (support validity, trust-scope locking
  and the complete protected dependency closure).
- `review#RC03` — F11: ADR-0084 and D6 ("admission precedes hydration"), if reservations are
  sized after hydration.
- `review#RC04` — F13: ADR-0114, ADR-0084 and ADR-0085 (per-target vectors, batch receipts and
  numerical semantics), plus the native scalar-form contracts.
- `review#RC05` — F19, and F03 if a verified basis is carried beyond one invocation: ADR-0083.
- `review#RC06` — F26: ADR-0045 and the D3 frozen validation receipt.
- `review#RC07` — F28: the recorded-failure reuse rule in the PDF pipeline plans; ADR-0094.
- `review#RC08` — F09 (g): the query-custody guarantee recorded under DA-028.

The remaining leads (F01, F02, F08, F10, F12, F14–F18, F20–F25, F29, F31) change no recorded
rule that this pass found.

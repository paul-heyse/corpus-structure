# Lane: identity, reuse and execution findings at `5139eaba3`

**Interface-checked by source inspection, 2026-11-18.** Source: frozen snapshot `snap6/` of
`5139eaba3`. Paths omit `snap6/python/corpus-structure/src/corpus_structure/` unless they start
with `docs/` or `target_alembic/`. History from read-only `git log/diff d78c98765..5139eaba3`.
Nothing was run against the project, its tests or any database; no claim is Tested or Measured.
The only executed code was read-only text analysis (stdlib Python over `git show` output and the
snapshot), described where a count depends on it.

**Read fully:** `semantic/data_operation_storage.py:30–260, 536–576, 700–724, 1080–1145,
1555–1575`; `semantic/native_admission_release.py` (all 859 lines); `semantic/pdf_lowering.py:1–110`;
`semantic/data_operation_projections.py:2062–2192` and the diff of its watermark hunks;
`semantic/data_operation_admission.py:200–400`; `orchestrate/data_operations.py:690–790`;
`semantic/cpu_execution.py:145–304, 695–800`; `semantic/execution_admission.py:182–213`; the
full diffs of b294ab4e2, 5c5443d16, 188ec73c2, 7fdcd7643 and of storage, wire, characterization,
formal, prepare, demand_results, execution_admission and releases in the range.
**Sampled:** capture helpers (`data_operation_binding_native.py:30–56`,
`operation_event_native.py:220–241`, `data_operation_wire_native.py`, `data_operation_source_native.py:16–50`,
`original_document_contracts.py:137–160`, `data_operation_visual_read.py:89–112`,
`pdf_source_search.py:29–120`, `source_value_native.py:70–80`), `data_completion_settlement_native.py:486–545, 628–695`,
`data_derivation_native.py:372–400`, `companion_projection.py:562–640`, `file_custody.py`,
`data_operation_cpu.py:180–215`, `data_operation_cpu_basis.py` outline, `target_installation.py:760–830`,
`native_admission.py:42–110`, `demand_results.py:55–105`.
**Not read:** `serve/*` consumers beyond key lines; `schema/model_change.py` (no commit in range);
the "four consumers page the frontier twice" sub-point of DA-075; change impact; established validity.

## 1. Findings

| ID | Status at `5139eaba3` | Changing commits |
|---|---|---|
| DA-068 | **Stands, wider; first established instance of a digest-only native revision** | capture: 32ec30618, 1556c7638, 782f9f4df, fc6df4742, a463488ca, b834ddfdb, 80aea868f (11 commits to the storage module); seal: b294ab4e2 (no narrowing) |
| DA-069 | **Stands**; one hand-added whole module joined a view operation's sources | 67a6e7a51, 590b67b7a, 1fab40234 (characterization_ports); 32ec30618 |
| DA-075 | **Stands, unchanged** | none to key sites |
| DA-076 | **Stands, unchanged** | none to `_query_custody.py`, `serve/rich_queries.py`, `semantic/demand_queries.py` |
| DA-077 | **Stands, unchanged** (not in this brief's ten, checked once: no commit to `scientific_evidence.py` or `rich_policy_binding.py`) | none |
| DA-078 | **Stands; changed footprint** (a second, role-matched component was added; the operation-granular component remains) | 6d699ab46, 110e8aa1e |
| DA-082 | **Stands, unchanged list; the too-narrow half was exercised** | none to `pdf_lowering.py` |
| DA-083 | **Stands, unchanged**; the capture still has no holder | storage commits above changed content, not call structure |
| DA-033 | **Changed footprint (fully generated); substance stands** | 9364a5b88 (template retired), 06102f3dd, de5792052, 920f1b746, 08284dc6f, 1b643e7ed, 46cda0b30 |
| DA-058 | **Stands, unchanged** (one check: no commit to `semantic/visual_requests.py` or `ingest/pdf_chandra.py`) | none |

### DA-068 — kernel digest over the whole native capture (Q1)

*What the digest covers now (established).* `native_source_digest()` hashes every `native/*`
artifact (`semantic/data_operation_storage.py:712–722`) of `native_protocol_sources()`
(`:48–575`). Counted by listing every Python-module read inside that function and the nine
capture helpers it splices in (`with_name("…py").read_bytes()`, `Path(__file__).read_bytes()`,
the seven program modules at `:143–189`, the twelve binding modules at
`data_operation_binding_native.py:39–52`, the six Python renderer files of `_RENDERER_FILES`
at `pdf_source_search.py:29–37`), then de-duplicating file paths: **99 distinct Python modules**
(storage 61 read sites, binding 13, search 7, wire 4, operation-event 3, source 3, original
documents 3, visual read 3, projections 1, source values 1). By the same method at `d78c98765`:
about 95. The published "75 to 85" was an undercount. Distinct `"native/*.py"` literal names in
the ten capture modules rose from 70 to 74 (`git grep` at each commit): added
`contextual-neighborhood.py`, `original-document-native.py`, `source-admission-native.py`,
`visual-read-native.py`. Model files: the physical closure (five imported YAML files reached
from `physical.yaml` — counted by following `imports:` — plus referenced value-set sources, among
them `data-operation-native.yaml`, `:124–135`), the LinkML types (`:128`), three logical files
(`:41`), and `section-text-recipe.json` (renderer list). Libraries: six, unchanged — pglast,
sqlalchemy, linkml-runtime (`:207–214`), networkx (`:545–552`), docling-core and docling
(`pdf_source_search.py:63`). About 46 generator invocations per build (37 inside the function,
counted with `grep -oE '[a-z_]+_sql\('`, against 36 at `d78c98765`; the rest in helpers).

One positive change: eight generators now receive the captured `target_metadata`
(`:251, 259, 267, 275, 283, 314, 323, 339, 356`), so their SQL derives from the captured physical
closure rather than from import-time module metadata. That improves hermeticity (CI-11); it does
not narrow the key.

*The seven uses (established, current sites).* (1) spliced at `:815` and compared to the checkout
at `:1137–1142`; (2) release admission: `native_admission_release.py:515–531` and
`data_operation_compiler_native.py:1055–1093`, `data_operation_read_native.py:208`; (3) read
stamp `demand_result_native.py:223`, presence `data_read_boundary_native.py:98`; (4) completion
seal `data_completion_settlement_native.py:489–499`, compared at publication
`data_derivation_native.py:382–394`; (5) receipt `data_derivation_native.py:614`, replay gate
`data_completion_settlement_native.py:671`, routine still `stable=True` (`:695`), seven
validators still call it (`contextual_admission_native.py:752`, `definition_admission_native.py:427`,
`operation_event_native.py:1366`, `record_grade_native.py:720`,
`record_policy_completion_native.py:1658`, `artifact_admission_native.py:229`,
`rich_admission_native.py:844`); (6) native operation `behavior` (`data_operation_storage.py:993`);
(7) watermark (`data_operation_projections.py:2189`).

*What the N27 "shared completion digest" is (established).* b294ab4e2 factors one seal
builder, `_completion_seal_value` (`data_completion_settlement_native.py:489–499`), used by both
`ops.ddo_completion_seal` (`:519–541`) and the retain-intent insert (`:1042`), and computes the
completion's `ddo_digest` once into a local reused for the stored `payload_digest` and the seal
(`:1028–1048` region). The seal's `kernel` field is still `_KERNEL` = the whole digest. 956661772
only freezes that change as native revision N27. **Nothing seals or gates against a narrower
identity.** Publication still recomputes the seal, digesting the content again
(`data_derivation_native.py:383–385`).

*What an edit to one generator (or any captured) module forces today.* Unchanged chain from the
published text (refusal of acquisition until a native revision is authored and deployed, new
release id, replay of every older receipt in seven families, reacquired reads, every watermark
advances, PDF refusal if also on the lowering list). **New evidence of the chain in the range
(established):** I compared consecutive frozen revisions
`target_alembic/versions/semantic_ddo_pe_nNN_native.json` (N14–N29; 585 `desired` objects each,
about 9 MB each), statements per identity, masking 64-hex strings. N29 (d2ffba42e) changed nine
objects and **none beyond 64-hex literals**: the descriptor, read presence, read result,
publication, completion seal, episode correspondence, retain intent, the PDF search pin and the
execution-contract descriptor — exactly the kernel-stamp sites. The Python changes between the
N28 and N29 freezes include 477c82762, which added `matches_occurrence_extent` to
`semantic/native_source_view.py` for construction validation; that file is captured whole as a
PDF search *renderer* input (`pdf_source_search.py:34`), so the renderer digest and the kernel
digest moved. A Python-only construction helper therefore produced a full native revision,
rollback replay and stage deployment, and, after deployment, the replay of every older receipt
on validity evaluation. (N21 and N25 also changed only 64-hex literals, but only in
`execution_contract_descriptor`, not the kernel stamps.) The masking is a heuristic: a genuine
change to another 64-hex literal would be hidden; I did not map each of the 19 substitutions.

*Consequence now.* As published, with frequency no longer hypothetical: one of sixteen native
revisions in this range existed only to restamp the kernel digest. *Contrary evidence:* capture
remains fail-closed and attributable; `_captured`'s required-set and projection-physical checks
stand (`:577–700`); the release already carries its own native digest
(`native_digest_from_dependencies`, `prepare.py:1031, 1385`), so a carried identity exists.
*Uncertainty:* replay volume and the cost of one replay are not measured.

### DA-083 — no holder for the native capture (Q2)

Established. `require_data_operation_native` (`data_operation_storage.py:1127–1142`) still uses
`prepared` only to call `require_native_execution`, and calls `native_source_digest()` twice
(`:1139`, `:1142`), each rebuilding the whole capture from the checkout. It does not consult the
digest the prepared release carries (`prepare.py:1385`), although the SQL guard already compares
that archived digest with the installed descriptor (`native_admission_release.py:531`); the
Python check's only additional content is checkout-versus-descriptor. Rebuilds per call, by call
path:

| Call | Full captures | Site |
|---|---|---|
| Python or prepared port acquisition | 2 | `data_operation_admission.py:285` via `orchestrate/data_operations.py:718, 754` |
| Cached-port recheck | 2 | `data_operation_admission.py:354` via `orchestrate/data_operations.py:784` |
| Publication-port acquisition | 2 | `data_operation_admission.py:390` |
| Definition admission | 3 | `data_operation_storage.py:1561, 1571` |
| Preparation, regeneration, native products, candidate definitions, demand export | 1 each | `data_operation_preparation.py:261`; `primary_operations.py:403`; `regeneration.py:331`; `native_products.py:110`; `data_operation_storage.py:1857/1865`; `serve/demand_export.py:281` |
| Model-change preview | at least 2 (unchanged file) | `schema/model_change.py` (no commit in range) |

No holder, memo or custody was added: no decorator on `native_protocol_sources` or
`native_source_digest`; the only new holders in the range are elsewhere (§3). One small change
lowers acquisition count: the dispatch loop now acquires a port for the first ready item only when
the operation is a batch (`orchestrate/data_operations.py:1765–1777`, 2619d5aef), and
reconciliation no longer builds a context. The per-execution acquisition and recheck paths are
unchanged. Each rebuild now runs larger generators (structural, rich, record-policy and
product admission generators grew by about 1,000–2,500 lines each), so the per-rebuild cost
probably rose (inferred, not timed). The custody gap stands: SQL comes from imported generator
objects while module bytes are read fresh (`:186–188`).

### DA-082 — `LOWERING_FILES` (Q3)

Established. `semantic/pdf_lowering.py` has no commit in the range. The list still holds **70**
entries (64 Python modules, five model YAML files, one JSON schema; counted from the tuple at
`:33–104`), with **14** library names (`:15–30`). No completeness check exists. Nothing joined or
left. Static one-level check (method: parse every listed Python file with `ast`, collect
first-party `from … import` targets including lazy imports, keep existing files not on the
list): **30** first-party modules are imported by listed modules and unlisted, both at
`d78c98765` and now; among them `semantic/pdf_spool_native.py`, `semantic/pdf_domain.py` (nine
listed importers), `semantic/native_objects.py` (13), `semantic/pdf_effect_contract.py`,
`semantic/pdf_observations.py`, `semantic/visual_evidence.py`, `semantic/published_document.py`.
Not every one shapes lowering; the figure is an upper bound on the gap one level deep.

The too-narrow half was exercised in the range: unlisted `pdf_spool_native.py` changed
+605/−140 (af01f7776), `published_document.py` +221/−143, `native_objects.py` +25 and
`native_catalog.py` +89 without moving the lowering identity. The too-broad half was exercised
too: listed shared infrastructure `native_program.py` and `native_sql_body.py` changed (two
commits each), moving the lowering identity and the kernel digest together.

### DA-075 and DA-076 (Q4)

No commit touched `semantic/selected_query_cache.py`, `semantic/demand_queries.py`,
`_query_custody.py`, `serve/rich_queries.py`, `serve/contribution_facets.py`,
`serve/interpretations.py`, `serve/structural_products.py`, `serve/identity_exclusion_comparison.py`
or `cli/selected_results.py`. `semantic/demand_results.py` changed only in
`verify_detached_result` (426f64319, 32ec30618); `CutSelection.identity` is unchanged
(`demand_results.py:64–102`), and the read instance is still `read:` plus
`gen_random_uuid()` (`demand_result_native.py:195`). A new boundary field,
`public_disclosure` (ed410b80f), is added to the read boundary; whether it enters the cut pins
was not traced. Both **stand, unchanged**. For DA-076 the ordinary-edit case recurred: unlisted
answer-path modules `semantic/archive_reader.py` (3ba5daa84), `semantic/releases.py` and
`semantic/data_operation_protocol.py` changed. A further overlap appeared: listed
`semantic/native_source_view.py` is also a kernel renderer input (DA-068 above), so the one
N29-causing edit invalidated served cursors and the kernel together.

### DA-078 — readiness watermark

Established. `_inputs_watermarks` (`data_operation_projections.py:2062–2192`) keeps the
transitive-prerequisite component keyed by operation and `original_source` (`:2069–2110`), the
populations, every visible original admission, source sets, kernel digest and whole trust
snapshot (`:2184–2191`). 6d699ab46 added `_unconstrained_watermark_uses` (`:1919–2059`): for
selected operations with no dependencies, it adds same-demand fulfilled uses whose outputs match
an input role (`_watermark_role_matches`, `:1781–1809`) and pass disclosure and access checks.
This is the first watermark component using declared roles for local wakes (pinned uses already
did). It adds to the watermark, so it advances on more events, not fewer. **Consequence:**
unchanged for the one-source workload, and every kernel restamp such as N29 still advances
every watermark. The new component joins every fulfilled use of the demand × roles × outputs ×
members per dependency-free obligation, evaluating access functions per candidate; cost grows
with the demand's use count (inferred). *Contrary:* still the plan's specification; binding
remains the authority. Skip site unchanged (`data_operation_demands.py:736`).

### DA-033 — release-content re-proof (Q5)

Changed footprint; substance stands. `data.require_execution_release` is now fully generated by
`admission_kernel` (`native_admission_release.py:343–409`); `sql/admission.sql` is gone
(9364a5b88). The ~800 added lines are a predicate-for-predicate translation of the retired
template plus generated catalog checks in three new modules
(`native_admission_functions.py`, `native_admission_principals.py`, `native_admission_tables.py`).
Per call (each acquisition, recheck, publication-port acquisition, definition admission) it still:
checks finalization and then performs `sem.require_execution_projection` (`:41–56`), which
re-parses the archive and performs `sem.require_archive_bytes`
(`archive_projection_native.py:264`; byte hashing now generated in `closure_native.py:316–380`);
decodes `release.prepared_bytes` to scan diagnostics (`:438–459`); re-hashes every authored-SQL
input and its admission and decodes the admission JSON (`:461–496`); hashes
`data_operations.json` and decodes the archived native projection (`:513–534`); reads every
inference rule (`:629–808`); decodes `manifest_bytes` (`:835`); and runs
`sem.require_scientific_layout` (`:857`). It then records the deployment-admission receipt only
if absent (`:59–97`); the receipt does not short-circuit any re-proof. Nothing new is carried.
Per-binding re-parse is unchanged (`binding_admission_native.py`, `population_acquisition_native.py`:
no commits). Archive publication also performs both proofs (`archive_native.py:468–469`).
*Contrary:* the catalog half is a live drift guard; the trust decision (DA-029) is open as before.

### DA-069

Stands. The construction and formal asset lists are unchanged (`characterization_ports.py:48–194`,
shifted one line by an import; `formal_products.py:689–757`, shifted by an import). New in the
range: `enriched_document_products.py`, already a whole-file `view` asset (`:78`) and in
execution custody (`:206`), is now also appended by hand as a `PythonSource` of the composition
view (`characterization_ports.py:1144–1155`, 67a6e7a51), so its code enters the slice input as
well. The same fact ("which code determines the view") is now stated three times. Whether the
slicer slices it or folds it whole was not traced. `FormalEvidenceProduct.semantic_id`
became a `cached_property` (`formal_products.py:150`), a sound per-object memo.

### CPU execution (Q6)

Established. 5c5443d16 removed `_WORKER_REQUEST`; `_dispatch` now binds
`partial(_worker_active, slot, generation)` per invocation and passes it down
(`cpu_execution.py:293–299`, `_dispatch` around `:359`). Remaining module state, all per worker
process: `_WORKER_RELEASES` (`:226`; cleared at init `:284`; filled by
`_worker_release` keyed by a digest of the capsule reference, `:150–174`, with no bound in the
worker's lifetime), `_WORKER_STOP`, `_WORKER_CANCELLATION`, `_WORKER_NATIVE_THREADS` (set once
by `_initialize`, `:266–290`), `_WORKER_NATIVE_RUNTIME` (`:250`, mutable limiter and observed
pools, re-applied per call). `SIGINT` is ignored in workers (`:272`, 50aa17854). Coordinator
state is instance-held (`:695–713`). `data_operation_cpu_basis.py` holds only version constants
(`:27–29`); its +884 lines generate the native CPU-basis SQL from typed models (782f9f4df) while
the Python input-basis identity is unchanged (`:63–192, 330–460`). Sound; no shared mutable
request state remains.

## 2. Identity inventory (replaces the published table)

Basis: "model" = from model declarations or the compiled model; "content" = from supplied bytes
without a hand list; "hand" = membership fixed by a hand-written list. Mark = since `d78c98765`.

| # | Identity | Owner | Covers | Basis | Consumers | On mismatch | Mark |
|---|---|---|---|---|---|---|---|
| 1 | Native kernel digest | `semantic/data_operation_storage.py:712–722` | 99 Python modules, ~46 programs' SQL, physical closure, LinkML types, three logical YAML, renderer recipe, six library versions | hand (enumerated in code, four nested lists) | descriptor check, release admission, read stamp, seal, receipt and replay gate, operation `behavior`, watermark | refuse acquisition; reacquire; replay; re-bind | changed (+4 modules; captured metadata) |
| 2 | Native lowering digest | `:141, 817` | bytes of generated `compiler.sql` | content | demand authority and intent programs | not traced | unchanged |
| 3 | Release id | `semantic/prepare.py:986` | manifest over root, model, profile, libraries, every source and dependency digest (native capture, PDF lowering contract) | content | everything release-keyed | prepare and admit again | unchanged |
| 4 | Release-carried native digest | `prepare.py:1031, 1385` (`native_digest_from_dependencies`, storage `:1080`) | digest of the capture archived as dependencies | content | archived definitions projection; SQL admission `native_admission_release.py:531` | refuse admission | unchanged (not previously listed) |
| 5 | Kind, definition, eligibility, implementation-slice, recipe fingerprints | `semantic/data_operation_identity.py`; `data_operation_compilation.py` | compiled model records, sliced sources, boundary digests | model (+ boundaries) | completion revision equality; `_inspect_execution_identity` (`data_operation_admission.py:324–347`) | refuse | unchanged |
| 6 | Opaque boundary and operation-source assets | `characterization_ports.py:48–194, 1144–1155`; `formal_products.py:677–757`; `rich_invocations.py:15–70` | whole files, model YAML, library versions; rich uses an AST projection | hand | implementation slice, recipe (DA-069) | prior derivations not reusable | changed (composition module also a slice source) |
| 7 | Port generator custody | `semantic/data_operation_artifacts.py:22–39, 73–81` | eight generator modules | hand | release dependencies; compile refuses on drift | refuse | unchanged |
| 8 | Python port identity | `data_operation_ports.py:1086`; `data_operation_admission.py:22, 293–321` | model, sources, schema, declarations, contracts; runtime-retained digests | model + content | acquisition, cached-port authorize | refuse | unchanged |
| 9 | Prepared capability identity | `data_operation_admission.py:240–265` | port identity, runtime, asset and boundary digests | model + content | prepared factory `authorize` | refuse | unchanged |
| 10 | Runtime artifact and attestation | `semantic/data_operation_runtime.py:88–120, 180–213` | Python version, executable inputs; release, profile, observation | content | native manifest and archive digests (`data_operation_admission.py:343–347`) | refuse | unchanged |
| 11 | Native selection asset custody | `semantic/data_operation_preparation.py:291–326` (188ec73c2) | declared asset population with path, digest and stat receipts, verified through file custody | content | primary-profile acquisition | refuse | new |
| 12 | PDF lowering contract | `semantic/pdf_lowering.py:13–104, 168–256` | 70 listed files, boundary sources, generated schemas and codecs, 14 libraries | hand (DA-082) | release, producer contract, streaming, oracle, receipt `lowering_identity` | refuse ("restart" or "differs") | unchanged |
| 13 | PDF search renderer and pin | `semantic/pdf_source_search.py:29–37, 61–118` | six whole Python files and the recipe JSON, docling versions, configuration | hand | search contract, `ddo_pdf_search_pin`, kernel digest | refuse; re-pin | unchanged (not previously listed) |
| 14 | Served-read implementation | `serve/rich_queries.py:71–105`; `_query_custody.py:17–135`; `semantic/demand_queries.py:117–124` | listed module digests, nine libraries, request schema | hand (DA-076) | cursors, `resource_handle`, cache keys | refuse resume; restart | unchanged |
| 15 | Cut identity | `semantic/demand_results.py:64–102` | every pin incl. read instance, snapshot, clock | content | cursors, `expected_cut`, cache keys (DA-075) | refuse continuation | unchanged |
| 16 | Read kernel pin | `demand_result_native.py:223`; `data_read_boundary_native.py:98` | kernel digest at acquisition | as #1 | read presence | reacquire | unchanged |
| 17 | Semantic request key and reuse | `binding_admission_native.py:213`; `request_attachment_native.py:1254–1317` | request meaning without release or runtime; unleased equivalent work in an inactive capture may now be replaced by the active release's generation | model | request reuse across releases | new generation | changed (7fdcd7643) |
| 18 | Inputs watermark | `data_operation_projections.py:2062–2192` | transitive prerequisites by source; role-matched local uses; populations, originals, source sets, trust, kernel | model, operation-granular plus one role-granular part | planner skip `data_operation_demands.py:736` | re-bind | changed (6d699ab46) |
| 19 | Completion seal | `data_completion_settlement_native.py:489–541, 1042`; check `data_derivation_native.py:382–394` | kernel, request, generation, release, recipe, runtime, payload digest, trust | mixed | publication battery skip | run battery | changed (shared builder; no narrowing) |
| 20 | Receipt validating kernel and replay gate | `data_derivation_native.py:614`; `data_completion_settlement_native.py:633–695` | kernel at publication | as #1 | seven family validators | replay, unrecorded (`stable`) | unchanged |
| 21 | CPU input basis and authority reply digests | `semantic/data_operation_cpu_basis.py:63–192, 330–460`; native `:462–1150` | selected inputs, roles, positions, values | model + content | CPU authority conclusions, batch members | refuse | unchanged identity; native side regenerated (782f9f4df) |
| 22 | Physical id; deployment-admission receipt; frozen expectation | `schema/physical.py:142–151`; `native_admission_release.py:59–97`; `execution_admission.py:121–140` (body fingerprints via `native_catalog.function_body_fingerprints`) | physical closure; descriptor bytes; function body fingerprints and revision file digest with stat | content | admission, catalog guard | refuse | changed (generated, 1b643e7ed, 9364a5b88) |
| 23 | CHECK-contract digest for prerequisite recreation | `semantic/target_installation.py:781–787` | `physical_checks_source_digest` of retained vs current admission fields | content | native authoring of prerequisite recreation | refuse authoring | new (65ee94886, 1a290484d, 82b02e589) |
| 24 | Wire contract digest | `semantic/data_operation_wire.py:41–60, 550`; checked per call `data_operation_storage.py:1120` | protocol YAML or captured protocol | content | every native invocation envelope | refuse | unchanged |
| 25 | Scientific policy | `semantic/scientific_evidence.py:192–255`; `rich_policy_binding.py:22–30` | hand description of the kernel | hand (DA-077) | release check, rich context | refuse | unchanged |
| 26 | Model-change compilation and generator fingerprints | `schema/model_change.py:313–440, 1066–1077` | whole package tree, libraries, tools, HEAD | content (whole tree) | candidate checks | "prepare a fresh preview" | unchanged |
| 27 | Source-migration identities | `schema/source_migrations.py:168–198` | every file under `semantic/` and `model/semantic/` + libraries | content (whole tree) | `check_source_migration` | refuse | unchanged |
| 28 | File custody; query custody | `semantic/file_custody.py:20–137`; `_query_custody.py:136–260` | path digest with stat identity; module bytes at import | content | lowering, model and selection assets, CPU call assets, served reads | refuse, restart | unchanged (more consumers) |
| 29 | Archive and capsule identity | `semantic/releases.py:81–90, 451–455`; `cpu_execution.py:150–200, 783–800` | archive bytes digest and format; capsule digest and release id | content | release open, CPU transfer | refuse | unchanged |

Of 29, rows 5, 8, 9, 17, 18 and 21 derive membership from model declarations; rows 1, 6, 7,
12, 13, 14 and 25 are hand-kept; rows 3, 26 and 27 are whole-content and over-broad by
construction. Rows 1, 12, 13 and 14 overlap on shared files (`native_program.py`,
`native_source_view.py`, `identity.py`, `metadata.py`, `schema/physical.py`).

## 3. Cache and prepared-state inventory (production; replaces the published table)

Counts by `git grep` at each commit: `@lru_cache`/`@cache` 94 → 96; `@cached_property` 75 → 78;
one `cachetools` use (`semantic/selected_query_cache.py:12`). Test-side rows of the published table
are out of this production lane and not re-read.

| Holder | Key | Omits | Bound | Lifetime and invalidation | Threads and processes; identical misses | Mark |
|---|---|---|---|---|---|---|
| `SELECTED_QUERY_CACHE` (`selected_query_cache.py:58–86`) | cut identity (five consumers) or frontier stamps (exclusions), implementation, selection, budgets | nothing needed for safety; the read instance makes it over-specific (DA-075) | 32 MiB, 128 entries, 8 MiB and 4,096 rows per entry | process; new key only | `RLock`; both compute; CLI process per page never hits | unchanged |
| `_installed_read_basis` (`serve/rich_queries.py:71`) | contract type, source names, profile, libraries | file content (custody catches drift) | 64 | process | `lru_cache` | unchanged |
| `_current_boundary`, `_implementation_sources` (`pdf_lowering.py:107, 259`) | none | — | 1 | process; custody check each call | double compute on race | unchanged |
| `_prepared_lowering_sources` (`pdf_lowering.py:168`) | boundary source tuple | — | 4 | process | retains prepared PDF releases | unchanged |
| `_captured_projection_inputs`, `captured_projection` (`companion_projection.py:561, 620`) | PDF domain contract (content), metadata object, family | metadata by object identity | 4 and 8 | process | `lru_cache`; double compute on race | new (sound, content-keyed) |
| `_prepare_release_cached` (`prepare.py:600`) | bundle, dependencies, profile, stack | — | 8 | process | double compute on race | unchanged |
| `_bound_data_operation_calls`, bound model (`data_operation_admission.py:109`) | model bytes, correspondence | — | 8 | process | — | unchanged |
| Deployment expectation caches (`execution_admission.py`, `_deployment_expectation` and revision helpers) | revision identities; file digest with mtime and ctime | — | `lru_cache` bounds | process | — | changed (generated fingerprint query) |
| Wire protocol and validators (`data_operation_wire.py:47, 53, 262, 489, 525, 560`) | none, or the whole captured source tuple | — | 1–256 | process | thread-safe; a rebuilt capture hits only after hashing every artifact (inferred) | unchanged |
| Static preparation and model decode (`data_operation_static_preparation.py:66`; `data_operation_model.py:1206`) | exact captured bytes | — | 8–256 | process | thread-safe | unchanged (no commit) |
| CPU call descriptors (`data_operation_cpu.py:189`) | serialized call without arguments | — | 64 | worker process; asset custody checked per use | per worker | unchanged (not previously listed) |
| Worker releases (`cpu_execution.py:150–174, 226, 284`) | capsule-reference digest | — | unbounded within a worker's life | cleared at init; one entry per distinct capsule | per worker; decoded release outside the byte budget | changed (request global removed beside it) |
| Coordinator capsules (`cpu_execution.py:707, 746–800`) | release id, checked by capsule digest | — | owned-byte budget | invocation | `RLock` | unchanged |
| File custody (`file_custody.py:83–137`) | path and digest; stat identity | — | unbounded (finite files) | stat change or 2 s racy window re-hashes; refuse on change | `RLock` | unchanged (new consumers: native selection assets) |
| Query custody (`_query_custody.py:136–260`) | module | — | unbounded | reload refuses | `RLock` | unchanged |
| `_OPEN_CACHE` (`archive_reader.py:34, 394–434`) | archive header, libraries, per engine | — | 8 per engine | header re-read each call; dies with engine | `RLock` | unchanged in substance (3ba5daa84 removed dead adapter code) |
| Execution-host bases (`orchestrate/execution_host.py:186–272`) | engine, release, runtime, root, determinants | — | 2 idle, 256 MiB | header and runtime re-read on acquire | run lock | unchanged |
| Per-object memos: `semantic_id` on formal, construction and sentence products (`formal_products.py:150` and siblings) | object | — | object life | immutable objects | — | new (sound) |
| Math parsers and memo; encoder, spaCy, GLiNER packs; native residency; record-reader caches | as published | — | as published | as published | as published | unchanged (no commit to owners) |
| DuckDB connections | — | — | per invocation | closed at exit | no holder, appropriate | unchanged |

**Repeated expensive work with no holder** (call-path counts, not timed):

| Work | Where it repeats | Finding | Mark |
|---|---|---|---|
| Native capture: ~46 generators (now larger), physical compile when not supplied, schema view, ~110 file reads (99 modules plus model files) | 2 per acquisition, recheck and publication-port acquisition; 3 per definition admission; 1 per preparation, regeneration, candidate build, demand export; ≥2 per preview | DA-083 | changed (larger per rebuild) |
| Physical compile at import of `semantic/metadata.py` and inside captures | every importing process | DA-083 | unchanged |
| Release content re-proof in SQL (archive parse, byte hashes, prepared-bytes decode, authored-SQL hashes, model hash, projection decode) | every `require_native_execution` | DA-033 | changed footprint (generated) |
| Per-binding artifact parse | each binding and population selection | DA-033 | unchanged |
| Full native revision for a digest-only change | every edit to any of 99 captured modules or six libraries | DA-068 | new evidence (N29) |
| Scientific policy recipe | three comparison sites | DA-077 | unchanged |
| Frozen catalog verification rebuilt from the frozen guard (`native_admission.py:85–110`) | each `verify_deployment_catalog` (deployment and archive fence) | — | new; low consequence (not on the acquisition path) |

## 4. Structural causes

**No really new cause.** The range produced instances, not causes:

- *Established instance of cause 1 (identity broader than its premise), DA-068.* The kernel
  capture nests a further hand list (the PDF search renderer, `pdf_source_search.py:29–37`) whose
  members are also served-read inputs and construction helpers. A Python-only construction edit
  restamped the kernel and forced N29, whose deployed SQL differs from N28 only in digest
  literals. FP-04/A2, FP-07/A4, DP-09, DP-10, H18. *Contrary:* fail-closed by design; the plan
  accepted conservative replay. Home it in DA-068 as evidence of frequency.
- *DA-083 sharpened.* The release already carries the native digest it was prepared with, and the
  SQL guard already compares it to the descriptor; the Python check rebuilds the capture twice
  solely to compare the checkout. FP-07/A4, DP-10, H12. *Contrary:* that comparison is the
  intended "restart or redeploy" signal in the working loop.

## 5. Sound designs to preserve

The shared seal builder (one definition used by writer and checker, b294ab4e2); per-invocation
cancellation closure (5c5443d16); generators taking the captured physical metadata; the
content-keyed companion projection holder; native selection asset custody through
`verified_file`; release admission generated predicate for predicate with the receipt recorded
only if absent; file and query custody; the read kernel pin; the semantic request key without
release or runtime; `_captured`'s required-set and projection-physical checks; the rich assets'
AST meaning projection; `SelectedQueryCache` byte accounting.

**Uncertainty.** No call volumes, replay counts, rebuild times or memory were measured. Not traced:
whether `public_disclosure` enters cut pins; whether the composition module added to view
operation sources is sliced; whether `formal/execution-custody` enters the implementation revision.

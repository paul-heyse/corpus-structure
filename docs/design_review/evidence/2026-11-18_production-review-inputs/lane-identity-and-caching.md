# Lane: identity, reuse and execution findings at `d78c98765`

**Interface-checked by source inspection, 2026-11-18.** Source: frozen snapshot `snap5/` of
`d78c98765`. Paths below omit `snap5/python/corpus-structure/src/corpus_structure/` unless they
start with `docs/` or `tests/`. Nothing was run; no claim here is Tested or Measured. History
from read-only `git log 1afa63f88..d78c98765` (163 commits, 132 production files).

**Read fully:** `semantic/data_operation_storage.py:1–1131, 1540–1560, 1834–1873`;
`semantic/pdf_lowering.py`; `semantic/selected_query_cache.py`; `_query_custody.py:1–260`;
`semantic/native_admission_release.py`; `serve/rich_queries.py:30–145`;
`semantic/data_operation_projections.py:1809–1935, 2434–2470`;
`semantic/data_operation_admission.py:100–415`; `schema/physical.py:140–199`;
`semantic/characterization_ports.py:40–200`; `semantic/formal_products.py:660–790`.
**Sampled:** generators (`data_completion_settlement_native.py:500–685`,
`binding_admission_native.py:210–275, 795–830`, `population_acquisition_native.py:895–925`,
`demand_result_native.py`, `data_read_boundary_native.py:75–105`,
`archive_projection_native.py:114–264`), `sql/admission.sql`, `sql/closure.sql:36–77`,
`semantic/prepare.py:560–610, 940–1040`, `schema/model_change.py:300–440, 1066–1105`,
`schema/source_migrations.py:160–200, 680–715`, `schema/model_deployment.py:575–605`,
`orchestrate/data_operations.py:690–790`, `orchestrate/native_demand_io.py`.
**Not re-read** (no commit in range, earlier text taken as still valid): `visual_requests.py`,
`ingest/pdf_chandra.py`, `execution_admission.py`, `file_custody.py`,
`orchestrate/execution_host.py`, `cpu_execution.py`, `archive_reader.py`,
`methods/math/grammar.py`; the `serve/*` consumers of the query cache beyond the key lines;
established validity; change impact.

## 1. Findings re-read

| ID | Status at `d78c98765` | Changing commits |
|---|---|---|
| DA-068 | **Wider again**; mechanism and five uses stand; a sixth and seventh use confirmed | 555e28d59, d422c48e7, 46f13b88b, b1c10cbbf, 434f167c8 and the other generator commits listed under `git log … data_operation_storage.py` (30 commits) |
| DA-069 | **Stands, unchanged** | none (0 commits to `formal_products.py`, `characterization_ports.py`, `python_operation_sources.py`) |
| `LOWERING_FILES` | **Own finding recommended** (site of causes 1 and 2); grew from ~56 to 70 hand entries | 10 commits, latest 00310a212 |
| DA-075 | **Stands, unchanged** | none to the key sites (455405a8d touched `demand_results.py` detached verification only) |
| DA-076 | **Stands, unchanged**; contrary evidence strengthened for native SQL drift | none to `_query_custody.py` / `serve/rich_queries.py` |
| DA-077 | **Stands, unchanged** | none |
| DA-078 | **Stands**; kernel component now established (was inferred) | program form via 555e28d59 and binding commits; substance unchanged |
| DA-033 | **Changed footprint, substance stands** | f52742977, c1a2cdcbc (release preconditions generated), b1c10cbbf (binding), dbe22b899 |
| DA-058 | **Stands, unchanged** (source unchanged since `1afa63f88`) | none |

### DA-068 — kernel digest over the whole native capture: wider again

*Established.* `native_source_digest()` still hashes every `native/*` artifact of
`native_protocol_sources()` (`semantic/data_operation_storage.py:703–713`). The capture now
holds, whole: roughly 75–85 Python modules (52 `read_bytes` sites in
`data_operation_storage.py:181–566`; twelve binding modules plus the whole
`data_operation_model.py` in `data_operation_binding_native.py:30–53`; four wire modules;
three operation-event modules; source, search and projection helpers), the generated SQL of
about 45 programs, the physical YAML closure and LinkML types
(`data_operation_projections.py:2463–2470`), three logical YAML files (`:41–45`), and the
installed versions of pglast, sqlalchemy, linkml-runtime (`:206–214`), networkx (`:537–546`),
docling-core and docling (`semantic/pdf_source_search.py:63`). At `1afa63f88` there were 45
`read_bytes` sites in the storage module; now 57.

Uses of the digest (all established):
1. baked into SQL as `__DDO_SOURCE_DIGEST__` (`data_operation_storage.py:804`) and compared
   with the installed descriptor against the *checkout* on every
   `require_data_operation_native` (`:1116–1131`);
2. release admission compares the archived projection's `native_digest`
   (`data_operation_compiler_native.py:998–1093`; `sql/admission.sql:46`);
3. stamped on each read (`demand_result_native.py:209`); a read under another kernel is
   "not present" (`data_read_boundary_native.py:84–92`);
4. completion seal (`data_completion_settlement_native.py:509–528`);
5. receipt `validating_kernel_digest` (`data_derivation_native.py:614`), and the replay gate:
   `ddo_require_episode_correspondence` runs the full completion battery when the receipt's
   digest differs (`data_completion_settlement_native.py:661–676`). The routine is declared
   `stable=True` (`:681`), so it cannot record that the replay succeeded. Seven family
   validators still call it (`contextual_admission_native.py:226`,
   `definition_admission_native.py:129`, `operation_event_native.py:409`,
   `record_grade_native.py:709`, `record_policy_completion_native.py:595`,
   `artifact_admission_native.py:58`, `rich_admission_native.py:483`);
6. *new to this account:* each native protocol operation's declared `behavior` is
   `"ddo-native-v1:" + digest` (`data_operation_storage.py:982`), so every native operation
   definition, and with it its recipe, changes with the digest;
7. the readiness watermark (`data_operation_projections.py:1932`; see DA-078).

And indirectly: the release id hashes every dependency artifact digest
(`semantic/prepare.py:956–985`), and preparation passes the whole native capture and the port
generators as dependencies (`semantic/data_operation_preparation.py:261–271`;
`semantic/primary_operations.py:403–413`; `semantic/native_products.py:109–118`). So the
capture is part of `release_id` as well.

**What an edit to one generator module or a library bump forces today** (chain established,
volumes not): (a) in any process, the checkout digest differs from the installed descriptor,
so every port acquisition, cached-port recheck, publication-port acquisition and definition
admission refuses (`data_operation_admission.py:285, 354, 390`; `data_operation_storage.py:1548`)
until a kernel revision is authored and deployed; (b) the release id changes, so a new release
must be prepared and admitted; (c) after deployment every earlier receipt in the seven families
replays its battery on each validity evaluation that reaches it; (d) every read reacquires;
(e) every waiting obligation's watermark advances; (f) if the module is also on the PDF
lowering list (`native_program.py`, `native_call_contracts.py`, `metadata.py`,
`schema/physical.py`, `identity.py`…), PDF certification refuses as well. A patch bump of
sqlalchemy, pglast, linkml-runtime, networkx or docling does the same even when every generated
byte is identical.

**Finer identity available, unused for keying.** Each program's exact generated bytes are
captured beside its generator (`native/<name>.sql`, `:181–189`), and
`__DDO_LOWERING_DIGEST__` is already the digest of one generated file, `compiler.sql`
(`:805–808`). The per-program bytes would separate "generated SQL changed" from "a generator
or library changed" but nothing keys on them.

**New sub-observation (custody).** The capture pairs SQL generated by the *already imported*
generator objects with module bytes read *fresh from disk* (`:186–187`), with no file custody
(unlike the PDF lowering list and query custody, which refuse on drift). In a long-lived
process after an edit, the captured bytes and the generated SQL come from different code.
Admission then refuses (fail-closed), but a preparation run inside such a process would record
a capture that is not hermetic (CI-11). Whether preparation runs in long-lived processes was
not established; `ci model change` runs in a fresh process. *Likely, low frequency.*

**Contrary evidence.** Capture remains attributable and fail-closed; replay under changed
validators protects a real premise; the required-set check and the projection-physical
equality (`:569–692`) are sound. The plan's choice of the kernel digest for the seal stands as
documented.

### DA-069 — implementation identity of construction and formal operations

Stands with no source change. Construction assets hash whole `established_validity.py`,
`characterization*.py`, nine construction modules, rule JSON, the prose grammar,
`methods/annotation_rules.py`, `ingest/annotation_views.py`, the whole
`data-operation-constructions.yaml` and `lark`/`pydantic`/`spacy` versions
(`semantic/characterization_ports.py:47–193`); formal hashes twelve whole modules, math grammar,
transform, TeX, grammars, three model YAML files and `lark`/`sympy`/`pydantic`
(`semantic/formal_products.py:688–756`), while slicing its own module (`:723–744`).
`formal_execution_custody` additionally captures whole `formal_products.py`,
`established_validity.py`, `cpu_execution.py`, `cpu_receipts.py` (`:676–686`) and is passed as a
boundary contract (`:771`); whether it enters the implementation revision or only runtime
custody was not traced (`python_operation_sources.py:941–973` folds boundary digests in when
the model declares them). Contrary evidence and uncertainty unchanged.

### `LOWERING_FILES` (PDF lowering identity) — recommend its own finding

*Established.* `semantic/pdf_lowering.py:33–104` is a hand-written tuple of **70** paths
(64 Python modules, five model YAML files, one JSON schema; counted 2026-11-18) plus 14
library versions (`:15–30`, including sqlalchemy, pglast, pyarrow, linkml, pydantic). Its
docstring calls it an "explicit runtime responsibility closure" (`:31–32`). It grew by hand in
each of ten generator commits in the range (about 56 entries at `1afa63f88`).

What it keys: the lowering contract `implementation/pdf/lowering-contract.json` lists the
digest of every listed file, generated JSON schemas and Arrow codecs, the PDF boundary sources
and the libraries (`:243–256`). That contract enters the release through
`pdf_domain_sources` (`semantic/pdf_domain.py:144–147`), hence the release id, and its digest
is the receipt's `lowering_identity`.

What refuses on mismatch: `require_lowering_identity` (`:276–310`) refuses when current
metadata differs from the boundary ("restart required", `:296–300`) or when the recomputed
contract differs from the released one (`:301–303`). Consumers: PDF stream production
(`orchestrate/pdf_streaming.py:666`), the producer contract used in certification
(`semantic/pdf_certification.py:76`), and published-oracle capture, which also compares the
receipt's identity (`semantic/pdf_publication.py:1276–1281`).

How completeness is established: it is not. No derivation, import-closure check or test of
coverage exists (tests only check the equal and tampered-artifact paths:
`tests/semantic/test_pdf_lowering_contract_inputs.py`, `tests/semantic/test_pdf_producer_certification.py:137–170`;
two orchestration tests replace the function with a constant). It is demonstrably incomplete:
`pdf_staging_native.py` (listed) appends `pdf_spool_native_sql()` from the unlisted
`pdf_spool_native.py` (`semantic/pdf_staging_native.py:170`), and the unlisted
`semantic/pdf_domain.py` supplies `pdf_call_bindings`/`require_pdf_call_context` to five listed
modules. It is also broad: shared infrastructure (`native_program.py`, `schema/relational.py`,
`schema/physical.py`, `metadata.py`, `identity.py`, `prepared_sql.py`) is listed, so an edit
there refuses PDF work while also changing the kernel digest.

**Decision.** It is a site of both shared causes at once (identity broader *and* narrower than
its premise) and of the hand-list cause (a fact — "what code lowers PDF records" — kept by
hand). It is not a manifestation of DA-068 (different identity, different consumers) nor
DA-076 (served reads). Recommend a separate finding with FP-04, DP-04, DP-09, CI-10/CI-11,
H18; footprint: established for the list, the two omissions and the refusal paths; frequency
of refusals unknown.

**Sound parts to keep:** custody via `verified_file` with stat recheck and `lru_cache`
(`:107–165, 259–273`) so the process refuses instead of silently mixing code; contract bytes
compared in full; retained sources re-hashed against the contract.

### DA-075 — query cache keys include the acquisition instance

Stands unchanged. Keys: `serve/rich_queries.py:225`, `serve/contribution_facets.py:263`,
`serve/structural_products.py:282`, `semantic/demand_queries.py:200–213` (the interpretations
consumer was not re-read). `CutSelection.identity` is the SHA-256 of all pins including
`read_id`, `read_snapshot`, `frontier_at` (`semantic/demand_results.py:64–104`); native
acquisition now mints `read:` + `gen_random_uuid()` in generated code
(`demand_result_native.py:189`) and the snapshot/clock (`demand_registration_native.py:803–804`).
The CLI still opens a new engine and process per page (`cli/selected_results.py:96–130`).
`byte_bounded_page` still rebuilds the envelope per row (`semantic/selected_query_cache.py:189–200`).
The "four consumers page the frontier twice" sub-point was not re-read.

### DA-076 — served-read implementation identity is a hand-kept allowlist

Stands unchanged: `_query_custody.py:17–135` (four lists, docstring `:1–5`), the second list in
`semantic/demand_queries.py:117–124`, the duplicated statistics query names
(`serve/rich_queries.py:39–66`). Identity = listed file digests + nine library versions +
request JSON schema (`serve/rich_queries.py:71–105`); no native kernel. `semantic/releases.py`,
`archive_reader.py`, `data_operation_admission.py` and `_data_operation_wire.py` remain
unlisted.
**Contrary evidence, strengthened by the conversion:** answer-shaping native SQL now comes from
generators not on the list (`demand_result_native.py`, `data_operation_read_native.py`,
`data_operation_projections.py`), but their effect reaches answers only after a kernel
deployment, and a read acquired under another kernel is not present
(`data_read_boundary_native.py:84–92`); pinned cuts also carry `release_id`, which covers the
capture. The residual gap is Python-side answer code, as before.

### DA-077 — archived scientific policy is a description

Stands unchanged (`semantic/scientific_evidence.py:192–259` against `:1301`). A third comparison
site exists and also rebuilds the recipe per call: `semantic/rich_policy_binding.py:22–30`
(writer: `semantic/rich_knowledge_sources.py:81–82`). The DuckDB conversion did not touch it.

### DA-078 — readiness watermark coarser than declared dependencies

Stands. `_inputs_watermarks` (`semantic/data_operation_projections.py:1809–1935`) digests
fulfilled uses of every transitive prerequisite operation with the same `original_source`
(`:1821–1857`), relevant populations, every visible original admission for the demand
(`:1892–1901`), source sets, and the whole `trust_snapshot` and `kernel_digest`
(`:1927–1935`). The kernel component, inferred at `1afa63f88`, is now established. Skip site:
`semantic/data_operation_demands.py:736`.

### DA-033 — admission and binding re-prove immutable release content

Changed footprint, substance stands. `release_preconditions` (generated,
`semantic/native_admission_release.py:13–28`) checks the finalization row exists and then
performs `sem.require_execution_projection` — re-parsing the archive and registry
(`semantic/archive_projection_native.py:114–264`), which itself performs
`sem.require_archive_bytes` (`:264`), hashing every input and artifact (`sql/closure.sql:36–77`);
the retained body then parses the archive again for diagnostics (`sql/admission.sql:20–24`)
and the archived projection (`:40–60`). Receipts recorded only if absent
(`native_admission_release.py:31–67`). Per binding, `ops.ddo_require_binding` still parses and
hashes `data_operations.json` and the native definitions projection for every call
(`semantic/binding_admission_native.py:232–251`), as does population selection
(`semantic/population_acquisition_native.py:906–921`). The Python native closure is rebuilt
twice per `require_data_operation_native` (`data_operation_storage.py:1128, 1131`) and three
times per definition admission (`:1548, 1558`) — see §3.

### DA-058 — visual recognition re-prepares its runtime

Stands; no commit touched `semantic/visual_requests.py` or `ingest/pdf_chandra.py` in the
range, so the cited lines hold. Chandra remains outside scope by operator direction.

## 2. Identity inventory

"Model" = derived from model declarations or compiled model; "content" = derived from
supplied bytes without a hand list; "hand" = membership fixed by a hand-written list.

| Identity | Owner | Covers | Basis | Consumers | On mismatch |
|---|---|---|---|---|---|
| Native kernel digest | `semantic/data_operation_storage.py:703–713` | Whole native capture (§1 DA-068), six library versions | hand list (capture enumerated in code) | descriptor check, admission, read pin, seal, receipt, native op `behavior`, watermark | refuse acquisition; reacquire read; replay battery; re-bind |
| Native lowering digest | `:805–808` | Bytes of generated `compiler.sql` only | content | demand authority/intent programs (`:149–162`) | not traced |
| Release id | `semantic/prepare.py:956–985` | Root, model digest, profile, compiler and analysis library versions, every source and dependency artifact digest (native capture, generators, PDF lowering contract), vocabularies | content (over everything supplied) | everything release-keyed (cut pins, established validity, runtime attestation, admission) | new release must be prepared and admitted |
| Kind / definition / eligibility / implementation-slice / recipe fingerprints | `semantic/data_operation_identity.py:349–414`; `data_operation_compilation.py:1973–2219` | Compiled model records; sliced source graph; opaque boundary digests | model (+ boundaries) | native completion revision equality; acquisition `_inspect_execution_identity` (`data_operation_admission.py:324–347`) | refuse |
| Opaque boundary assets | `characterization_ports.py:47–193`; `formal_products.py:676–756`; `rich_invocations.py:15–70` | Whole files + whole model YAML + library versions; rich assets use an AST meaning projection (`python_module_projection.py:111–120`) | hand lists | implementation slice → recipe | prior derivations not reusable |
| Port generator custody | `semantic/data_operation_artifacts.py:22–39, 73–81` | Eight generator modules | hand | release dependencies; compile refuses if installed generator differs | refuse |
| Runtime artifact and attestation | `semantic/data_operation_runtime.py:88–120, 180–213` | Python version + every supplied executable input; attestation adds release, profile, observation | content | native retained manifest/archive digests (`data_operation_admission.py:343–347`) | refuse |
| PDF lowering contract | `semantic/pdf_lowering.py:33–104, 168–256` | 70 listed files, boundary sources, generated schemas and codecs, 14 libraries | hand | release, producer contract, streaming, oracle, receipt `lowering_identity` | refuse ("restart" or "differs") |
| Served-read implementation | `serve/rich_queries.py:71–105`; `_query_custody.py:17–135`; `demand_queries.py:117–124` | Listed module digests, 9 libraries, request schema | hand | cursors, `resource_handle`, query-cache keys | refuse resume; in-process drift refuses (restart) |
| Cut identity | `semantic/demand_results.py:64–104` | All native pins incl. read instance, snapshot, clock | content | cursors, `expected_cut`, cache keys | refuse continuation |
| Read kernel pin | `demand_result_native.py:209`; `data_read_boundary_native.py:84–92` | Kernel digest at acquisition | as kernel | read presence | reacquire |
| Semantic request key | `binding_admission_native.py:213`; `request_attachment_native.py:1024–1539` | Request meaning only (no release or runtime) | model | request reuse across releases | new request |
| Inputs watermark | `data_operation_projections.py:1809–1935` | Transitive prerequisite operations' uses (by source), populations, originals, source sets, trust snapshot, kernel | model at operation granularity, not role | planner skip (`data_operation_demands.py:736`) | re-bind |
| Completion seal | `data_completion_settlement_native.py:509–528` | Kernel, request, generation, release, recipe, runtime, payload digest, trust | mixed | publication battery skip | run battery |
| Receipt validating kernel | `data_derivation_native.py:614`; gate `data_completion_settlement_native.py:661–676` | Kernel at publication | as kernel | seven family validators | replay, unrecorded |
| Physical id; deployment-admission receipt; frozen descriptor expectation | `schema/physical.py:142–151`; `native_admission_release.py:31–67`; `execution_admission.py:285–420` | Physical YAML closure; descriptor bytes; Alembic revision file digest + mtime/ctime | content | admission, catalog guard | refuse |
| Wire contract digest | `data_operation_wire.py:46–60`; checked per call `data_operation_storage.py:1111` | Protocol YAML / captured protocol | content | every native invocation envelope | refuse |
| Scientific policy | `scientific_evidence.py:192–259`; `rich_policy_binding.py:22–30` | Hand-written description of the kernel | hand | release check, rich context | refuse |
| Model-change compilation fingerprint | `schema/model_change.py:323–440` | Every `.py/.sql/.yaml/.json/.lark/.jinja` in both selected and running package (excl. generated and `model/`), union of byte/analysis/deployment libraries + 8 tools, request, bases, acquired inputs | content (whole tree) | `check_candidate_files` (`schema/model_deployment.py:582–604`); `cli/model.py:1676, 1925` | "prepare a fresh preview" |
| Generator fingerprint; HEAD; Python version | `schema/model_change.py:313–320, 1066–1077` | All `schema/*.py`; worktree HEAD | content | preview and candidate checks | refuse |
| Source-migration preparation / implementation identity | `schema/source_migrations.py:168–198` | Every file under `semantic/` and `model/semantic/` + 8 libraries; two modules + 2 libraries | content (whole tree) | `check_source_migration` (`:701–712`) | refuse |
| File custody; query custody | `semantic/file_custody.py:20, 79–137`; `_query_custody.py:136–260` | Path digest with stat identity; module bytes at import | content | lowering, model assets, served reads | refuse, restart |

Of these, only the request key, the per-operation fingerprints and (partly) the watermark are
derived from model declarations. The kernel capture, lowering list, served-read lists, boundary
asset lists, generator list and scientific policy are hand-maintained; the release id, preview
fingerprints and source-migration identity are whole-content and so over-broad by construction.

## 3. Cache and prepared-state inventory, refreshed

Counts unchanged from the audit: 94 `functools` caches, 75 `cached_property`, one `cachetools`
use (`semantic/selected_query_cache.py:12`; `serve/rich_queries.py:81` only names the
library's version). Rows of the audit table not re-read are unchanged by commits (archive open
cache, execution host, CPU worker releases, grammar memos, native residency — one commit
`890761d41` refactored startup validation only).

| Holder | Key | Omits | Bound | Lifetime / invalidation | Concurrency |
|---|---|---|---|---|---|
| `SELECTED_QUERY_CACHE` (`selected_query_cache.py:58–86`) | as audit (DA-075) | — | 32 MiB by size, 128 entries by hand `popitem`, 8 MiB / 4,096 rows per entry | process; new key only | `RLock`; identical misses both compute |
| `_installed_read_basis` (`serve/rich_queries.py:71`) | contract type, source names, profile, extra libraries | file content (captured inside; drift caught by custody) | 64 | process | `lru_cache` |
| `_current_boundary`, `_implementation_sources` (`pdf_lowering.py:107, 259`) | none | — | 1 | process; file custody `check()` each call refuses on drift | `lru_cache`; double compute on race |
| `_prepared_lowering_sources` (`pdf_lowering.py:168`) | boundary source tuple | — | 4 | process | each entry retains a prepared PDF release and full sources (memory not assessed) |
| `_prepare_release_cached` (`prepare.py:599`) | bundle, dependencies, profile, stack | — | 8 | process | as audit |
| `_bound_data_operation_calls` (`data_operation_admission.py:108`) and bound model | model bytes, correspondence | — | 8 | process | — |
| Deployment expectation caches (`execution_admission.py:285, 363, 393, 420`) | revision identities; file digest + mtime + ctime | — | lru | process | — |
| Wire protocol (`data_operation_wire.py:46, 52, 261, 414, 450, 485`) | none / whole captured source tuple | — | 1–256 | process | key is the *entire native capture tuple*; a freshly rebuilt capture hits only after hashing and comparing every artifact's bytes (inferred cost) |
| DuckDB connections (`semantic/rich_relations.py:60–85`; `serve/companion_export.py:410, 552`; `semantic/artifact_identity.py:481, 579`; `ingest/pdf_stream_reconciliation.py:301`; `ingest/pdf_candidate_geometry.py:87`) | — | — | per invocation | closed at exit | no holder; appropriate for in-memory relations |
| File custody; query custody | as audit | — | unbounded (finite) | stat/racy recheck; reload refuses | `RLock` |

**Repeated expensive work with no holder (established structure; call counts from code paths,
not measured):**

- **The native capture** (`native_protocol_sources()`): runs ~45 SQL generators, compiles the
  physical LinkML model (`data_operation_storage.py:123–136`, `compile_physical` is uncached,
  `schema/physical.py:166–199`, and does not reuse the identical module-level
  `semantic/metadata.py:33` metadata), builds a `SchemaView` for source values
  (`source_value_native.py:56`), and reads ~80 files. No cache. Per call site:
  `require_data_operation_native` 2× (`:1128, 1131`), reached once per operation per execution
  context on port creation (`orchestrate/data_operations.py:698–757`), once per operation per
  run on cached-port recheck (`:782–785`), on each publication-port acquisition
  (`data_operation_admission.py:390`); definition admission 3× (`:1548, 1558`); each
  preparation (`data_operation_preparation.py:261`, `primary_operations.py:403`,
  `regeneration.py:331`); candidate definitions (`:1844`); and a demand export rebuilds the
  whole capture to read one wire schema (`serve/demand_export.py:281`). In a run touching N
  operations that is about 3N full captures (2N at creation, N at recheck when reused), plus
  publication.
- **Scientific policy recipe**, rebuilt per comparison (DA-077, three sites).
- **Release re-proof and per-binding artifact parse** in SQL (DA-033): not a cache gap, an
  assurance-carrying gap.

## 4. Structural causes in this area

**N1 (recommend new DA): the PDF lowering identity is a hand-kept whole-file list** — see §1.
FP-04, DP-04, DP-09, CI-10, CI-11, H18. Sites `semantic/pdf_lowering.py:15–104`. Consequence:
any edit to 70 files (including shared infrastructure) or 14 library bumps refuses PDF
production, certification and oracle capture until re-release; edits to at least two unlisted
modules on the lowering path (`pdf_spool_native.py`, `pdf_domain.py`) do not. Contrary: file
custody makes in-process drift fail closed; the list is labelled as the deliberate closure.

**N2 (recommend new DA, or a sharpened DA-033/068 sub-finding): the native capture has neither
holder nor custody.** FP-07/A4, DP-10, CI-11, H12. It is regenerated from imported code and
re-read from disk on every admission-side call (§3), so its cost scales with the converted
kernel (now ~45 generators and a LinkML compile per rebuild, versus hand-written SQL files
before the conversion), and generated SQL and captured module bytes can come from different
code in a long-lived process (§1 DA-068). Contrary: rebuilding is what makes the descriptor
check track the checkout, which the design wants as a "restart or redeploy" signal; a holder
would need the same file-custody pattern the lowering list already uses.

**Not new, but its footprint changed: one file now feeds several overlapping identities.**
`native_program.py`, `native_call_contracts.py`, `metadata.py`, `schema/physical.py`,
`identity.py` sit in the kernel capture, the lowering list and (through dependencies) the
release id; the whole tree also feeds the preview and source-migration fingerprints. One edit
there invalidates the kernel, the release, PDF certification and any open model-change
candidate together. This is cause 1 ("identity broader than its premise") and cause 2 (the
fact "which code determines which artifact" restated in five hand lists) meeting. The model
already compiles implementation slices for Python operations
(`data_operation_identity.py:378–414`); no comparable declared owner exists for native
generators, PDF lowering or served reads.

**Sound designs to preserve.** Query custody's import loader that compiles exactly the hashed
bytes and refuses reloads (`_query_custody.py:136–200`); file custody with stat identity and a
racy window; the read kernel pin that turns kernel drift into reacquisition
(`data_read_boundary_native.py:84–92`); the semantic request key excluding release and runtime;
`_captured`'s required-set and projection-physical equality checks
(`data_operation_storage.py:569–692`); generated bytes captured beside generators; the rich
assets' AST meaning projection (`python_module_projection.py:111–120`), the finest
implementation identity in the codebase; deployment expectations cached by file digest and
stat; `SelectedQueryCache`'s byte accounting and immutable encoded entries; per-invocation
DuckDB connections with spill directories.

**Uncertainty.** No call counts, run volumes, replay frequency or memory figures were
measured. Whether `formal/execution-custody` enters the implementation revision, and whether
preparation ever runs in a long-lived process, were not traced.

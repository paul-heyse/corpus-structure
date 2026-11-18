# The domain model and execution, across production and tests

**Interface-checked by source inspection.** This page was written on 2026-11-17 at source
`fbd3f2a98` as the integrated analysis of a joint refresh of the [broad account](README.md) and
the [test account](../test-audit/README.md), with two priorities set by the operator: the
comprehensive domain data model, and efficiency of execution. On 2026-11-18 the production
side was refreshed at source `d78c98765` ([refresh](README.md#refresh-2026-11-18)): the
shared-causes table, the cache inventory, the identity inventory and the analytical section
below are at that source, and each other section says which date it carries. The test account
was not refreshed, so every `DTA` entry keeps its 2026-11-17 date. The page holds analysis,
inventories and links. Findings keep their primary homes in the topic pages of each account,
and nothing here selects a remedy.

Production paths omit `python/corpus-structure/src/corpus_structure/`; test paths beginning
`tests/` are relative to `python/corpus-structure/`; `scripts/` and `conftest.py` are at the
repository root. No timing on this page is measured unless it cites a stored run; statements
of cost are counts of repeated work read from code paths.

## The short version

The declared model governs operations, kinds, roles, states and result identity well. The
strongest design in the codebase is the semantic request identity: it is built from the
recipe, content-addressed inputs and the implementation slice, and it leaves out the release
and the runtime, so a result survives a new release and an unchanged input stops recomputation
from spreading.

Around that core, the same three things recur in production code and in the test system:

1. **Identities that are much coarser, or narrower, than what they stand for.** A digest over
   about eighty modules and six library versions stands for "the kernel that validated this".
   A per-test directory is part of "which scenario this is". A hand-kept file list stands for
   "the code that produced this answer", and another for "the code that lowers PDF records".
   Coarse keys throw away valid work on unrelated edits; narrow keys let stale work through.
2. **Facts the model holds, or could hold, written again by hand.** Operation-id lists, three
   encodings of the support graph, role names, fixture-name lists, nine copies of a test
   converter. Each copy is a place where a model change has to be remembered.
3. **Reuse added without the evidence that it is safe.** Several mechanisms that skip a check
   or carry a result forward are tested only where the reuse is correct.

These are the same problem seen from three sides. Caching and targeted execution both need an
answer to "what does this result depend on?". Where the model gives that answer as data, reuse
is exact (the request identity). Where it does not, each mechanism invents its own
approximation, and the approximation is either too broad to hit or too narrow to trust.

**What the 2026-11-18 refresh adds.** Most of the model-owned SQL conversion landed between the
two readings. It is not complete: ADR-0131 and the DDO plan record residual SQL authoring as
open work, and the hand-written PostgreSQL still deployed is inventoried in
[DA-084](boundaries-and-composition.md#da-084). What landed replaced most hand-written
PostgreSQL with typed programs that take relations and
columns from the compiled model, which is a real gain: a renamed table or column now fails at
generation. It did not move any of the hand lists of cause 2 into the model; it moved them
from SQL into Python. It also made cause 1 worse in one place and exposed a fourth recurring
thing:

4. **Derived artifacts with no holder and no registry.** The native program set is
   regenerated from scratch at every admission-side call ([DA-083](execution-fit.md#da-083)).
   It is also listed by hand in six places, and once rendered it is handled as text that is
   concatenated, patched and parsed again to recover facts the program objects held
   ([DA-081](semantic-model-and-authority.md#da-081)).

## Shared causes and where their findings live

Production entries are at `d78c98765` (2026-11-18); test entries are at `fbd3f2a98`
(2026-11-17).

| Cause | Production | Tests |
|---|---|---|
| **Identity broader than its premise**: valid work discarded on unrelated change | [DA-068](execution-fit.md#da-068) native kernel digest; [DA-069](execution-fit.md#da-069) opaque-boundary implementation identity; [DA-075](execution-fit.md#da-075) cache key includes the read instance; [DA-078](execution-fit.md#da-078) readiness watermark; [DA-082](execution-fit.md#da-082) PDF lowering list (shared infrastructure listed whole) | [DTA-040](../test-audit/execution-and-qualification.md#dta-040) per-test path in recipe identity; [DTA-038](../test-audit/execution-and-qualification.md#dta-038) deployment key includes the whole lockfile and artifact mtimes |
| **Identity narrower than its premise**: stale work can pass | [DA-076](served-claims.md#da-076) read implementation allowlist; [DA-077](served-claims.md#da-077) scientific policy description; [DA-082](execution-fit.md#da-082) PDF lowering list (two modules on the path are unlisted) | [DTA-038](../test-audit/execution-and-qualification.md#dta-038) deployment key misses modules run by upgrade bodies |
| **A model fact restated by hand** | No declaration exists and a hand list is the only statement: [DA-070](semantic-model-and-authority.md#da-070) validity-family id lists; [DA-071](semantic-model-and-authority.md#da-071) support graph three times; [DA-073](semantic-model-and-authority.md#da-073) release composition; [DA-074](native-integrity.md#da-074) guard, role and grant lists; [DA-081](semantic-model-and-authority.md#da-081) no typed registry of programs and generated outputs, with the text handoff as its footprint. A declaration or typed source exists and is not read: [DA-086](semantic-model-and-authority.md#da-086) literals in generators and analytical modules. Two generations of the model: [DA-072](semantic-model-and-authority.md#da-072) | [DTA-037](../test-audit/retirement-transfer.md#dta-037) fixture-name lists; [DTA-041](../test-audit/support-structure.md#dta-041) converter copies; [DTA-042](../test-audit/support-structure.md#dta-042) pack composition; [DTA-043](../test-audit/support-structure.md#dta-043) copied reservation formula; [DTA-033](../test-audit/evidence-and-discrimination.md#dta-033) vector input rebuilt per consumer |
| **No one compiled object for cross-view facts to be derived from** | [DA-085](semantic-model-and-authority.md#da-085) one LinkML composition per consumer; constraints as JSON strings in annotations | — |
| **Model changes do not reach a deployed body** | [DA-084](boundaries-and-composition.md#da-084) hand-written PostgreSQL whose conversion is scheduled and open, inventoried here | — |
| **Established assurance re-proved instead of carried** | [DA-033](execution-fit.md#da-033) release content per admission and per binding; residuals of PE-F09 [below](#pe-state) | [DTA-039](../test-audit/execution-and-qualification.md#dta-039) whole migration chain per key miss; repeated head and seed verification |
| **A derived artifact rebuilt because nothing holds it** | [DA-083](execution-fit.md#da-083) native capture per admission-side call; the scientific policy recipe per comparison ([DA-077](served-claims.md#da-077)) | — |
| **Reuse without discriminating evidence** | The mechanisms are production's; the gap is in tests | [DTA-044](../test-audit/evidence-and-discrimination.md#dta-044) skips tested only on the equal path; [DTA-045](../test-audit/evidence-and-discrimination.md#dta-045) profile check asserted against a double; [DTA-046](../test-audit/evidence-and-discrimination.md#dta-046) batch attribution invisible |
| **Superseded machinery kept** | [DA-080](boundaries-and-composition.md#da-080), now including unread settings, kernels with no caller and two migration trees | [DTA-037](../test-audit/retirement-transfer.md#dta-037), [DTA-035](../test-audit/retirement-transfer.md#dta-035) |

Each cause has one primary finding per manifestation; where a production cause explains a test
manifestation, the test account links to the production finding instead of opening its own
(for example, tests of unused evaluation modules are footprint of DA-080).

Four production findings are hand-kept answers to "which code determines this artifact":
DA-068, DA-069, DA-082 and DA-076. DA-069 and the too-broad half of DA-082 are the closest
pair, since both take whole files and library versions as an implementation identity.

One interaction is new in the refresh: several files now feed overlapping identities.
`semantic/native_program.py`, `semantic/native_call_contracts.py`, `semantic/metadata.py`,
`schema/physical.py` and `semantic/identity.py` sit in the kernel capture, in the PDF lowering
list and, through dependencies, in the release id, and the whole tree feeds the model-change
preview and source-migration fingerprints. One edit there invalidates the kernel, the release,
PDF certification and any open model-change candidate together.

## Model facts that could key, scope or invalidate work

These are observations about what the model already makes available, paired with what the work
is keyed by today. They are leads for a later review, not selected changes.

| Model fact (already declared or compiled) | Work it could key or scope | Keyed by today |
|---|---|---|
| Per-operation recipe, definition and eligibility identities; implementation-slice fingerprint | Which definitions a new release actually changes; implementation identity of construction and formal operations | `release_id` over every input file (`semantic/prepare.py:956–985`); whole files and library versions ([DA-069](execution-fit.md#da-069)) |
| The source of each family's validators (captured per module), and each program's exact generated bytes (captured as `native/<name>.sql`) | Completion seal and receipt validation identity; separating "generated SQL changed" from "a generator or library changed" | The whole native capture ([DA-068](execution-fit.md#da-068)) |
| Direct role producers and subject context | Readiness of a waiting obligation | Every upstream operation for the same source ([DA-078](execution-fit.md#da-078)) |
| Compiled dependency projections (`potential-producers`, `selected-dependencies`) | Change impact; which obligations of a re-registered demand can only reuse | Rebuilt by hand in change impact ([DA-071](semantic-model-and-authority.md#da-071)); `potential-producers` is not consumed by execution |
| Validator asset content digest | Reuse of established product validity across releases | `release_id` (`semantic/established_validity.py:116`) |
| Release finalization and deployment-admission receipts | The release-content half of native admission | Re-proved per acquisition ([DA-033](execution-fit.md#da-033)) |
| Admitted definition rows and the lowering digest | Per-binding correspondence checks | Artifacts re-parsed per attached item ([DA-033](execution-fit.md#da-033)) |
| Frontier content stamp with release, runtime and selection | Served query results across fresh requests | The acquisition instance ([DA-075](execution-fit.md#da-075)); soundness of the alternative is an open premise |
| Whole rich product body with release | One validated graph index shared by every query on that product | Per-query selection |
| Physical annotations on relations; in particular `ph:immutability: pending-content` on exactly the two shared-stream relations | Frontier-guard and trigger membership | Hand lists and a name set ([DA-074](native-integrity.md#da-074)) |
| The protocol's declared task lifecycle; typed `Literal` vocabularies | State tests and tag tests in generated kernels | String literals ([DA-086](semantic-model-and-authority.md#da-086)) |
| Implementation slices, which the compiler already derives for Python operations | The code identity of PDF lowering, native generators and served reads | Hand-kept file lists ([DA-082](execution-fit.md#da-082), [DA-068](execution-fit.md#da-068), [DA-076](served-claims.md#da-076)) |
| The migration graph and its pinned artifact digests | The test head: content identity of artifacts; building from the predecessor head | Size and mtime; full replay ([DTA-038](../test-audit/execution-and-qualification.md#dta-038), [DTA-039](../test-audit/execution-and-qualification.md#dta-039)) |
| Recipe content identity without the capture directory | Scenario seed and prepared-kernel reuse across tests | A value that includes the per-test path ([DTA-040](../test-audit/execution-and-qualification.md#dta-040)) |
| The fixture graph and the recipe-type registry | Database classification and worker affinity of tests | Hand lists of fixture names ([DTA-037](../test-audit/retirement-transfer.md#dta-037)) |

Two boundaries are right as they are and should not be "improved": the model YAML does not
reach the test head, because frozen migrations never import current compiler state; and the
request identity excludes the release and the runtime.

<a id="cache-inventory"></a>

## Caches and prepared state

### What exists

Refreshed 2026-11-18 at `d78c98765`. Production has one cache built on `cachetools`
(`semantic/selected_query_cache.py:12`), about 94 `functools` caches, about 75
`cached_property` sites and about ten hand-built process-level holders; these counts are
unchanged from 2026-11-17. The repository pins `cachetools` 7.2.7; the
[library overview](../../libraries/analytical_infrastructure/cachetools.md) describes 8.0.
Tests use no `cachetools`; they have 31 session and 96 module fixtures, about 50 `functools`
helpers, and two cross-run stores (test-side figures are from 2026-11-17).

Rows marked "2026-11-17" were not re-read; no commit in `1afa63f88..d78c98765` changed their
substance (one commit, `890761d41`, refactored startup validation of native residency only).

| Holder | Key | Bound | Lifetime and invalidation | Concurrency | Note |
|---|---|---|---|---|---|
| `SELECTED_QUERY_CACHE` (`semantic/selected_query_cache.py:58–86`) | Cut identity (five consumers) or frontier stamps only (exclusions), with implementation, selection and budgets | 32 MiB by size function, 128 entries by a hand-written `popitem`, 8 MiB and 4,096 rows per entry | Process; new key only | `RLock` on get and put; concurrent identical misses both compute | [DA-075](execution-fit.md#da-075) |
| `_installed_read_basis` (`serve/rich_queries.py:71`) | Contract type, source names, profile, extra libraries | 64 | Process. File content is not in the key; it is captured inside, and drift is caught by query custody | `lru_cache` | [DA-076](served-claims.md#da-076) |
| `_current_boundary`, `_implementation_sources` (`semantic/pdf_lowering.py:107, 259`) | None | 1 each | Process; file custody is checked on each call and refuses on drift | `lru_cache`; double compute on a race | [DA-082](execution-fit.md#da-082) |
| `_prepared_lowering_sources` (`semantic/pdf_lowering.py:168`) | Boundary source tuple | 4 | Process | `lru_cache` | Each entry retains a prepared PDF release and full sources; memory not assessed |
| `_prepare_release_cached` (`semantic/prepare.py:599`) | Bundle, dependencies, profile, compiler stack | 8 | Process; new key | Thread-safe; double compute on a race | Sound; retains up to eight full artifact sets |
| `_bound_data_operation_calls` and the bound model (`semantic/data_operation_admission.py:108`) | Model bytes, correspondence | 8 | Process | — | — |
| Deployment expectation caches (`semantic/execution_admission.py:285, 363, 393, 420`) | Revision identities; file digest with mtime and ctime | `lru_cache` bounds | Process | — | Sound: keyed by content and stat |
| Wire protocol and validators (`semantic/data_operation_wire.py:46, 52, 261, 414, 450, 485`) | None, or the whole captured source tuple | 1 to 256 | Process | Thread-safe | The key is the entire native capture tuple, so a freshly rebuilt capture hits only after every artifact's bytes are hashed and compared (inferred cost; [DA-083](execution-fit.md#da-083)) |
| Static preparation and model decode (`semantic/data_operation_static_preparation.py:66`; `semantic/data_operation_model.py:1206`) | Exact captured bytes | 8–256 | Process; new key | Thread-safe | 2026-11-17. Sound, with strong key-sensitivity tests |
| `_ambient_protocol*`; `trusted_pdf_context`; `_report_*` | None: first read in the process | 1 | Process restart | — | 2026-11-17. Deliberate; a mismatch refuses by digest |
| DuckDB connections (`semantic/rich_relations.py:60–85`; `serve/companion_export.py:410, 552`; `semantic/artifact_identity.py:481, 579`; `ingest/pdf_stream_reconciliation.py:301`; `ingest/pdf_candidate_geometry.py:87`) | — | — | Per invocation; closed at exit | — | No holder, which is appropriate for in-memory relations |
| File custody (`semantic/file_custody.py:20, 79–137`) | Path and digest; stat identity | Unbounded (finite files) | Stat change or a 2 s racy window re-hashes; changed bytes refuse | `RLock` | Refusal means "restart" |
| Query custody (`_query_custody.py:136–260`) | Module | Unbounded | None; reload refuses | `RLock` | [DA-076](served-claims.md#da-076) |
| `_OPEN_CACHE` (`semantic/archive_reader.py:32–38, 396–434`) | Archive header and library versions, per engine | 8 per engine, hand-built `OrderedDict` | Header re-read each call | `RLock`; first cold result wins | 2026-11-17. Dies with the engine, so per-call engines defeat it ([PE state](#pe-state), F16) |
| Execution-host bases (`orchestrate/execution_host.py:186–272`) | Engine, release, runtime, root, run determinants | 2 idle capsules, 256 MiB | Header and runtime row re-read each acquire; mismatch refuses | Run lock | 2026-11-17. [DA-079](boundaries-and-composition.md#da-079) |
| Worker releases (`semantic/cpu_execution.py:148–224`) | Capsule digest | Per CPU generation | Cleared at worker init | Per worker | 2026-11-17. Decoded release is outside the byte budget |
| Math parsers and memo (`methods/math/grammar.py:309–327, 966–991`) | Macro classification; (latex, kind, table, context) | Parsers **unbounded**; memo 8,192 | None | Main thread | 2026-11-17. Now lives across runs in long-lived workers |
| Encoder, spaCy pipeline, compiled GLiNER pack | Profile or config | 1 / unbounded / 64 | Stat checks or process death | — | 2026-11-17 |
| Native residency (`methods/native_host.py:660–944`) | Profile fingerprint | Declared selections | Retired at run end unless keep-warm is set (default 0) | Waits on a condition | 2026-11-17 |
| Record reader per-instance caches (`semantic/pdf_record_reader.py:268`) | Record id | 256 per reader | Instance lifetime | — | 2026-11-17. Returns a shared mutable dict; consumers read only |
| Test head database (`scripts/native_test_support.py:896–1116`) | Deployment key | Three retained | Key change; failed verification retires | Advisory locks | 2026-11-17. [DTA-038](../test-audit/execution-and-qualification.md#dta-038), [DTA-039](../test-audit/execution-and-qualification.md#dta-039) |
| Scenario seeds (`scripts/native_scenario_seeds.py:193–360`) | Recipe value and head | Unbounded until session end | Head replacement | `RLock`, per worker | 2026-11-17. [DTA-040](../test-audit/execution-and-qualification.md#dta-040) |
| Test-side `functools` helpers (about 50) | Mostly none | 1 each, per worker | None | — | 2026-11-17. Values are frozen; acceptable within one run |

**Repeated expensive work with no holder** (structure established 2026-11-18; counts are read
from call paths, not measured):

| Work | Where it repeats | Finding |
|---|---|---|
| The native capture: about 45 SQL generators, a physical model compile, a further schema view and about eighty file reads | Twice per `require_data_operation_native` (each port acquisition, cached-port recheck and publication-port acquisition); three times per definition admission; once per preparation, per candidate-definition build and per demand export; at least twice per model-change preview | [DA-083](execution-fit.md#da-083) |
| Physical model compile | At import of `semantic/metadata.py` (two projections, in every importing process) and again inside each capture that is not handed compiled metadata | [DA-083](execution-fit.md#da-083) |
| Scientific policy recipe | Rebuilt at each of three comparison sites | [DA-077](served-claims.md#da-077) |
| Release content proof and per-binding artifact parse, in SQL | Each admission call; each binding and population selection | [DA-033](execution-fit.md#da-033). This is assurance that is not carried, not a missing cache |
| Parsing of generated SQL text | Per statement at render; per selected function name at installation; again for the inventory and the entry-point rename | [DA-081](semantic-model-and-authority.md#da-081) |

### What the inventory shows

- **Invalidation is by key alone.** No production cache is ever cleared outside tests, and none
  expires. That is sound only where the key is complete, which is why the completeness of each
  identity matters more than the cache mechanics.
- **Every cache is process-local.** The agent-facing `ci` CLI runs each command, and each page
  of a paged result, in a new process. In-process caches therefore help the long-lived MCP
  server and workers and do nothing for CLI paging. Reuse across CLI invocations would need
  something durable, which is a different mechanism from any in-process cache library.
- **Bounded caches are built four different ways**: `cachetools.LRUCache` with a size function,
  `functools.lru_cache`, a hand-built `OrderedDict` LRU, and plain dicts. The one `cachetools`
  use adds its entry-count cap by hand beside the library's size cap.
- **No cache coordinates concurrent identical misses.** In the MCP server, two agents asking
  the same uncached question both derive it.
- **Long-lived processes changed the meaning of some bounds.** Holders written for one
  invocation (math parsers, worker memo) now live for the life of a process host, and one
  family is unbounded and outside the declared byte budget. The number of distinct macro
  tables per corpus is unknown, so the growth is a hypothesis.
- **Refusal on drift means restart.** File custody, query custody, the ambient protocol and the
  host basis all refuse when their premise changes and ask for a new process. That is safe and
  deliberate, and it makes restarting the MCP server part of the edit loop.
- **The most expensive derived artifact has no holder at all (2026-11-18).** The native capture
  is rebuilt on every admission-side use, and unlike the PDF lowering sources it is not under
  file custody ([DA-083](execution-fit.md#da-083)). The caches that would serve it downstream
  key on the whole capture tuple, so they do not spare the rebuild.

### Facts about the library that bear on these observations

The overview is used here as a lens on what exists, not as a list of features to adopt. The
audit does not select remedies, and a missing cache is not a finding.

| Observation above | What the overview describes (section) | Caution |
|---|---|---|
| Entry-count cap added by hand beside a size cap | Capacity can be any weight through `getsizeof`; one cache has one capacity measure (§2.2, §2.4) | Two simultaneous bounds are not a built-in; the hand-written cap is a legitimate way to get both |
| Concurrent identical misses both compute | A `condition` argument on `cached` coordinates identical in-flight computations; a `lock` alone does not (§5.2, §5.3; addendum §1) | Coordination is local to one decorated wrapper and depends on the result being admitted to the cache. The pinned 7.2.7 already has the `condition` argument (installed source read 2026-11-17) |
| Hand-built `OrderedDict` LRU; `lru_cache` wrapped around bound methods | `cached` with externally owned storage; `cachedmethod` for explicit per-instance ownership (§4.1, §4.6; addendum §2) | Caching on methods can retain whole object graphs through the key (addendum §2.2) |
| Keys built by hand as JSON bytes or tuples | Key functions can define semantic identity; argument equality is not semantic equality (§4.4) | This is where the model-identity findings apply: a key function is only as good as the identity it is given |
| Invalidation only by new key | Explicit invalidation is distinct from expiry; generation-aware and dependency-aware keys (§7.3, §9.4; addendum §7) | Time-based expiry does not fit content-addressed, immutable results |
| Process-local only | The library provides no persistence or cross-process sharing of its own; a custom mapping could delegate storage elsewhere, without built-in atomicity or consistency (§9.2, §10.1) | CLI paging is outside what the cache classes address by themselves |
| Unbounded parser family in long-lived workers | Eviction policies and bounded storage (§2.3) | Evicting a parser is safe only if rebuilding is cheap relative to memory; not assessed |

<a id="identity-inventory"></a>

## Identity inventory

**Interface-checked by source inspection, 2026-11-18**, source `d78c98765`. An identity here is
a digest or key that decides whether earlier work, an installed object or a continued request
is still acceptable. "Basis" says how its membership is decided: *model* means derived from
model declarations or the compiled model; *content* means derived from whatever bytes are
supplied, with no hand list; *hand* means membership is fixed by a hand-written list. The
table has 22 rows; three of them group closely related identities under one owner.

| # | Identity | Owner | Covers | Basis | Consumers | On mismatch |
|---|---|---|---|---|---|---|
| 1 | Native kernel digest | `semantic/data_operation_storage.py:703–713` | The whole native capture and six library versions ([DA-068](execution-fit.md#da-068)) | Hand (the capture is enumerated in code) | Descriptor check, release admission, read pin, completion seal, receipt, native operation `behavior`, watermark | Refuse acquisition; reacquire the read; replay the battery; re-bind |
| 2 | Native lowering digest | `semantic/data_operation_storage.py:805–808` | The bytes of the generated `native/data-operation-compiler.sql` only | Content | Demand authority and intent programs (`:149–162`) | Refuse: the demand programs compare the release's `lowering_digest` with the compiled-in value (`semantic/demand_authority_native.py:137–138`; `semantic/demand_registration_native.py:602`) |
| 3 | Release id | `semantic/prepare.py:956–985` | Root, model digest, profile, compiler and analysis library versions, every source and dependency artifact digest (the native capture, generators, the PDF lowering contract), vocabularies | Content (over everything supplied) | Everything keyed by release: cut pins, established validity, runtime attestation, admission | A new release must be prepared and admitted |
| 4 | Kind, definition, eligibility, implementation-slice and recipe fingerprints | `semantic/data_operation_identity.py:349–414`; `semantic/data_operation_compilation.py:1973–2219` | Compiled model records; the sliced source graph; opaque boundary digests | Model (plus boundaries) | Native completion revision equality; acquisition (`semantic/data_operation_admission.py:324–347`) | Refuse |
| 5 | Opaque boundary assets | `semantic/characterization_ports.py:47–193`; `semantic/formal_products.py:676–756`; `semantic/rich_invocations.py:15–70` | Whole files, whole model YAML and library versions; rich assets use a projection of the parsed module (`semantic/python_module_projection.py:111–120`) | Hand | Implementation slice, then recipe ([DA-069](execution-fit.md#da-069)) | Prior derivations are not reusable |
| 6 | Port generator custody | `semantic/data_operation_artifacts.py:22–39, 73–81` | Eight generator modules | Hand | Release dependencies; compile refuses if the installed generator differs | Refuse |
| 7 | Runtime artifact and attestation | `semantic/data_operation_runtime.py:88–120, 180–213` | Python version and every supplied executable input; the attestation adds release, profile and observation | Content | Native retained manifest and archive digests (`semantic/data_operation_admission.py:343–347`) | Refuse |
| 8 | PDF lowering contract | `semantic/pdf_lowering.py:33–104, 168–256` | 70 listed files, boundary sources, generated schemas and codecs, 14 libraries | Hand ([DA-082](execution-fit.md#da-082)) | Release, producer contract, streaming, oracle capture, receipt `lowering_identity` | Refuse ("restart required" or "differs") |
| 9 | Served-read implementation | `serve/rich_queries.py:71–105`; `_query_custody.py:17–127`; `semantic/demand_queries.py:117–124` | Listed module digests, nine libraries, the request schema | Hand ([DA-076](served-claims.md#da-076)) | Cursors, `resource_handle`, query-cache keys | Refuse to resume; in-process drift refuses and needs a restart |
| 10 | Cut identity | `semantic/demand_results.py:64–104` | All native pins, including the read instance, snapshot and clock | Content | Cursors, `expected_cut`, cache keys ([DA-075](execution-fit.md#da-075)) | Refuse continuation |
| 11 | Read kernel pin | `semantic/demand_result_native.py:209`; `semantic/data_read_boundary_native.py:84–92` | The kernel digest at acquisition | As the kernel digest | Read presence | Reacquire |
| 12 | Semantic request key | `semantic/binding_admission_native.py:213`; `semantic/request_attachment_native.py:1024–1539` | Request meaning only; no release and no runtime | Model | Request reuse across releases | A new request |
| 13 | Inputs watermark | `semantic/data_operation_projections.py:1809–1935` | Uses of transitive prerequisite operations (by source), populations, originals, source sets, trust snapshot, kernel | Model at operation granularity, not role ([DA-078](execution-fit.md#da-078)) | Planner skip (`semantic/data_operation_demands.py:732–738`) | Re-bind |
| 14 | Completion seal | `semantic/data_completion_settlement_native.py:509–528` | Kernel, request, generation, release, recipe, runtime, payload digest, trust | Mixed | Publication battery skip | Run the battery |
| 15 | Receipt validating kernel | `semantic/data_derivation_native.py:614`; gate at `semantic/data_completion_settlement_native.py:661–676` | The kernel at publication | As the kernel digest | Seven family validators | Replay, not recorded |
| 16 | Physical id; deployment-admission receipt; frozen descriptor expectation (three identities) | `schema/physical.py:142–151`; `semantic/native_admission_release.py:31–67`; `semantic/execution_admission.py:285–420` | The physical YAML closure; descriptor bytes; the migration revision file digest with mtime and ctime | Content | Admission, catalog guard | Refuse |
| 17 | Wire contract digest | `semantic/data_operation_wire.py:46–60`; checked per call at `semantic/data_operation_storage.py:1111` | The protocol YAML or the captured protocol | Content | Every native invocation envelope | Refuse |
| 18 | Scientific policy | `semantic/scientific_evidence.py:192–255`; `semantic/rich_policy_binding.py:22–30` | A hand-written description of the kernel | Hand ([DA-077](served-claims.md#da-077)) | Release check, rich context | Refuse |
| 19 | Model-change compilation fingerprint | `schema/model_change.py:323–440` | Every `.py`, `.sql`, `.yaml`, `.json`, `.lark` and template file in both the selected and the running package (generated outputs and `model/` excluded), the union of byte, analysis and deployment libraries with eight tools, the request, bases and acquired inputs | Content (whole tree) | Candidate file check (`schema/model_deployment.py:582–604`); `cli/model.py:1676, 1925` | "Prepare a fresh preview" |
| 20 | Generator fingerprint; worktree head; Python version | `schema/model_change.py:313–320, 1066–1077` | All `schema/*.py`; the worktree head | Content | Preview and candidate checks | Refuse |
| 21 | Source-migration preparation and implementation identity | `schema/source_migrations.py:168–198` | Every file under `semantic/` and `model/semantic/` with eight libraries; two modules with two libraries | Content (whole tree) | `check_source_migration` (`:701–712`) | Refuse |
| 22 | File custody; query custody | `semantic/file_custody.py:20, 79–137`; `_query_custody.py:136–260` | A path's digest with its stat identity; module bytes at import | Content | The lowering list, model assets, served reads | Refuse; restart |

What the inventory shows:

- **Only three identities are derived from model declarations**: the request key (12), the
  per-operation fingerprints (4) and, at a coarser grain than the model offers, the watermark
  (13). These are also the ones on which reuse is exact.
- **Six are hand-maintained**: the kernel capture, the boundary asset lists, the generator
  list, the lowering list, the served-read lists and the scientific policy. Each is a
  hand-written answer to "which code determines this artifact". A hand list can be wrong in
  either direction, and two of them are established as both too broad and too narrow
  (DA-082) or too narrow (DA-076).
- **Three are whole-content** (the release id, the model-change fingerprints and the
  source-migration identity)
  and so over-broad by construction: any byte supplied changes them. That is safe, and it is
  why an unrelated edit asks for a new release or a fresh preview.
- **Mismatch refuses, or redoes the whole unit.** No identity in the table narrows the redone
  work to what actually changed, and the replay gated by the receipt's kernel digest (1, 15)
  does not record that it succeeded.
- **A finer identity exists and is unused**: each program's generated bytes are captured, and
  only one of them is used as a digest (2).

<a id="analytical"></a>

## Analytical and set-wise computation

**Interface-checked by source inspection, 2026-11-18**, source `d78c98765`. This section
records where derived, aggregating, joining and graph-shaped work runs today. It is a map of
facts for the review that follows; it makes no judgment about where any item should run, and
no size or timing was measured. "Bound to PostgreSQL authority" means the computation needs
the database transaction itself: snapshot visibility, trust locks, the caller's principal, or
writes.

| Kind of work | Where it runs | Bound to PostgreSQL authority, and why | Sites |
|---|---|---|---|
| Validity closure and its fixpoint | PostgreSQL: a generated recursive query followed by a PL/pgSQL loop | Yes: visibility by transaction id relative to the read boundary, the revocation table, the caller's principal | `semantic/data_validity_native.py:471–610`; the node check is used by about 20 native programs and the closure once per read page |
| Support walk, watermark prerequisites, dependency and record-tree walks | PostgreSQL: generated recursive queries (25 Core sites, plus 5 in hand-written SQL and SQLite) | Yes: the same visibility and locks | `semantic/data_operation_projections.py:132–242, 1809–1840`; listed per program in the analytical map lane |
| Authorization, selection, keyset ordering, full-text ranking | PostgreSQL programs | Yes | `semantic/data_operation_projections.py:1938–1992`; `semantic/pdf_search_native.py:783–837` |
| Contextual mutual neighbours | PostgreSQL: a hand-written SQL function over pgvector | No: a stable function of its JSON arguments; its numerical backend is pinned and checked | `sql/contextual_neighborhood.sql`; `semantic/contextual_neighborhood.py:30–55` |
| Row filtering, ordinal paging, joins of already-acquired pages, byte budgeting, response shaping for served reads | Python generators and dictionaries, with the one `cachetools` cache | Acquisition is bound and is repeated on every call; the shaping is a pure function of the acquired page | `semantic/demand_queries.py:57–260`; `semantic/selected_query_cache.py`; `serve/selected_contributions.py:61–330`; `semantic/rich_queries.py:196–586` |
| Change impact, declared graph inspection, rich relation walks, the semantic operation graph | Python with NetworkX, over a SQLite scratch index or the compiled model | Acquisition is bound; the analysis is pure | `semantic/change_impact.py:157–500`; `semantic/graph_inspection.py:130–300`; `semantic/rich_statistics_queries.py:188–264`; `semantic/data_operation_identity.py:201–330` |
| Rich-rule occurrence views (same slot, alternative of, declared projections) | DuckDB relations over Arrow tables built from Python objects; the rule loop, premise accumulation and equivalence components stay in Python | No | `semantic/analytical_kernels.py:204–309`; `semantic/rich_rule_evaluation.py:325–940` |
| Companion export inventory and multiset comparison | DuckDB over Parquet files | No: a pure function of verified files | `serve/companion_export.py:403–606` |
| PDF candidate geometry (box normalization, containment and intersection joins, window ambiguity) | DuckDB over Arrow batches | No | `ingest/pdf_candidate_geometry.py:75–313` |
| Recognition replay ordering | DuckDB external sort with a spill directory | No | `ingest/pdf_stream_reconciliation.py:293–340` |
| Artifact identity scoring | Splink on DuckDB, after pairwise candidate generation in Python | No | `semantic/artifact_identity.py:296–395, 452–585` |
| Evaluation and scoring (assignment, graph matching, bootstrap, fitting, sampling), scientific comparison, record interpretation | Python with numpy, scipy, scikit-learn and NetworkX over acquired values | No, except that operation fitting reads one population count through Core | `evaluate/*`; `semantic/scientific_evidence.py:442–686, 1217–1339`; `semantic/record_interpretation.py:349–743` |
| Export and verification row work (logical row digests, dedup, per-page joins) | Python loops over Arrow batches; SQLite as an out-of-core store in five modules | The export snapshot is bound; verification is pure | `serve/companion_export.py:99–395`; `serve/demand_export.py:98–415`; `serve/native_source.py:822–1086` |

**DuckDB use, as facts.** DuckDB is imported by six modules. Every connection is in-memory,
created per invocation and closed at the end of its scope; there is no shared or persistent
connection, no extension loading and no attachment to PostgreSQL. All use is through the
relational and expression API with no SQL text. No operation moved from PostgreSQL to DuckDB
in the conversion: these uses existed at `fbd3f2a98` as DuckDB SQL strings, and commits
`ef6a7b13f`, `048d5ab17` and `dbe22b899` rewrote them onto the relational API. Three of the
five use sites declare their Arrow input schemas by hand
([DA-086](semantic-model-and-authority.md#da-086)); the companion export's schema is derived
from the model. Two rich kernels have no production caller and the analytics settings for
threads and memory are not read ([DA-080](boundaries-and-composition.md#da-080)).

**Transports between PostgreSQL and analysis.** There are three, and they do not overlap:

1. SQLAlchemy Core over psycopg, the default for every serving path. Rows arrive as Python
   objects, and a native program typically returns one JSON document per call
   (`core/db/store.py`).
2. ADBC, which yields Arrow record batches, used by exactly two callers: the companion export,
   through a second session that imports the read snapshot
   (`serve/companion_export.py:131–200`), and catalog description
   (`serve/database_description.py:235–263`).
3. Arrow into PostgreSQL by binary COPY, used for the release archive, PDF staging and PDF
   publication (`semantic/arrow_transfer.py:134–171`).

There is no path that hands a PostgreSQL result to DuckDB directly. Python-built Arrow tables
enter DuckDB through `from_arrow`, files through `from_parquet`, and Arrow produced from
PostgreSQL leaves only through the companion ADBC path.

**Limits of this map.** Realistic row counts were not established; only declared bounds were
read (for example 100,000 members for a rich graph index and 2 GB for DuckDB). The generated
PDF call module and several native-program generators were not read beyond their recursive
queries, so further set-wise PostgreSQL programs may exist. Whether the validity closure is
evaluated once or per row inside the read-page plan was not verified from a query plan.

<a id="pe-state"></a>

## State of the production-efficiency mechanisms in source

Source-level state at `fbd3f2a98`, 2026-11-17. The
[DDO plan](../../plans/declared-data-operations_2026-11-12.md) owns status, and native
deployment of several of these is not yet adopted. "Implemented" here means present in source,
not qualified. The refresh of 2026-11-18 did not re-read this table as a subject. A row was
updated only where a lane re-read the finding it links to, and says so; every other row keeps
its 2026-11-17 date.

| Finding | State in source | Residual observed |
|---|---|---|
| PE-F01, F02 | Implemented at the examined sites | — |
| PE-F03 | Implemented for read paths | None. Execution derives the release at registration and once per host basis, which the review records as deliberate |
| PE-F04 | Implemented | — |
| PE-F05 | Partly | Set evaluator exists; scalar per-item and per-step calls remain, the fixpoint scans all edges per fact per iteration and evaluates the edge function twice per node (2026-11-17; the closure is now the generated program at `semantic/data_validity_native.py:471–610` and its loop was not re-assessed). Re-read 2026-11-18: family membership is still assigned by name list, now two Python tuples ([DA-070](semantic-model-and-authority.md#da-070)) |
| PE-F06 | Partly | Re-read 2026-11-18: the waiting-obligation skip is still coarse, and the kernel digest is an established component of the watermark ([DA-078](execution-fit.md#da-078)). Python and native both evaluate the binding (2026-11-17) |
| PE-F07 | Implemented | — |
| PE-F08 | Declared in the physical model | — |
| PE-F09 | Partly | (a) prepared-kernel ports recompute their asset artifacts from disk on every verification, including each blocked submit tick, so the work grows with waiting time (`semantic/characterization_ports.py:502–550, 882–991`; `semantic/data_operation_cpu.py:150–171`; `core/work.py:137–142`); (b) binding re-parses artifacts ([DA-033](execution-fit.md#da-033); re-read 2026-11-18, stands at `semantic/binding_admission_native.py:232–251`); (c) the seal key is the whole capture ([DA-068](execution-fit.md#da-068); re-read 2026-11-18, stands and wider); (d) established validity is keyed by release; (e) found 2026-11-18: the native capture is rebuilt at every port acquisition and recheck ([DA-083](execution-fit.md#da-083)) |
| PE-F10 | Implemented for attach and claim | Discovery expansion is still per population |
| PE-F11 | Implemented (two-stage admission) | — |
| PE-F12 | Partly | Member validation is still per member, including on replay |
| PE-F13 | Implemented (spot-checked) | Test evidence gap: [DTA-046](../test-audit/evidence-and-discrimination.md#dta-046) |
| PE-F14 | Mostly | Selected-item hydration still reads per record |
| PE-F15, F18, F22, F29 | Implemented | — |
| PE-F16 | Partly | The evaluator MCP server and the render fallback still open an engine per call (`intervene/selected_assessment_server.py:45–80`), which also defeats the per-engine archive cache |
| PE-F17 | Partly | [DA-075](execution-fit.md#da-075), re-read 2026-11-18 and unchanged; change impact rebuilds the whole comparison for every page (`semantic/change_impact.py:687–777`; that file has no commit since `fbd3f2a98`) |
| PE-F19 | Implemented, with limits | Native models still retire per run at the default keep-warm of 0; Chandra is outside the host ([DA-058](execution-fit.md#da-058)) |
| PE-F20, F21, F25, F28 | Implemented | Test evidence gaps: [DTA-041](../test-audit/support-structure.md#dta-041), [DTA-044](../test-audit/evidence-and-discrimination.md#dta-044) |
| PE-F24 | Partly | Not examined beyond the candidate reusing the preview capsule |
| PE-F26 | Implemented in source | The oracle skip has no discriminating test ([DTA-044](../test-audit/evidence-and-discrimination.md#dta-044)) |
| PE-F30 | Implemented | No two-settler concurrency case was found; the settlement SQL was not read for this |
| PE-F31 | Partly | Re-read 2026-11-18: ten of fourteen orphan SQL files are gone, six files now have no loader, and new unconsumed items appeared ([DA-080](boundaries-and-composition.md#da-080)) |

<a id="planned-change"></a>

## Planned change not yet in source

**Superseded by the refresh of 2026-11-18.** This section mapped the then-remaining steps of
the model-owned SQL conversion onto the findings they would affect, as plan and not as
evidence. Most of those steps have since landed, and the refresh read the source at
`d78c98765`. The conversion as a whole is still open: ADR-0131 and the DDO plan record
residual SQL authoring (native admission and privileges, scientific routines, administrative
paths) as remaining work. The table keeps each step and the condition recorded on 2026-11-17, and adds what
the refresh found. The plan remains owned by the
[PostgreSQL companion](../../plans/declared-data-operations/postgresql-realization-and-retirement.md#model-owned-sql-authoring).
Test-account entries (`DTA`) were not re-read and keep their 2026-11-17 statements.

| Planned step | Condition recorded on 2026-11-17 | What the refresh found at `d78c98765` |
|---|---|---|
| Shared bytes and PDF publication as typed programs; new generators captured in lowering and certification custody; controlled fixtures moved through the certified producer; fixture-only occurrence replay writer deleted | [DA-074](native-integrity.md#da-074) is corrected only if shared-stream trigger membership is read from a declaration. [DA-068](execution-fit.md#da-068) widens as generators join custody | Landed as typed programs. Trigger membership is still chosen by relation name, although the model declares the class that would select it (DA-074 stands). DA-068 is wider again, and the lowering list that the generators joined is its own finding ([DA-082](execution-fit.md#da-082)): it grew from about 56 to 70 hand entries. `pdf_publication_native.py` still holds hand-written view and function declarations ([DA-084](boundaries-and-composition.md#da-084)). [DTA-041](../test-audit/support-structure.md#dta-041), [DTA-035](../test-audit/retirement-transfer.md#dta-035) and [DTA-044](../test-audit/evidence-and-discrimination.md#dta-044) were not re-read |
| DDO kernels and readers through Core and a finite native program compiler; body markers, substring rewrites and duplicate field lists replaced | [DA-070](semantic-model-and-authority.md#da-070) is corrected only if the compiler takes family membership from the model and refuses an undeclared operation; a Python transcription keeps the cause. [DA-071](semantic-model-and-authority.md#da-071) goes from three encodings to two at best | Largely landed, and `data_operations.sql` is deleted. The outcome for DA-070 is the transcription: two Python tuples, both failing open. DA-071 still has three encodings, because the validity copy became a typed program rather than being derived. Markers and rewrites were reduced, not removed: eleven splice sites into hand-written bodies and two patches of generated text remain (DA-084, [DA-081](semantic-model-and-authority.md#da-081)). The contextual, definition, rich and artifact family layer is not yet converted. [DTA-047](../test-audit/execution-and-qualification.md#dta-047) was not re-read |
| Native admission and administration: catalog admission, archive and activation guards, runtime bindings, scientific policy checks, scoring wrappers; generated declarations, triggers, roles and ACLs; host bootstrap and test provisioning through shared builders; orphan SQL removed | DA-074 is corrected only if role sets and grants come from declarations. [DA-033](execution-fit.md#da-033) changes footprint. Thirteen orphan files remain ([DA-080](boundaries-and-composition.md#da-080)) | Partly landed; the plan lists native admission and privileges as remaining work. Release preconditions and receipts are typed, and host bootstrap renders its statements from parsed nodes; the enforcing admission function is still the hand-written `admission.sql`, with typed fragments spliced in at markers (DA-084). Roles and grants are still code: 176 occurrences of role names in 39 modules, and every `ph:read_roles` annotation is empty (DA-074 stands, wider). DA-033 changed footprint and its substance stands. Ten of the fourteen orphan files are gone and six files now have no loader (DA-080). [DTA-038](../test-audit/execution-and-qualification.md#dta-038) and [DTA-039](../test-audit/execution-and-qualification.md#dta-039) were not re-read |
| DuckDB 2.0 relations for the rich evaluator, companion export and PDF derived analysis | [DA-077](served-claims.md#da-077) is corrected only if the archived scientific recipe is derived from the kernel's parameters | Landed as a rewrite of existing DuckDB SQL strings onto the relational API; nothing moved from PostgreSQL. DA-077 is untouched and stands, with a third comparison site found. Three modules declare their input schemas by hand ([DA-086](semantic-model-and-authority.md#da-086)), and two kernels have no production caller (DA-080) |

The observation recorded across the steps on 2026-11-17 was that the plan text committed to
typed programs and generated statements and did not state that membership and family facts
would be read from the model, which is the condition on which the model-restatement findings
close. The source matches that reading: programs are typed, and the membership and
family facts are still hand lists.

## Unresolved premises

- Whether a content-based key is sound for served results. One consumer already relies on it ([DA-075](execution-fit.md#da-075)).
- Whether opaque-boundary digests also capture third-party model weights, so that reuse across
  runtimes cannot return a result a different library would change. Not examined.
- Whether equal outputs stop recomputation below the formal and construction operations
  ([DA-069](execution-fit.md#da-069)).
- Reached node counts for validity closure and watermark sets in the book run (the open premise
  of PE-F05).
- Whether the release capsule fits the 256 MiB idle bound. If it does not, the host evicts the
  basis after every run and the process-scoped host gives no reuse.
- Every unpinned read writes durable read and scope rows; no pruning was found. Hypothesis
  only, recorded on 2026-11-17 against the SQL file that has since been replaced; the read
  acquisition generator is `semantic/demand_result_native.py` and the question was not re-read.
- Added 2026-11-18: how often the native capture is rebuilt in a real run and what one rebuild
  costs ([DA-083](execution-fit.md#da-083)); whether preparation ever runs inside a long-lived
  process; whether `formal/execution-custody` enters the implementation revision
  ([DA-069](execution-fit.md#da-069)); which hand-written PostgreSQL bodies reference relations
  or columns ([DA-084](boundaries-and-composition.md#da-084)); and whether the per-consumer
  model closures ever differ in result ([DA-085](semantic-model-and-authority.md#da-085)).

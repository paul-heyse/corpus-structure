# The domain model and execution, across production and tests

**Interface-checked by source inspection.** This page was written on 2026-11-17 at source
`fbd3f2a98` as the integrated analysis of a joint refresh of the [broad account](README.md) and
the [test account](../test-audit/README.md), with two priorities set by the operator: the
comprehensive domain data model, and efficiency of execution. On 2026-11-18 the production
side was updated at source `5139eaba3` ([update](README.md#update-2026-11-18-5139eaba3)): the
shared-causes table, the cache inventory, the identity inventory and the analytical section
below are at that source, and each other section says which date it carries. The test account
was refreshed separately on 2026-11-18 by another engagement
([its refresh](../test-audit/README.md#tdm-refresh-2026-11-18)); the `DTA` entries on this page
were not re-read against it and keep their 2026-11-17 statements. The page holds analysis,
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
   99 modules and six library versions stands for "the kernel that validated this".
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

**What the update of 2026-11-18 at `5139eaba3` adds.** The conversion of hand-written
PostgreSQL to typed programs is now almost complete as far as statement text goes:
hand-written SQL inside Python fell from about 2,430 lines to about 180, and the sixteen
`.sql` files (about 1,290 lines) went to none, so about 3,700 lines became about 180 by two
counting methods that agree. What is left is mostly permitted control SQL
and SQLite ([DA-084](boundaries-and-composition.md#da-084)). Relations and columns in every
converted module come from the captured model, so a renamed table or column fails at
generation. That is a real gain. It did not move any of the hand lists of cause 2 into the
model. The admission generators take only table metadata as input, so the facts that identify
an operation, a role or a state are still strings written in each generator, and an operation
missing from a family list is still treated as valid, now also through early returns in
several family guards ([DA-070](semantic-model-and-authority.md#da-070)). The observation of
the previous refresh holds in sharper form: the conversion changed how statements are written,
and where relations and columns come from, but not where membership facts come from. Cause 1
became concrete in one place: native revision N29 changed no generated statement and
restamped two digests in installed objects ([DA-068](execution-fit.md#da-068)). This is the
consequence, predicted in the previous refresh, of converting before declaring; it is not a
divergence from ADR-0131, whose decision governs physical types and call correspondence. A
fourth recurring thing, found in the
previous refresh, stands:

4. **Derived artifacts with no holder and no registry.** The native program set is
   regenerated from scratch at every admission-side call ([DA-083](execution-fit.md#da-083)).
   It is also listed by hand in six places, and once rendered it is handled as text that is
   concatenated, patched and parsed again to recover facts the program objects held
   ([DA-081](semantic-model-and-authority.md#da-081)).

## Shared causes and where their findings live

Production entries are at `5139eaba3` (2026-11-18); test entries are at `fbd3f2a98`
(2026-11-17).

| Cause | Production | Tests |
|---|---|---|
| **Identity broader than its premise**: valid work discarded on unrelated change | [DA-068](execution-fit.md#da-068) native kernel digest, with one observed instance of digest-only churn in installed objects; [DA-069](execution-fit.md#da-069) opaque-boundary implementation identity; [DA-075](execution-fit.md#da-075) cache key includes the read instance; [DA-078](execution-fit.md#da-078) readiness watermark; [DA-082](execution-fit.md#da-082) PDF lowering list (shared infrastructure listed whole) | [DTA-040](../test-audit/execution-and-qualification.md#dta-040) per-test path in recipe identity; [DTA-038](../test-audit/execution-and-qualification.md#dta-038) deployment key includes the whole lockfile and artifact mtimes |
| **Identity narrower than its premise**: stale work can pass | [DA-076](served-claims.md#da-076) read implementation allowlist; [DA-077](served-claims.md#da-077) scientific policy description; [DA-082](execution-fit.md#da-082) PDF lowering list (thirty imported modules unlisted, one level deep); [DA-028](semantic-model-and-authority.md#da-028) source demand reads the live `slices.yaml`, not the release's copy | [DTA-038](../test-audit/execution-and-qualification.md#dta-038) deployment key misses modules run by upgrade bodies |
| **A model fact restated by hand** | No declaration exists and a hand list is the only statement: [DA-070](semantic-model-and-authority.md#da-070) twelve validity-family lists, with early-return guards; [DA-071](semantic-model-and-authority.md#da-071) support graph three times; [DA-073](semantic-model-and-authority.md#da-073) release composition; [DA-074](native-integrity.md#da-074) guard, role and grant lists; [DA-081](semantic-model-and-authority.md#da-081) no typed registry of programs and generated outputs, with the text handoff as its footprint. A declaration or typed source exists and is not read: [DA-086](semantic-model-and-authority.md#da-086) literals in generators and analytical modules, with [DA-001](semantic-model-and-authority.md#da-001) and [DA-004](semantic-model-and-authority.md#da-004) on the semantic side. Two generations of the model: [DA-072](semantic-model-and-authority.md#da-072) | [DTA-037](../test-audit/retirement-transfer.md#dta-037) fixture-name lists; [DTA-041](../test-audit/support-structure.md#dta-041) converter copies; [DTA-042](../test-audit/support-structure.md#dta-042) pack composition; [DTA-043](../test-audit/support-structure.md#dta-043) copied reservation formula; [DTA-033](../test-audit/evidence-and-discrimination.md#dta-033) vector input rebuilt per consumer |
| **No one compiled object for cross-view facts to be derived from** | [DA-085](semantic-model-and-authority.md#da-085) one LinkML composition per consumer; constraints as JSON strings in annotations; kernel generators receive table metadata only | — |
| **A value refused late or by the wrong failure** | [DA-040](structure-and-invariants.md#da-040) unbounded decimal expansion; [DA-013](structure-and-invariants.md#da-013) prose refusals, with [DA-079](boundaries-and-composition.md#da-079) as an instance | — |
| **Established assurance re-proved instead of carried** | [DA-033](execution-fit.md#da-033) release content per admission and per binding; residuals of PE-F09 [below](#pe-state) | [DTA-039](../test-audit/execution-and-qualification.md#dta-039) whole migration chain per key miss; repeated head and seed verification |
| **A derived artifact rebuilt because nothing holds it** | [DA-083](execution-fit.md#da-083) native capture per admission-side call; the scientific policy recipe per comparison ([DA-077](served-claims.md#da-077)) | — |
| **Reuse without discriminating evidence** | The mechanisms are production's; the gap is in tests | [DTA-044](../test-audit/evidence-and-discrimination.md#dta-044) skips tested only on the equal path; [DTA-045](../test-audit/evidence-and-discrimination.md#dta-045) profile check asserted against a double; [DTA-046](../test-audit/evidence-and-discrimination.md#dta-046) batch attribution invisible |
| **Superseded machinery kept, and declarations that govern nothing** | [DA-080](boundaries-and-composition.md#da-080), including a preview explanation that still walks a removed directory, release machinery with no supplier and two unconsumed migration trees; [DA-020](boundaries-and-composition.md#da-020) unread settings | [DTA-037](../test-audit/retirement-transfer.md#dta-037), [DTA-035](../test-audit/retirement-transfer.md#dta-035) |
| **Residue of the SQL conversion** | [DA-084](boundaries-and-composition.md#da-084): one small item of hand-written PostgreSQL; its former consequence moved to DA-070 and DA-074 | — |

Each cause has one primary finding per manifestation; where a production cause explains a test
manifestation, the test account links to the production finding instead of opening its own
(for example, tests of unused evaluation modules are footprint of DA-080).

Four production findings are hand-kept answers to "which code determines this artifact":
DA-068, DA-069, DA-082 and DA-076. DA-069 and the too-broad half of DA-082 are the closest
pair, since both take whole files and library versions as an implementation identity.

One interaction stands from the previous refresh and was exercised in the range: several files
feed overlapping identities. `semantic/native_program.py`, `semantic/native_source_view.py`,
`semantic/identity.py`, `semantic/metadata.py` and `schema/physical.py` sit in two or more of
the kernel capture, the PDF search renderer list, the PDF lowering list and the served-read
lists, and through dependencies in the release id; the whole tree feeds the model-change
preview and source-migration fingerprints. The edit to `native_source_view.py` that restamped
the kernel digest at native revision N29 moved the renderer digest, the kernel digest and the served-read identity
together.

## Model facts that could key, scope or invalidate work

These are observations about what the model already makes available, paired with what the work
is keyed by today. They are leads for a later review, not selected changes.

| Model fact (already declared or compiled) | Work it could key or scope | Keyed by today |
|---|---|---|
| Per-operation recipe, definition and eligibility identities; implementation-slice fingerprint | Which definitions a new release actually changes; implementation identity of construction and formal operations | `release_id` over every input file (`semantic/prepare.py:986`); whole files and library versions ([DA-069](execution-fit.md#da-069)) |
| The source of each family's validators (captured per module), each program's exact generated bytes (captured as `native/<name>.sql`), and the native digest the release already carries | Completion seal and receipt validation identity; separating "generated SQL changed" from "a generator or library changed" | The whole native capture ([DA-068](execution-fit.md#da-068)) |
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

Production rows were rebuilt on 2026-11-18 at `5139eaba3`; the last column marks each against
the inventory at `d78c98765`. Counts by search at each commit: `functools` caches 94 then 96;
`cached_property` sites 75 then 78; one cache built on `cachetools`
(`semantic/selected_query_cache.py:12`). The repository pins `cachetools` 7.2.7; the
[library overview](../../libraries/analytical_infrastructure/cachetools.md) describes 8.0.
Test-side rows are from 2026-11-17 and were not re-read.

| Holder | Key | Omits | Bound | Lifetime and invalidation | Threads and processes; identical misses | Mark |
|---|---|---|---|---|---|---|
| `SELECTED_QUERY_CACHE` (`semantic/selected_query_cache.py:58–86`) | Cut identity (five consumers) or frontier stamps (exclusions), with implementation, selection and budgets | Nothing needed for safety; the read instance makes it over-specific ([DA-075](execution-fit.md#da-075)) | 32 MiB, 128 entries, 8 MiB and 4,096 rows per entry | Process; new key only | `RLock`; concurrent identical misses both compute; the CLI's process per page never hits | unchanged |
| `_installed_read_basis` (`serve/rich_queries.py:71`) | Contract type, source names, profile, libraries | File content (query custody catches drift) | 64 | Process | `lru_cache` | unchanged |
| `_current_boundary`, `_implementation_sources` (`semantic/pdf_lowering.py:107, 259`) | None | — | 1 each | Process; custody check on each call | Double compute on a race | unchanged |
| `_prepared_lowering_sources` (`semantic/pdf_lowering.py:168`) | Boundary source tuple | — | 4 | Process | Retains prepared PDF releases | unchanged |
| `_captured_projection_inputs`, `captured_projection` (`semantic/companion_projection.py:561, 620`) | The PDF domain contract (content), the metadata object, the family | Metadata is keyed by object identity | 4 and 8 | Process | `lru_cache`; double compute on a race | new (sound, content-keyed) |
| `_prepare_release_cached` (`semantic/prepare.py:600`) | Bundle, dependencies, profile, compiler stack | — | 8 | Process | Double compute on a race | unchanged |
| `_bound_data_operation_calls` and the bound model (`semantic/data_operation_admission.py:109`) | Model bytes, correspondence | — | 8 | Process | — | unchanged |
| Deployment expectation caches (`semantic/execution_admission.py`) | Revision identities; file digest with mtime and ctime | — | `lru_cache` bounds | Process | — | changed (the fingerprint query is generated) |
| Wire protocol and validators (`semantic/data_operation_wire.py:47, 53, 262, 489, 525, 560`) | None, or the whole captured source tuple | — | 1 to 256 | Process | Thread-safe; a rebuilt capture hits only after every artifact is hashed (inferred; [DA-083](execution-fit.md#da-083)) | unchanged |
| Static preparation and model decode (`semantic/data_operation_static_preparation.py:66`; `semantic/data_operation_model.py:1206`) | Exact captured bytes | — | 8 to 256 | Process | Thread-safe | unchanged (no commit) |
| `_ambient_protocol*`; `trusted_pdf_context`; `_report_*` | None: first read in the process | — | 1 | Process restart; a mismatch refuses by digest | — | unchanged (2026-11-17, not re-read) |
| CPU call descriptors (`semantic/data_operation_cpu.py:189`) | The serialized call without arguments | — | 64 | Worker process; asset custody checked per use | Per worker | unchanged (not listed before) |
| Worker releases (`semantic/cpu_execution.py:150–174, 226, 284`) | Digest of the capsule reference | — | Unbounded within a worker's life | Cleared at worker init; one entry per distinct capsule | Per worker; the decoded release is outside the byte budget | changed (the shared request global beside it was removed, `5c5443d16`) |
| Coordinator capsules (`semantic/cpu_execution.py:707, 746–800`) | Release id, checked by capsule digest | — | Owned-byte budget | Invocation | `RLock` | unchanged |
| File custody (`semantic/file_custody.py:83–137`) | Path and digest; stat identity | — | Unbounded (finite files) | A stat change or a 2 s racy window re-hashes; changed bytes refuse | `RLock` | unchanged (new consumer: native selection assets) |
| Query custody (`_query_custody.py:136–260`) | Module | — | Unbounded | A reload refuses | `RLock` | unchanged |
| `_OPEN_CACHE` (`semantic/archive_reader.py:34, 394–434`) | Archive header and library versions, per engine | — | 8 per engine | Header re-read each call; dies with the engine | `RLock` | unchanged in substance (`3ba5daa84` removed dead adapter code) |
| Execution-host bases (`orchestrate/execution_host.py:186–272`) | Engine, release, runtime, root, run determinants | — | 2 idle, 256 MiB | Header and runtime re-read on acquire | Run lock ([DA-079](boundaries-and-composition.md#da-079)) | unchanged |
| Per-object memos: `semantic_id` on formal, construction and sentence products (`semantic/formal_products.py:150` and siblings) | The object | — | Object life | Immutable objects | — | new (sound) |
| Math parsers and memo (`methods/math/grammar.py`) | Macro classification; (latex, kind, table, context) | — | Parsers **unbounded**; memo 8,192 | None | Main thread; now lives across runs in long-lived workers | unchanged (no commit to the owner) |
| Encoder, spaCy pipeline, compiled GLiNER pack; native residency (`methods/native_host.py`); record reader caches | As recorded on 2026-11-17 | — | As recorded | As recorded | As recorded | unchanged (no commit to the owners) |
| DuckDB connections | — | — | Per invocation | Closed at exit | No holder, which is appropriate | unchanged |
| Test head database (`scripts/native_test_support.py`) | Deployment key | — | Three retained | Key change; failed verification retires | Advisory locks | 2026-11-17; see the test account |
| Scenario seeds (`scripts/native_scenario_seeds.py`) | Recipe value and head | — | Unbounded until session end | Head replacement | `RLock`, per worker | 2026-11-17; see the test account |
| Test-side `functools` helpers (about 50) | Mostly none | — | 1 each, per worker | None | — | 2026-11-17 |

**Repeated expensive work with no holder** (counts are read from call paths, not timed):

| Work | Where it repeats | Finding | Mark |
|---|---|---|---|
| The native capture: about 46 generators (now larger), a physical compile when none is supplied, a schema view, about 110 file reads | Twice per acquisition, recheck and publication-port acquisition; three times per definition admission; once per preparation, regeneration, candidate build and demand export; at least twice per preview | [DA-083](execution-fit.md#da-083) | changed (larger per rebuild) |
| Physical compile at import of `semantic/metadata.py`, and inside captures | Every importing process | [DA-083](execution-fit.md#da-083) | unchanged |
| Release content re-proof in SQL (archive parse, byte hashes, prepared-bytes decode, authored-SQL hashes, model hash, projection decode) | Every `require_native_execution` | [DA-033](execution-fit.md#da-033). Assurance that is not carried, not a missing cache | changed footprint (generated) |
| Per-binding artifact parse | Each binding and population selection | [DA-033](execution-fit.md#da-033) | unchanged |
| Digest-only changes to installed objects in a native revision | An edit to any of 99 captured modules or six libraries restamps the kernel digest; an edit to any of the 48 authoring inputs restamps the execution-contract descriptor, even when the generated output is byte-identical | [DA-068](execution-fit.md#da-068) | new evidence (N28 to N29: no generated statement changed) |
| Scientific policy recipe | Three comparison sites | [DA-077](served-claims.md#da-077) | unchanged |
| Parsing of generated SQL text | Per statement at render; per selected function name at installation; again for the inventory, the entry-point rename and twelve modules that re-parse their own output | [DA-081](semantic-model-and-authority.md#da-081) | unchanged |
| Frozen catalog verification rebuilt from the frozen guard (`semantic/native_admission.py:85–110`) | Each deployment-catalog verification (deployment and the archive fence) | — | new; low consequence, not on the acquisition path |

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
- **The most expensive derived artifact has no holder at all.** The native capture is rebuilt
  on every admission-side use, and unlike the PDF lowering sources it is not under file
  custody ([DA-083](execution-fit.md#da-083)). The caches that would serve it downstream key
  on the whole capture tuple, so they do not spare the rebuild. The holders added in the range
  (the companion projection, per-object memos) are sound and are elsewhere.

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

**Interface-checked by source inspection, 2026-11-18**, source `5139eaba3`; rebuilt by the
identity lane. An identity here is a digest or key that decides whether earlier work, an
installed object or a continued request is still acceptable. "Basis" says how its membership
is decided: *model* means derived from model declarations or the compiled model; *content*
means derived from whatever bytes are supplied, with no hand list; *hand* means membership is
fixed by a hand-written list. The last column marks each row against the inventory at
`d78c98765`. The table has 30 rows; row 30 was added after the independent challenge.

| # | Identity | Owner | Covers | Basis | Consumers | On mismatch | Mark |
|---|---|---|---|---|---|---|---|
| 1 | Native kernel digest | `semantic/data_operation_storage.py:712–722` | 99 Python modules, the SQL of about 46 generator invocations, the physical closure, LinkML types, three logical YAML files, the renderer recipe, six library versions ([DA-068](execution-fit.md#da-068)) | Hand (enumerated in code, in four nested lists) | Descriptor check, release admission, read stamp, seal, receipt and replay gate, operation `behavior`, watermark | Refuse acquisition; reacquire; replay; re-bind | changed (four modules joined; captured metadata) |
| 2 | Native lowering digest | `semantic/data_operation_storage.py:141, 816–818` | The bytes of the generated compiler SQL | Content | Demand authority and intent programs | Refuse (as read at `d78c98765`) | unchanged |
| 3 | Release id | `semantic/prepare.py:986` | A manifest over root, model, profile, libraries, every source and dependency digest (the native capture, the PDF lowering contract) | Content | Everything keyed by release | Prepare and admit again | unchanged |
| 4 | Release-carried native digest | `semantic/prepare.py:1031, 1385` (`native_digest_from_dependencies`, `semantic/data_operation_storage.py:1080`) | The digest of the capture archived as dependencies | Content | The archived definitions projection; SQL admission (`semantic/native_admission_release.py:531`) | Refuse admission | unchanged (not listed before) |
| 5 | Kind, definition, eligibility, implementation-slice and recipe fingerprints | `semantic/data_operation_identity.py`; `semantic/data_operation_compilation.py` | Compiled model records, sliced sources, boundary digests | Model (plus boundaries) | Completion revision equality; execution identity inspection (`semantic/data_operation_admission.py:324–347`) | Refuse | unchanged |
| 6 | Opaque boundary and operation-source assets | `semantic/characterization_ports.py:48–194, 1144–1155`; `semantic/formal_products.py:677–757`; `semantic/rich_invocations.py:15–70` | Whole files, model YAML, library versions; rich uses a projection of the parsed module | Hand | Implementation slice, then recipe ([DA-069](execution-fit.md#da-069)) | Prior derivations are not reusable | changed (the composition module is also a slice source) |
| 7 | Port generator custody | `semantic/data_operation_artifacts.py:22–39, 73–81` | Eight generator modules | Hand | Release dependencies; compile refuses on drift | Refuse | unchanged |
| 8 | Python port identity | `semantic/data_operation_ports.py:1086`; `semantic/data_operation_admission.py:22, 293–321` | Model, sources, schema, declarations, contracts; digests retained at run time | Model and content | Acquisition; cached-port authorization | Refuse | unchanged |
| 9 | Prepared capability identity | `semantic/data_operation_admission.py:240–265` | Port identity, runtime, asset and boundary digests | Model and content | The prepared factory's authorization | Refuse | unchanged |
| 10 | Runtime artifact and attestation | `semantic/data_operation_runtime.py:88–120, 180–213` | Python version and executable inputs; release, profile, observation | Content | Native manifest and archive digests | Refuse | unchanged |
| 11 | Native selection asset custody | `semantic/data_operation_preparation.py:291–326` (`188ec73c2`) | The declared asset population, with path, digest and stat receipts, verified through file custody | Content | Primary-profile acquisition | Refuse | new |
| 12 | PDF lowering contract | `semantic/pdf_lowering.py:13–104, 168–256` | 70 listed files, boundary sources, generated schemas and codecs, 14 libraries | Hand ([DA-082](execution-fit.md#da-082)) | Release, producer contract, streaming, oracle capture, receipt `lowering_identity` | Refuse ("restart required" or "differs") | unchanged |
| 13 | PDF search renderer and pin | `semantic/pdf_source_search.py:29–37, 61–118` | Six whole Python files and the recipe JSON, docling versions, configuration | Hand | The search contract, the search pin, the kernel digest | Refuse; pin again | unchanged (not listed before) |
| 14 | Served-read implementation | `serve/rich_queries.py:71–105`; `_query_custody.py:17–135`; `semantic/demand_queries.py:117–124` | Listed module digests, nine libraries, the request schema | Hand ([DA-076](served-claims.md#da-076)) | Cursors, `resource_handle`, cache keys | Refuse to resume; restart | unchanged |
| 15 | Cut identity | `semantic/demand_results.py:64–102` | Every pin, including the read instance, snapshot and clock | Content | Cursors, `expected_cut`, cache keys ([DA-075](execution-fit.md#da-075)) | Refuse continuation | unchanged |
| 16 | Read kernel pin | `semantic/demand_result_native.py:223`; `semantic/data_read_boundary_native.py:98` | The kernel digest at acquisition | As row 1 | Read presence | Reacquire | unchanged |
| 17 | Semantic request key and reuse | `semantic/binding_admission_native.py:213`; `semantic/request_attachment_native.py:1254–1317` | Request meaning without release or runtime; unleased equivalent work in an inactive capture may now be replaced by the active release's generation | Model | Request reuse across releases | A new generation | changed (`7fdcd7643`) |
| 18 | Inputs watermark | `semantic/data_operation_projections.py:2062–2192` | Transitive prerequisites by source; role-matched local uses; populations, originals, source sets, trust, kernel | Model, at operation granularity, with one role-granular part ([DA-078](execution-fit.md#da-078)) | Planner skip (`semantic/data_operation_demands.py:736`) | Re-bind | changed (`6d699ab46`) |
| 19 | Completion seal | `semantic/data_completion_settlement_native.py:489–541, 1042`; checked at `semantic/data_derivation_native.py:382–394` | Kernel, request, generation, release, recipe, runtime, payload digest, trust | Mixed | Publication battery skip | Run the battery | changed (shared builder; no narrowing) |
| 20 | Receipt validating kernel and replay gate | `semantic/data_derivation_native.py:614`; `semantic/data_completion_settlement_native.py:633–695` | The kernel at publication | As row 1 | Seven family validators | Replay, not recorded (the routine is stable) | unchanged |
| 21 | CPU input basis and authority reply digests | `semantic/data_operation_cpu_basis.py:63–192, 330–460`; native side `:462–1150` | Selected inputs, roles, positions, values | Model and content | CPU authority conclusions, batch members | Refuse | unchanged identity; native side regenerated (`782f9f4df`) |
| 22 | Physical id; deployment-admission receipt; frozen expectation | `schema/physical.py:142–151`; `semantic/native_admission_release.py:59–97`; `semantic/execution_admission.py:121–140` | The physical closure; descriptor bytes; function body fingerprints and the revision file digest with stat; the descriptor also carries the authoring-source digests of row 30 | Content | Admission, catalog guard | Refuse | changed (generated; `1b643e7ed`, `9364a5b88`) |
| 23 | CHECK-contract digest for prerequisite recreation | `semantic/target_installation.py:781–787` | A digest of retained against current admission fields | Content | Native authoring of prerequisite recreation | Refuse authoring | new (`65ee94886`, `1a290484d`, `82b02e589`) |
| 24 | Wire contract digest | `semantic/data_operation_wire.py:41–60, 550`; checked per call at `semantic/data_operation_storage.py:1120` | The protocol YAML or the captured protocol | Content | Every native invocation envelope | Refuse | unchanged |
| 25 | Scientific policy | `semantic/scientific_evidence.py:192–255`; `semantic/rich_policy_binding.py:22–30` | A hand-written description of the kernel | Hand ([DA-077](served-claims.md#da-077)) | Release check, rich context | Refuse | unchanged |
| 26 | Model-change compilation and generator fingerprints | `schema/model_change.py:313–440, 1066–1077` | The whole package tree, libraries, tools, the worktree head | Content (whole tree) | Candidate checks | "Prepare a fresh preview" | unchanged |
| 27 | Source-migration identities | `schema/source_migrations.py:168–198` | Every file under `semantic/` and `model/semantic/`, with libraries | Content (whole tree) | The source-migration check | Refuse | unchanged |
| 28 | File custody; query custody | `semantic/file_custody.py:20–137`; `_query_custody.py:136–260` | A path's digest with its stat identity; module bytes at import | Content | Lowering, model and selection assets, CPU call assets, served reads | Refuse; restart | unchanged (more consumers) |
| 29 | Archive and capsule identity | `semantic/releases.py:81–90, 451–455`; `semantic/cpu_execution.py:150–200, 783–800` | Archive bytes digest and format; capsule digest and release id | Content | Release open, CPU transfer | Refuse | unchanged |
| 30 | Authoring-source digests in the execution-contract descriptor | `semantic/native_products.py:54–170` (`capture_native_authoring_inputs`); recorded in `data.execution_contract_descriptor` | 48 `authoring/*` entries: the bytes of 28 listed modules, model files and generated artifacts | Hand | The deployed descriptor and its frozen expectation (row 22) | A new native revision restamps the descriptor, even when no generated statement changes (four entries changed at N29) | unchanged mechanism (not listed before; found by the independent challenge) |

What the inventory shows:

- **Six identities derive their membership from model declarations** (rows 5, 8, 9, 17, 18
  and 21). These are also the ones on which reuse is exact, or would be if the watermark used
  role granularity throughout.
- **Eight are hand-kept** (rows 1, 6, 7, 12, 13, 14, 25 and 30). Each is a hand-written answer to
  "which code determines this artifact". A hand list can be wrong in either direction, and
  the lowering list is established as both too broad and too narrow (DA-082), the served-read
  list as too narrow (DA-076).
- **The hand lists nest and overlap.** The kernel capture (row 1) contains the search renderer
  list (row 13), whose members are also served-read inputs (row 14) and construction helpers.
  Rows 1, 12, 13 and 14 share files (`native_program.py`, `native_source_view.py`,
  `identity.py`, `metadata.py`, `schema/physical.py`), so one edit can move several identities
  at once. Native revision N29 shows two such edits: one to a renderer input moved the
  renderer pin, the kernel digest and the served-read identity, and one to authoring modules
  moved the descriptor's authoring digests (row 30).
- **Three are whole-content** (rows 3, 26 and 27) and so over-broad by construction: any byte
  supplied changes them. That is safe, and it is why an unrelated edit asks for a new release
  or a fresh preview.
- **Mismatch refuses, or redoes the whole unit.** No identity in the table narrows the redone
  work to what actually changed, and the replay gated by the receipt's kernel digest (rows 1
  and 20) does not record that it succeeded.
- **Finer identities exist and are not used for keying**: each program's generated bytes are
  captured, only one of them is used as a digest (row 2), and the release carries the native
  digest it was prepared with (row 4) while the Python admission check rebuilds the capture
  to compare the checkout ([DA-083](execution-fit.md#da-083)).

<a id="analytical"></a>

## Analytical and set-wise computation

**Interface-checked by source inspection.** The map was built on 2026-11-18 at `d78c98765`
and updated the same day at `5139eaba3` by checking every row's owner against the commits in
the range; rows whose owners have no commit were not re-read. It records where derived,
aggregating, joining and graph-shaped work runs today. It is a map of facts for the review
that follows; it makes no judgment about where any item should run, and no size or timing was
measured. "Bound to PostgreSQL authority" means the computation needs the database transaction
itself: snapshot visibility, trust locks, the caller's principal, or writes.

| Kind of work | Where it runs | Bound to PostgreSQL authority, and why | Sites | State at `5139eaba3` |
|---|---|---|---|---|
| Validity closure and its fixpoint | PostgreSQL: a generated recursive query followed by a PL/pgSQL loop | Yes: visibility by transaction id relative to the read boundary, the revocation table, the caller's principal | `semantic/data_validity_native.py:471–610` | unchanged (no commit) |
| Support walk | PostgreSQL: a generated recursive query | Yes: the same visibility and locks | `semantic/data_operation_projections.py:171`; six callers | changed: the walk takes a name parameter, and public reads carry a second recursive closure per page, seeded from the page's public uses after an access-scoped obligations step (`:452, 2231`; `ed410b80f`, `6d699ab46`) |
| Watermark prerequisites | PostgreSQL: a generated recursive query | Yes | `semantic/data_operation_projections.py:2062–2192` | changed: a role-matched component for dependency-free operations (`:1781, 1919`), and whole-demand frontiers include discovery (`110e8aa1e`) |
| Dependency and record-tree walks; authorization, selection, keyset ordering, full-text ranking | PostgreSQL programs | Yes | `semantic/pdf_search_native.py:783–837` and the per-program sites of the analytical map lane | unchanged. Materialized common-table expressions in `semantic/` rose from 47 to 55 (search) |
| Binding population selection | PostgreSQL program | Yes | `semantic/data_operation_bindings.py:1028–1055` | added: independent optional roles are selected per role from the anchor instead of joining all optional roles and projecting distinct rows, which removes a cross product (`1d3640990`) |
| PDF inventory completeness | PostgreSQL program | Yes | `semantic/pdf_publication_native.py:1925, 2160–2210` | added: parent-to-child access edges are materialized once and used for both the missing-child and the wrong-parent direction (`66c36d4c8`) |
| Archived class matching for record grading | PostgreSQL program | Yes | `semantic/record_grade_native.py:150–175` | added: the archived operation model is parsed to JSON once per call and complete classes are filtered once (`a31503daf`); the whole archived model is still parsed in PostgreSQL on each grading call |
| Contextual mutual neighbours | PostgreSQL: generated Core over pgvector (a distance operator, a ranked window per partition, and a limit taken from the declared numerical policy) | No: a stable function of its JSON arguments; its numerical backend is pinned and checked | `semantic/contextual_neighborhood.py:70–300` | changed: generated, where it was a hand-written SQL file; the same computation (`32ec30618`, `df0cb85b8`) |
| Row filtering, ordinal paging, joins of already-acquired pages, byte budgeting, response shaping for served reads | Python generators and dictionaries, with the one `cachetools` cache | Acquisition is bound and is repeated on every call; the shaping is a pure function of the acquired page | `semantic/demand_queries.py`; `semantic/selected_query_cache.py`; `serve/selected_contributions.py`; `semantic/rich_queries.py` | unchanged |
| Change impact, declared graph inspection, rich relation walks, the semantic operation graph | Python with NetworkX, over a SQLite scratch index or the compiled model | Acquisition is bound; the analysis is pure | `semantic/change_impact.py:157–500`; `semantic/graph_inspection.py`; `semantic/rich_statistics_queries.py`; `semantic/data_operation_identity.py` | unchanged |
| Captured document composition | Python | No | `methods/captured_document_composition.py`; `semantic/enriched_document_products.py:174–193` | added: inputs declared as a set and ordered canonically by authenticated source coordinate, without asserting a reading order (`590b67b7a`, `1fab40234`, `67a6e7a51`) |
| Rich-rule occurrence views (same slot, alternative of, declared projections) | DuckDB relations over Arrow tables built from Python objects; the rule loop, premise accumulation and equivalence components stay in Python | No | `semantic/analytical_kernels.py:204–309`; `semantic/rich_rule_evaluation.py` | unchanged |
| Companion export inventory and multiset comparison | DuckDB over Parquet files | No: a pure function of verified files | `serve/companion_export.py:403–606` | unchanged; its captured projection inputs are now held by a content-keyed cache (`semantic/companion_projection.py:561, 620`) |
| PDF candidate geometry; recognition replay ordering | DuckDB over Arrow batches; DuckDB external sort with a spill directory | No | `ingest/pdf_candidate_geometry.py:75–313`; `ingest/pdf_stream_reconciliation.py:293–340` | unchanged |
| Artifact identity scoring | Splink on DuckDB, after pairwise candidate generation in Python | No | `semantic/artifact_identity.py` | unchanged |
| Evaluation and scoring (assignment, graph matching, bootstrap, fitting, sampling), scientific comparison, record interpretation | Python with numpy, scipy, scikit-learn and NetworkX over acquired values | No, except that operation fitting reads through four `text(...)` calls | `evaluate/*`; `semantic/scientific_evidence.py`; `semantic/record_interpretation.py` | changed in one place: the operation-event scorer moved into a declared scorer port's `run` (`semantic/operation_policy.py:362, 380–391`; `04f542206`); the same computation |
| Export and verification row work (logical row digests, dedup, per-page joins) | Python loops over Arrow batches; SQLite as an out-of-core store in five modules | The export snapshot is bound; verification is pure | `serve/companion_export.py`; `serve/demand_export.py`; `serve/native_source.py` | unchanged |

Rows removed since `d78c98765`: the hand-written contextual neighborhood SQL file as an owner
(now generated, above); the source-record graph SQL file (deleted in `c25cada3f`); and the
scalar encoder kernels (`93b7141ec`).

**DuckDB use, as facts.** DuckDB is imported by six modules, none of which has a commit in
`d78c98765..5139eaba3`. Every connection is in-memory, created per invocation and closed at
the end of its scope; there is no shared or persistent connection, no extension loading and no
attachment to PostgreSQL. All use is through the relational and expression API with no SQL
text. No operation moved from PostgreSQL to DuckDB in the conversion. Three of the five use
sites declare their Arrow input schemas by hand
([DA-086](semantic-model-and-authority.md#da-086)); the companion export's schema is derived
from the model. Two rich kernels have no production caller
([DA-080](boundaries-and-composition.md#da-080)), and the analytics settings for threads and
memory are not read ([DA-020](boundaries-and-composition.md#da-020)).

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
not qualified. The update of 2026-11-18 at `5139eaba3` did not re-read this table as a subject.
A row was updated only where a lane re-read the finding it links to, and says so; every other
row keeps its 2026-11-17 date.

| Finding | State in source | Residual observed |
|---|---|---|
| PE-F01, F02 | Implemented at the examined sites | — |
| PE-F03 | Implemented for read paths | None. Execution derives the release at registration and once per host basis, which the review records as deliberate; current sites are listed under [DA-033](execution-fit.md#da-033) (2026-11-18 at `5139eaba3`) |
| PE-F04 | Implemented | — |
| PE-F05 | Partly | Set evaluator exists; scalar per-item and per-step calls remain, the fixpoint scans all edges per fact per iteration and evaluates the edge function twice per node (2026-11-17; the closure is the generated program at `semantic/data_validity_native.py:471–610`, which has no commit since and was not re-assessed). Re-read 2026-11-18 at `5139eaba3`: family membership is still assigned by name list, now twelve lists ([DA-070](semantic-model-and-authority.md#da-070)) |
| PE-F06 | Partly | Re-read 2026-11-18 at `5139eaba3`: the waiting-obligation skip is still coarse; a role-matched component was added for dependency-free operations, and the kernel digest remains a component ([DA-078](execution-fit.md#da-078)). Python and native both evaluate the binding (2026-11-17) |
| PE-F07 | Implemented | — |
| PE-F08 | Declared in the physical model | — |
| PE-F09 | Partly | (a) prepared-kernel ports recompute their asset artifacts from disk on every verification, including each blocked submit tick, so the work grows with waiting time (2026-11-17; not re-read); (b) binding re-parses artifacts ([DA-033](execution-fit.md#da-033); stands at `5139eaba3`, `semantic/binding_admission_native.py:232–251`); (c) the seal key is the whole capture ([DA-068](execution-fit.md#da-068); stands and wider at `5139eaba3`; the shared seal builder of native revision N27 did not narrow it); (d) established validity is keyed by release; (e) the native capture is rebuilt at every port acquisition and recheck ([DA-083](execution-fit.md#da-083); stands at `5139eaba3`) |
| PE-F10 | Implemented for attach and claim | Discovery expansion is still per population |
| PE-F11 | Implemented (two-stage admission) | — |
| PE-F12 | Partly | Member validation is still per member, including on replay |
| PE-F13 | Implemented (spot-checked) | Test evidence gap: [DTA-046](../test-audit/evidence-and-discrimination.md#dta-046) |
| PE-F14 | Mostly | Selected-item hydration still reads per record |
| PE-F15, F18, F22, F29 | Implemented | — |
| PE-F16 | Partly | The evaluator MCP server and the render fallback still open an engine per call (`intervene/selected_assessment_server.py:45–80`), which also defeats the per-engine archive cache |
| PE-F17 | Partly | [DA-075](execution-fit.md#da-075), re-read 2026-11-18 at `5139eaba3` and unchanged; change impact rebuilds the whole comparison for every page (`semantic/change_impact.py:687–777`; that file has no commit since `fbd3f2a98`) |
| PE-F19 | Implemented, with limits | Native models still retire per run at the default keep-warm of 0; Chandra is outside the host ([DA-058](execution-fit.md#da-058)) |
| PE-F20, F21, F25, F28 | Implemented | Test evidence gaps: [DTA-041](../test-audit/support-structure.md#dta-041), [DTA-044](../test-audit/evidence-and-discrimination.md#dta-044) |
| PE-F24 | Partly | Not examined beyond the candidate reusing the preview capsule |
| PE-F26 | Implemented in source | The oracle skip has no discriminating test ([DTA-044](../test-audit/evidence-and-discrimination.md#dta-044)) |
| PE-F30 | Implemented | No two-settler concurrency case was found; the settlement SQL was not read for this |
| PE-F31 | Partly | Re-read 2026-11-18 at `5139eaba3`: every orphan SQL file is gone with its directory, a migration helper and the scalar encoder kernels were removed, and other unconsumed items remain or were found ([DA-080](boundaries-and-composition.md#da-080)) |

<a id="planned-change"></a>

## Planned change not yet in source

This section mapped the then-remaining steps of the model-owned SQL conversion onto the
findings they would affect. Those steps have landed, and each finding now records what the
conversion did to it, so the table only restated history and was removed in the update of
2026-11-18 at `5139eaba3`; its last text is in Git at the publication of the refresh at
`d78c98765`.

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
  process; whether `formal/execution-custody` enters the implementation revision and whether
  the composition module added to a view operation's sources is sliced
  ([DA-069](execution-fit.md#da-069)); whether `public_disclosure` enters the cut pins
  ([DA-075](execution-fit.md#da-075)); whether the per-consumer model closures ever differ in
  result ([DA-085](semantic-model-and-authority.md#da-085)); replay volume and the cost of one
  replay after a kernel restamp ([DA-068](execution-fit.md#da-068)); and what layers beyond the family guards
  do with an operation that no guard lists
  ([DA-070](semantic-model-and-authority.md#da-070)).

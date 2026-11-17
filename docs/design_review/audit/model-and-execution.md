# The domain model and execution, across production and tests

**Interface-checked by source inspection, 2026-11-17**, source `fbd3f2a98`. This page is the
integrated analysis of a joint refresh of the [broad account](README.md) and the
[test account](../test-audit/README.md), run together at one commit with two priorities set by
the operator: the comprehensive domain data model, and efficiency of execution. It holds
analysis, inventories and links. Findings keep their primary homes in the topic pages of each
account, and nothing here selects a remedy.

Production paths omit `python/corpus-structure/src/corpus_structure/`; test paths beginning
`tests/` are relative to `python/corpus-structure/`; `scripts/` and `conftest.py` are at the
repository root. No timing on this page is measured unless it cites a stored run.

## The short version

The declared model now governs operations, kinds, roles, states and result identity well. The
strongest design in the codebase is the semantic request identity: it is built from the
recipe, content-addressed inputs and the implementation slice, and it leaves out the release
and the runtime, so a result survives a new release and an unchanged input stops recomputation
from spreading.

Around that core, the same three things recur in production code and in the test system:

1. **Identities that are much coarser, or narrower, than what they stand for.** A digest over
   forty modules stands for "the kernel that validated this". A per-test directory is part of
   "which scenario this is". A hand-kept file list stands for "the code that produced this
   answer". Coarse keys throw away valid work on unrelated edits; narrow keys let stale work
   through.
2. **Facts the model holds, or could hold, written again by hand.** Operation-id lists in SQL,
   three encodings of the support graph, fixture-name lists, nine copies of a test converter.
   Each copy is a place where a model change has to be remembered.
3. **Reuse added without the evidence that it is safe.** Several mechanisms that skip a check
   or carry a result forward are tested only where the reuse is correct.

These are the same problem seen from three sides. Caching and targeted execution both need an
answer to "what does this result depend on?". Where the model gives that answer as data, reuse
is exact (the request identity). Where it does not, each mechanism invents its own
approximation, and the approximation is either too broad to hit or too narrow to trust.

## Shared causes and where their findings live

| Cause | Production | Tests |
|---|---|---|
| **Identity broader than its premise**: valid work discarded on unrelated change | [DA-068](execution-fit.md#da-068) native kernel digest; [DA-069](execution-fit.md#da-069) opaque-boundary implementation identity; [DA-075](execution-fit.md#da-075) cache key includes the read instance; [DA-078](execution-fit.md#da-078) readiness watermark | [DTA-040](../test-audit/execution-and-qualification.md#dta-040) per-test path in recipe identity; [DTA-038](../test-audit/execution-and-qualification.md#dta-038) deployment key includes the whole lockfile and artifact mtimes |
| **Identity narrower than its premise**: stale work can pass | [DA-076](served-claims.md#da-076) read implementation allowlist; [DA-077](served-claims.md#da-077) scientific policy description | [DTA-038](../test-audit/execution-and-qualification.md#dta-038) deployment key misses modules run by upgrade bodies |
| **A model fact restated by hand** | [DA-070](semantic-model-and-authority.md#da-070) validity-family id lists; [DA-071](semantic-model-and-authority.md#da-071) support graph three times; [DA-072](semantic-model-and-authority.md#da-072) two models; [DA-073](semantic-model-and-authority.md#da-073) release composition; [DA-074](native-integrity.md#da-074) guard and grant lists | [DTA-037](../test-audit/retirement-transfer.md#dta-037) fixture-name lists; [DTA-041](../test-audit/support-structure.md#dta-041) converter copies; [DTA-042](../test-audit/support-structure.md#dta-042) pack composition; [DTA-043](../test-audit/support-structure.md#dta-043) copied reservation formula; [DTA-033](../test-audit/evidence-and-discrimination.md#dta-033) vector input rebuilt per consumer |
| **Established assurance re-proved instead of carried** | [DA-033](execution-fit.md#da-033) release content per admission and per binding; residuals of PE-F09 [below](#pe-state) | [DTA-039](../test-audit/execution-and-qualification.md#dta-039) whole migration chain per key miss; repeated head and seed verification |
| **Reuse without discriminating evidence** | The mechanisms are production's; the gap is in tests | [DTA-044](../test-audit/evidence-and-discrimination.md#dta-044) skips tested only on the equal path; [DTA-045](../test-audit/evidence-and-discrimination.md#dta-045) profile check asserted against a double; [DTA-046](../test-audit/evidence-and-discrimination.md#dta-046) batch attribution invisible |
| **Superseded machinery kept** | [DA-080](boundaries-and-composition.md#da-080) | [DTA-037](../test-audit/retirement-transfer.md#dta-037), [DTA-035](../test-audit/retirement-transfer.md#dta-035) |

Each cause has one primary finding per manifestation; where a production cause explains a test
manifestation, the test account links to the production finding instead of opening its own
(for example, tests of unused evaluation modules are footprint of DA-080).

## Model facts that could key, scope or invalidate work

These are observations about what the model already makes available, paired with what the work
is keyed by today. They are leads for a later review, not selected changes.

| Model fact (already declared or compiled) | Work it could key or scope | Keyed by today |
|---|---|---|
| Per-operation recipe, definition and eligibility identities; implementation-slice fingerprint | Which definitions a new release actually changes; implementation identity of construction and formal operations | `release_id` over every input file (`semantic/prepare.py:963–985`); whole files and library versions ([DA-069](execution-fit.md#da-069)) |
| The source of each family's validators (captured per module) | Completion seal and receipt validation identity | The whole native capture ([DA-068](execution-fit.md#da-068)) |
| Direct role producers and subject context | Readiness of a waiting obligation | Every upstream operation for the same source ([DA-078](execution-fit.md#da-078)) |
| Compiled dependency projections (`potential-producers`, `selected-dependencies`) | Change impact; which obligations of a re-registered demand can only reuse | Rebuilt by hand in change impact ([DA-071](semantic-model-and-authority.md#da-071)); `potential-producers` is not consumed by execution |
| Validator asset content digest | Reuse of established product validity across releases | `release_id` (`semantic/established_validity.py:116`) |
| Release finalization and deployment-admission receipts | The release-content half of native admission | Re-proved per acquisition ([DA-033](execution-fit.md#da-033)) |
| Admitted definition rows and the lowering digest | Per-binding correspondence checks | Artifacts re-parsed per attached item ([DA-033](execution-fit.md#da-033)) |
| Frontier content stamp with release, runtime and selection | Served query results across fresh requests | The acquisition instance ([DA-075](execution-fit.md#da-075)); soundness of the alternative is an open premise |
| Whole rich product body with release | One validated graph index shared by every query on that product | Per-query selection |
| Physical annotations on relations | Frontier-guard and trigger membership | Hand lists ([DA-074](native-integrity.md#da-074)) |
| The migration graph and its pinned artifact digests | The test head: content identity of artifacts; building from the predecessor head | Size and mtime; full replay ([DTA-038](../test-audit/execution-and-qualification.md#dta-038), [DTA-039](../test-audit/execution-and-qualification.md#dta-039)) |
| Recipe content identity without the capture directory | Scenario seed and prepared-kernel reuse across tests | A value that includes the per-test path ([DTA-040](../test-audit/execution-and-qualification.md#dta-040)) |
| The fixture graph and the recipe-type registry | Database classification and worker affinity of tests | Hand lists of fixture names ([DTA-037](../test-audit/retirement-transfer.md#dta-037)) |

Two boundaries are right as they are and should not be "improved": the model YAML does not
reach the test head, because frozen migrations never import current compiler state; and the
request identity excludes the release and the runtime.

<a id="cache-inventory"></a>

## Caches and prepared state

### What exists

Production has one cache built on `cachetools`, about 94 `functools` caches, about 75
`cached_property` sites and about ten hand-built process-level holders. The repository pins
`cachetools` 7.2.7; the [library overview](../../libraries/analytical_infrastructure/cachetools.md)
describes 8.0. Tests use no `cachetools`; they have 31 session and 96 module fixtures, about 50
`functools` helpers, and two cross-run stores (the reusable head database and the receipt
classification).

| Holder | Key | Bound | Invalidation | Concurrency | Note |
|---|---|---|---|---|---|
| `SELECTED_QUERY_CACHE` (`semantic/selected_query_cache.py:58–86`) | Cut identity (five consumers) or frontier stamps only (exclusions), with implementation, selection and budgets | 32 MiB by `getsizeof`, 128 entries by manual `popitem`, 8 MiB and 4,096 rows per entry | New key only | `RLock` on get and put; concurrent identical misses both compute | [DA-075](execution-fit.md#da-075) |
| `_OPEN_CACHE` (`semantic/archive_reader.py:32–38, 396–434`) | Archive header and library versions, per engine | 8 per engine, hand-built `OrderedDict` | Header re-read each call | `RLock`; first cold result wins | Dies with the engine, so per-call engines defeat it ([PE state](#pe-state), F16) |
| `_prepare_release_cached` (`semantic/prepare.py:599`) | Bundle, dependencies, profile, compiler stack | 8 | New key | Thread-safe; double compute on race | Sound; retains up to eight full artifact sets |
| Static preparation, model decode, wire protocol and validators (`data_operation_static_preparation.py:66`, `data_operation_model.py:1206`, `data_operation_wire.py:52–464`) | Exact captured bytes | 8–256 | New key | Thread-safe | Sound, with strong key-sensitivity tests |
| `_ambient_protocol*` (`data_operation_wire.py:46, 429`); `trusted_pdf_context`; `_report_*` | None: first read in the process | 1 | Process restart | — | Deliberate; a mismatch refuses by digest |
| File custody (`semantic/file_custody.py:79–137`) | Path and digest; stat identity | Unbounded (finite files) | Stat change or a 2 s racy window re-hashes; changed bytes refuse | `RLock` | Refusal means "restart" |
| Query custody (`_query_custody.py:134–176`) | Module | Unbounded | None; reload refuses | — | [DA-076](served-claims.md#da-076) |
| Execution-host bases (`orchestrate/execution_host.py:186–272`) | Engine, release, runtime, root, run determinants | 2 idle capsules, 256 MiB | Header and runtime row re-read each acquire; mismatch refuses | Run lock | [DA-079](boundaries-and-composition.md#da-079) |
| Worker releases (`semantic/cpu_execution.py:148–224`) | Capsule digest | Per CPU generation | Cleared at worker init | Per worker | Decoded release is outside the byte budget |
| Math parsers and memo (`methods/math/grammar.py:309–327, 966–991`) | Macro classification; (latex, kind, table, context) | Parsers **unbounded**; memo 8,192 | None | Main thread | Now lives across runs in long-lived workers |
| Encoder, spaCy pipeline, compiled GLiNER pack | Profile or config | 1 / unbounded / 64 | Stat checks or process death | — | — |
| Native residency (`methods/native_host.py:660–944`) | Profile fingerprint | Declared selections | Retired at run end unless keep-warm is set (default 0) | Waits on a condition | — |
| Record reader per-instance caches (`semantic/pdf_record_reader.py:268`) | Record id | 256 per reader | Instance lifetime | — | Returns a shared mutable dict; consumers read only |
| Test head database (`scripts/native_test_support.py:896–1116`) | Deployment key | Three retained | Key change; failed verification retires | Advisory locks | [DTA-038](../test-audit/execution-and-qualification.md#dta-038), [DTA-039](../test-audit/execution-and-qualification.md#dta-039) |
| Scenario seeds (`scripts/native_scenario_seeds.py:193–360`) | Recipe value and head | Unbounded until session end | Head replacement | `RLock`, per worker | [DTA-040](../test-audit/execution-and-qualification.md#dta-040) |
| Test-side `functools` helpers (about 50) | Mostly none | 1 each, per worker | None | — | Values are frozen; acceptable within one run |

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

<a id="pe-state"></a>

## State of the production-efficiency mechanisms in source

Source-level state at `fbd3f2a98`. The [DDO plan](../../plans/declared-data-operations_2026-11-12.md)
owns status, and native deployment of several of these is not yet adopted. "Implemented" here
means present in source, not qualified.

| Finding | State in source | Residual observed |
|---|---|---|
| PE-F01, F02 | Implemented at the examined sites | — |
| PE-F03 | Implemented for read paths | None. Execution derives the release at registration and once per host basis, which the review records as deliberate |
| PE-F04 | Implemented | — |
| PE-F05 | Partly | Set evaluator exists; scalar per-item and per-step calls remain, the fixpoint scans all edges per fact per iteration and evaluates the edge function twice per node, and family membership is assigned by name list ([DA-070](semantic-model-and-authority.md#da-070)) |
| PE-F06 | Partly | Waiting-obligation skip is coarse ([DA-078](execution-fit.md#da-078)); Python and native both evaluate the binding |
| PE-F07 | Implemented | — |
| PE-F08 | Declared in the physical model | — |
| PE-F09 | Partly | (a) prepared-kernel ports recompute their asset artifacts from disk on every verification, including each blocked submit tick, so the work grows with waiting time (`semantic/characterization_ports.py:502–550, 882–991`; `semantic/data_operation_cpu.py:150–171`; `core/work.py:137–142`); (b) binding re-parses artifacts ([DA-033](execution-fit.md#da-033)); (c) the seal key is the whole capture ([DA-068](execution-fit.md#da-068)); (d) established validity is keyed by release |
| PE-F10 | Implemented for attach and claim | Discovery expansion is still per population |
| PE-F11 | Implemented (two-stage admission) | — |
| PE-F12 | Partly | Member validation is still per member, including on replay |
| PE-F13 | Implemented (spot-checked) | Test evidence gap: [DTA-046](../test-audit/evidence-and-discrimination.md#dta-046) |
| PE-F14 | Mostly | Selected-item hydration still reads per record |
| PE-F15, F18, F22, F29 | Implemented | — |
| PE-F16 | Partly | The evaluator MCP server and the render fallback still open an engine per call (`intervene/selected_assessment_server.py:45–80`), which also defeats the per-engine archive cache |
| PE-F17 | Partly | [DA-075](execution-fit.md#da-075); change impact rebuilds the whole comparison for every page (`semantic/change_impact.py:687–777`) |
| PE-F19 | Implemented, with limits | Native models still retire per run at the default keep-warm of 0; Chandra is outside the host ([DA-058](execution-fit.md#da-058)) |
| PE-F20, F21, F25, F28 | Implemented | Test evidence gaps: [DTA-041](../test-audit/support-structure.md#dta-041), [DTA-044](../test-audit/evidence-and-discrimination.md#dta-044) |
| PE-F24 | Partly | Not examined beyond the candidate reusing the preview capsule |
| PE-F26 | Implemented in source | The oracle skip has no discriminating test ([DTA-044](../test-audit/evidence-and-discrimination.md#dta-044)) |
| PE-F30 | Implemented | No two-settler concurrency case was found; the settlement SQL was not read for this |
| PE-F31 | Partly | See [DA-080](boundaries-and-composition.md#da-080) |

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
- Every unpinned read writes durable read and scope rows
  (`semantic/sql/data_operations.sql:1983–1993`); no pruning was found. Hypothesis only.

# Served claims and evaluation

These findings cover the go-forward consumers that serve or grade knowledge:
- the read kernel and `serve/`;
- the CLI query, explain, export, golden and eval commands;
- the MCP server;
- reference evaluation under ADR-0030.

The code-intelligence profile (CI-01–CI-13) applies directly here. Findings are at the
[audited baseline](README.md#baseline).

Paths are relative to `python/corpus-structure/src/corpus_structure/` unless they start with
`domains/`, `docs/`, `tests/` (`python/corpus-structure/tests/`) or `rev/`
(`python/corpus-structure/semantic_alembic/versions/`).

"Recorded output" means the files under
`docs/design_review/evidence/2026-10-29_semantic-consumer-regeneration/raw/`, produced by the SP-08
journeys on 2026-10-29.

Two related findings have their homes elsewhere:
- the live, unpinned query plug-in is part of [DA-028](semantic-model-and-authority.md#da-028);
- refusal surfaces and the `claims` `object=` crash are part of
  [DA-013](structure-and-invariants.md#da-013).

<a id="da-035"></a>

## DA-035 — Coverage producers and consumers use different vocabularies, so absence can never be stated

**Principles:** CI-04, CI-05, CI-08, CI-11; FP-04/A2 (no owned translation between contexts);
DP-03, DP-12, DP-20; FP-07/A4. **Subject:** implemented.

### Diagnosis

Coverage is the only way a consumer can tell "none" from "not known here". Producers and consumers
use incompatible meanings for its two keys, and nothing translates between them.

**Producers** write `family` as an item or source kind and `scope` as a unit, observation or
`source/item` key:
- families include `task`, `claim`, `entity`, `statement`, `mention`, `scope`, `extract.math`,
  `claim_proposal` and `unsupported`;
- writers: every `coverage_row(...)` in `semantic/domain_operations.py:1126-1709`, and the
  `SourceCoverage` in `intervene/semantic.py:205-213`.

**Consumers** read `family` as a property IRI and `scope` as `"*"` or a document id:
- the kernel asks `self.coverage(prop.iri, spec.coverage_scope)` with default scope `"*"`
  (`semantic/query.py:1095`, `:74`);
- serving filters `c.family == ctx.reader.iri(family)` (`serve/journey.py:231`) and compares the
  documents scope with `str(document_id)` (`:84-92`).

**As a result:**
- The kernel's `knowledge="absent"` branch is unreachable.
- Queries with a predicate filter receive an empty coverage list.
- Queries without one receive every coverage row of the realization on every page.
- The documents scope never matches.
- Recorded output: the toy predicate query has `coverage=[]`. A three-row statistics query carries
  4,102 coverage records, which are 1,399,601 of its 1,406,553 characters.

**At the native boundary, coverage is asserted by the writer.** Staged coverage rows are checked
only against the outcome closed set and the CHECK on the translation from source outcome
(`rev/0001_physical_bootstrap.py:313-316`; `rev/semantic_0024_decisions.sql:3-4`). `family`,
`scope` and `reason` are free text. No native routine derives coverage or checks it against the
bound cut, although native code re-derives facts, evidence and statement context from the same
reports. Under ADR-0025's untrusted-writer premise, a staged `complete` would turn an empty result
into an apparent absence. That consequence is suspected.

The only test that exercises `absent` builds a coverage row in a shape production never writes
(`tests/semantic/test_query.py:229-231`). That belongs to the test audit's
[DTA-008](../test-audit/support-structure.md#dta-008).

### Consequence

- **CI-04 is unmet in its positive direction.** Every empty answer reads `unknown`. That is
  conservative, but the system cannot say "none" for any scope.
- **Coverage does not relate to the rows it accompanies.**
- **Envelopes grow with the corpus.** Whole-realization coverage counts toward `max_chars`
  (`serve/journey.py:265-275`). Any bound smaller than the coverage refuses every predicate-less
  query: "a complete row and response envelope do not fit". `explain` repeats the same coverage
  ([DA-039](#da-039)).
- **Coverage rows carry no producer.** Two producers covering one unit write rows that differ only
  in outcome (`semantic/domain_operations.py:1112-1121`).
- **A latent hazard.** If the absent branch became reachable as written, it would assert absence
  regardless of status, modality, subject or projection filters.

### Counterevidence

The default never claims absence falsely.

**Evidence:** diagnosed from source; confirmed against recorded output.

**Lineage:** related to [DA-007](semantic-model-and-authority.md#da-007) (unresolved items recorded
only as coverage) and [DA-013](structure-and-invariants.md#da-013) (prose reasons).

**Lead:** one coverage vocabulary owned by the release, with a declared mapping from a query's
universe to coverage records, derived or checked natively.

<a id="da-036"></a>

## DA-036 — Selection status is an undifferentiated filter, not a served attribute

**Principles:** CI-02, CI-11, FP-04, DP-02. **Subject:** implemented.

### Diagnosis

Acceptance is written twice:
- as a `consolidate.status` assessment (`semantic/domain_operations.py:3317-3339`);
- as `data.selection` rows (`:3342-3378`).

Consumers derive accepted against candidate from selection alone (`serve/read.py:101-129`,
`semantic/query.py:436-445`). So `candidate` lumps together facts that were rejected, ambiguous,
deselected by equivalence ([DA-034](semantic-model-and-authority.md#da-034)) or deduplicated for
display.

`QueryRow` and `ClaimAnswer` have no status field, so an answer cannot carry the distinction:
- `include_candidates=True`, the `status` parameter and the fact and occurrence projections mix
  selected and unselected facts with no marker (`semantic/query.py:147-159`;
  `serve/journey.py:174-177`);
- `transformations_of` and `relations_between` hydrate premises and path claims with
  `include_candidates=True, include_suppositions=True`, whatever the caller asked for
  (`domains/statistics/queries.py:232-242`, `:358-362`).

The accepted projection also includes inferred conclusions without a per-row marker of how each
fact was established.

### Consequence

- A consumer that asked for accepted knowledge can receive candidate premises indistinguishable
  from accepted facts.
- A consumer that asked for candidates cannot tell rejection from ambiguity or equivalence
  deselection.

**Evidence:** diagnosed from source.

<a id="da-037"></a>

## DA-037 — Grades conflate "not matched" with "not comparable", condition their universe on extraction success, and use production identity as the pairing basis

**Principles:** CI-12 ("an evaluation states what it covers"; non-circular), CI-04, CI-06, CI-08,
DP-22, FP-06. **Subject:** implemented.

### Diagnosis

Reference evaluation keeps several properties ADR-0030 promises:
- immutable reference bytes;
- versioned frames;
- a separate evaluator principal;
- policy read from the archive;
- mathematically undecided outcomes kept as undecided.

Five other properties of a grade are not stated or preserved:
- **(a) Unaligned pairs disappear.** A claim pair whose subject entities did not align is skipped
  silently. It is recorded neither as undecided nor as a field failure
  (`evaluate/semantic_alignment.py:789-793`, `:900-901`).
- **(b) Undecided pairs are scored as misses.** They are kept in a separate `undecided` list
  (`evaluate/semantic_alignment.py:802-811, 893`), but the match counts treat them as misses.
- **(c) The reference universe is conditioned on extraction success.** Reference sets are sampled
  only from units whose extraction produced an `AgentStoredBatch` (`evaluate/semantic.py:97-112`).
  Units the extractor refused are written as `SourceObservation` (`intervene/semantic.py:194-216`),
  so they are never sampled, and neither are units that failed.
- **(d) A missing prediction refuses the whole grade.** If the graded run lacks an observation for
  a reference unit, both Python and the native `eval.record_reference_evaluation` refuse
  (`evaluate/semantic.py:276`, `:828-831`; `rev/semantic_0029_reference_boundaries.sql`). A zero
  for that unit would be the honest result.
- **(e) The coverage attached to a grade spans the whole realization**, not the scored units
  (`evaluate/semantic.py:848-856`).

**Entity pairing reuses production identity.** The `alias_normalization` basis calls the same
legacy `core.keys.normalize_label`, with the same release alias policy, that production identity
resolution uses (`evaluate/semantic_alignment.py:439-447`, `:611-616`; compare
`semantic/domain_operations.py:817-974`). `record_pass` admits references against classes from the
graded run's output realization, so a reference may cite production-resolved entity ids. Pairing
then defers to production identity (`evaluate/semantic.py:366-376`, `:620-632`;
`evaluate/semantic_alignment.py:641-645`).

**Split provenance is not recorded.** `split_documents` takes its policy from the project's
*active* release, while set creation uses the completed result's release.
`eval.document_split` stores only `(project_id, source_uri, split)`, and a `--seed` override is not
persisted (`evaluate/semantic.py:555-617`).

### Consequence

The recorded transfer grade cannot be interpreted:
- precision, recall and F1 are all 0.0;
- `undecided` and `field_failures` are both empty;
- the cause is that "P-17" and "vessel P-17" did not pair (recorded `transfer-grade.json`).

Recall over the hardest units is structurally invisible. Where identity normalization serves as
the pairing basis, errors shared by production and grading cannot show in the grade (CI-12). The
operational extent of that is suspected; the recorded grade paired by label.

**Evidence:** diagnosed from source, and confirmed against the recorded grade. The effect of the
shared normalization is suspected.

**Related:** the evaluator's own prediction translation and its third notion of value sameness
are part of [DA-005](semantic-model-and-authority.md#da-005) and
[DA-034](semantic-model-and-authority.md#da-034).

<a id="da-038"></a>

## DA-038 — The kernel's paged query route has no production consumer; serving rebuilds it from private members

**Principles:** FP-02, FP-06, A1/A3 (an interface that hides its internals), CI-05, DP-22.
**Subject:** implemented.

### Diagnosis

The kernel's paged query route is `ReadSession.query` with `QuerySpec`, its fingerprinted
continuation token (`_token`, `_after`) and knowledge derivation. Only tests use it: outside
`semantic/query.py`, `QuerySpec` appears only under `tests/`. Other kernel members are used in
production: `ReadSession.explain` and `coverage` (`serve/explain.py:46`; `serve/read.py:379`;
`serve/journey.py:85`), and `read_session` (`semantic/analytics.py:469`).

`serve/read.Reader` and the pack plug-ins compose SQL from the kernel's private members instead:
`_scope`, `_same_scope`, `_values`, `_entities`, `_occurrence_contexts`
(`serve/read.py:12`, `:191`, `:200`, `:359`; `serve/queries.py:8`, `:140`;
`domains/statistics/queries.py:12`, `:151`, `:157-166`). Domain operations do the same
(`semantic/domain_operations.py:521`). Pack plug-ins are an external authoring
surface, so the private names have become an unacknowledged API.

Each path keeps its own machinery:
- **Continuation:** `semantic-query-1` in the kernel; a parameter digest through legacy
  `core.canonical` in `serve/journey.py:95-131`.
- **Adapter caches:** separate in the kernel and `Reader`; `families_where` builds adapters a third
  way.
- **Property resolution:**
  - the kernel uses an explicit class handle;
  - `Reader` takes the first definition, in `prepared.definitions` order, among the subject's
    memberships (`serve/read.py:205-216`).

### Consequence

- Kernel tests do not cover what is served.
- Every change to the read contract must be made twice.
- An entity with several memberships that declare the property is validated under whichever
  class comes first.
- Plug-ins break whenever the kernel's private members change.

**Evidence:** diagnosed from source. A scenario reviewer narrowed the scope from "the kernel" to
its paged query route, and withdrew a claimed `next()` failure, which is guarded (W2-C,
2026-10-29).

**Lineage:** related to the leverage review's
[CBO-001](../../library_leverage/reviews/consumer-read-boundary.md#cbo-001), which is solution
reasoning, not diagnosis.

<a id="da-039"></a>

## DA-039 — Explanation and path queries are unbounded

**Principles:** CI-08, FP-07/A4, DP-20. **Subject:** implemented. D8 sets a bound ("top 10 supports
and 10 links, counts for the rest", D8:176) in its legacy body, and its semantic header defers to
that body until consumers migrate.

### Diagnosis

`explain` returns:
- all supports and all evidence;
- the full `kb.observation.payload` of every supporting observation, which means whole agent
  batches;
- identity exclusions;
- `coverage=self.coverage()` for the whole realization
  (`semantic/query.py:1173-1185`, `:1323`; `serve/explain.py:89-119`).

Unit explanations embed whole task-result bodies. `ci explain` has no character bound. The
`evidence` query recomputes the entire explanation on every page and filters in Python
(`serve/queries.py:171-176`; `serve/read.py:378-379`).

`relations_between` is depth-bounded but frontier-unbounded. Its recursive `union_all` has no
visited set, so it emits non-simple paths, and its frontier grows exponentially with node degree.
The depth bound (`walk.c.depth < 4`) is hard-coded and not stated in the answer, and each page sorts
all paths before applying its cursor (`domains/statistics/queries.py:327-353`).
`transformations_of` recomputes its full premise set on every page (`:231-243`).

Query pages are unbounded by default: `max_rows` and `max_chars` default to `None`
(`cli/query.py:106-107`).

### Consequence

Explanation size and cost grow with the realization rather than with the fact explained. A path
answer can be partial with nothing to say so (CI-08).

**Evidence:** diagnosed from source. The 1.4 MB coverage in [DA-035](#da-035) indicates the
growth; it is not a measurement of `explain`.

<a id="da-050"></a>

## DA-050 — Explanation and other follow-up references sit outside the pinned serving journey

**Principles:** CI-13, CI-11, DP-19. **Subject:** implemented.

### Diagnosis

Query pages are pinned to one completed result. The journey resolves `promoted` from the project's
selection on the first page, then binds release, realization and data revision. Continuation tokens
carry that binding and compare it on every later page (`serve/journey.py:44-81, 119-131, 191-222`).
Data cannot mix across pages. This is a strength.

Follow-up references do not carry the binding. `ci explain` takes `--run`, defaulting to
`promoted`, and has no token or binding argument. It re-resolves the selection on every call
(`cli/explain.py:35-60`; `serve/explain.py:42-48`). After a selection change between a query and its
explanation:
- explaining a page-1 fact refuses with a misleading "no semantic fact", because fact ids are scoped
  to the realization (`semantic/identity.py:76-95`; `serve/explain.py:47-48`);
- `ci explain unit <key>` silently explains the *new* run's tasks and observations, because unit
  keys are not scoped to the realization (`serve/explain.py:62-103`).

The explanation carries no premise status (`semantic/query.py:1307-1316`;
[DA-036](#da-036)). A continued page does not say whether its run is still the selected one.

### Consequence

A journey can resolve an earlier reference under a different result, which is the CI-13 audit
question answered in the affirmative. An agent following a query with an explanation can receive
evidence for a result it did not query.

### Counterevidence

The explanation output carries `run_id` and `binding`, so a careful consumer could detect the
switch. Passing `--run` explicitly pins it.

**Evidence:** diagnosed from source (W2-C scenario SC6, 2026-10-29).

<a id="da-051"></a>

## DA-051 — Producer attribution is declared by configuration and never established by the executing provider

**Principles:** CI-01, DP-05, DP-21, FP-02. **Subject:** implemented.

### Diagnosis

The model that produced a claim is recorded only as configuration: `ops.method_config.params.model`.
Nothing establishes or records which model actually executed:
- **MCP leases ignore it.** The server leases any `agent.opus` task whose config matches the mode,
  with no filter on model (`intervene/semantic_server.py:123-139`). A session running one model can
  complete a task configured for another.
- **Execution details are reported, not recorded.** The automated provider returns the executing
  model and provider session only in the CLI report (`intervene/automated.py:211-216`;
  `cli/regenerate.py:137, 181`). Neither is persisted. `ops.task.claimed_by` stores a session
  instance, not a model.
- **Served evidence names the method.** Evidence `provider` and `operation_version` are the method
  name and version (`semantic/domain_operations.py:768-769, 1401-1405`). So every agent claim is
  attributed to `agent.opus`/`semantic-1` whatever model produced it. Served custody stops at the
  task and run (`semantic/query.py:183-193`).

### Consequence

- A manual MCP session can author claims attributed to another configured model.
- Two agent tiers configured under `agent.opus` cannot be told apart in served evidence or in grades.
- The automated provider avoids the gap only by refusing a run with more than one configured model
  (`intervene/automated.py:62-64`).

### Counterevidence

The configuration hash includes the model, and the automated path passes the configured `--model`
to the provider (`intervene/automated.py:130-131`).

**Evidence:** diagnosed from source (W2-C scenario SC5, 2026-10-29).

**Related:** [DA-052](boundaries-and-composition.md#da-052).

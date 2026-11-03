# Unified domain model after the test-architecture implementation

**Date:** 2026-11-02. **Lens:** combined design and assurance; plan-improvement review.
**Baseline:** `af567228` plus the identified in-progress TA production, test, support and owner
changes. Source-inspected observations are Implemented only within their named paths;
recommendations remain Proposed until implemented and qualified. This engagement publishes the
review and revises UM under the operator's explicit instruction. No product code, dependencies,
services, databases or reference outputs are changed by it.

## Combined judgment

Retain the existing unified-model architecture. TA is making it more substantive: one released
alias policy now serves consolidation and reference alignment; full independently authored keys
and current source-backed counterparts challenge actual consumers; native acquisition and
qualification retain observed identities instead of trusting configuration. Reimplementing these
as UM-specific fixtures or a generic scenario/validation language would dilute those benefits.

One useful new functional amendment is warranted: alias-only semantic changes need their own
located change/consumer facts in UM's impact report. A newly answer-affecting query helper also
needs inclusion in existing implementation custody (I05). Other amendments connect existing UM
obligations to the stronger TA foundations and preserve the scope of their evidence. The
SQLAlchemy-to-ADBC cancellation gap remains open; formatter and stdio settlement do not close it.

This is neither a new diagnostic audit nor a TA completion audit. The TA coordinator owns DTA
disposition and qualification. UM owns UM-CA10/13 and its assembled acceptance. Phase0 X2-01
retains the broader authored-name obligation. Existing provider improvement proposals are not
automatically adopted. No architectural rule change is proposed; RC01–RC04 and ADR-0032/0047
remain in force. The dirty accepted ADR-0048 is consumed as current context, not altered here.

## Coverage and assessment basis

Read the TA coordinator and four companions, UM coordinator and eight companions, current
completion/improvement reviews, test-audit baseline and relevant architectural owners. Three
read-only contributions examined policy/identity/consumer meaning, scenario/preparation/native
composition, and resources/interfaces/receipts. The coordinator reconciled their evidence and
inspected decisive source. The standard is core3.3, heuristics1.0, test-assessment1.2 and applicable
CI1.4 fidelity/evidence guidance. This is responsibility-oriented coverage, not a claim to read
every source line or rerun every retained reference.

FP-01/03 and A1/A3 favor the existing coherent policy, scenario and lifecycle owners. FP-04/A2
require behavior to consume released meaning while independent examples challenge that meaning.
FP-02/05/06 require failure and consumer contracts to survive the real boundaries. FP-07/A4 favor
immutable preparation and fresh committed clones where they remove unrelated setup, while cold,
race, publication and recovery tests retain the actual work they assess. These are qualitative
judgments; no speed, capacity or extraction-quality benefit is measured. Correctness, fidelity
and assembled qualification remain separate from this scoped architectural judgment.

Paths below use `python/corpus-structure/src/corpus_structure/` for production and
`python/corpus-structure/tests/` for package tests.

<a id="I01"></a>
## I01 — Carry released alias meaning into semantic impact

**Selected extension:** UM-12, with UM-01/03/13/14 consumers. FP-04/05; DP-08/21/24.

`semantic/alias_policy.py:25–113` resolves source-relative names to effective full class IRIs and
emits `operation/alias-policy.json` (`class-iri-aliases-1`). Preparation adds it to release artifacts;
`domain_operations._entity_mappings` and `evaluate.semantic_alignment._entity_pairs` both use
`label_normalizer`. Ordered rewrites, articles, head words, conflicts and origin remain explicit.
Old nonempty unversioned policies refuse execution rather than acquiring today's interpretation.
This is an implemented TA correction, not new UM implementation to schedule again.

However, `operation_reporting.compare_semantic_releases:565–746` compares normalized definitions,
execution groups, comparison roles and qualified projection products without comparing this alias
artifact. A policy-only edit can change grouping/alignment without a corresponding alias change
fact or located advice. Generic unknowns elsewhere are not a substitute for reporting a known
changed product. This is a new artifact-coverage extension, not a retraction of the original
bounded impact implementation.

Compare both archived products by profile and full class IRI. Report added/removed/changed policy
members through the existing SemanticImpactReport and `_changed_members`; report origin-only
changes separately from normalization meaning. Missing/incompatible profiles are explicit
unassessed coverage, never silently an empty policy. Preserve ordered rewrite meaning and known
neutral-policy semantics. Reuse released-product decoding; do not compile live YAML during diff.

Connect known consolidation/entity-mapping and semantic-alignment consumers through their owned,
versioned dependency/binding declarations. If a consumer is not an executable operation ID, retain
its actual consumer kind rather than inventing an operation. Keep dynamic/undeclared consumers
unknown. No manually maintained parallel registry or universal semantic-equivalence engine follows.

Retaining generic unknown advice is simpler but loses a known actionable change. A new universal
dependency framework is disproportionate. Select the finite existing-report extension. Reuse its
generated Pydantic boundary and existing CLI/MCP/regeneration adapters; if their report contract
changes, version/admit it through the existing route without rewriting frozen migrations.

**Closure:** independent alias-only edits with unchanged class shapes identify the changed class,
member and affected known consumers through actual diff/advice and CLI/MCP. Include origin-only
edits, ordered rewrites, added/removed policies, unknown profile and intentionally incomplete
consumer knowledge. A new active release must not reinterpret an older producing release.

<a id="I02"></a>
## I02 — Reuse preparation without reusing the assertion's authority

**Selected assurance amendment:** UM-03/05/06/07/14/15. FP-02/04/06/07; H12/H19/H20.

TA support separates immutable acquisition/preparation from committed effects. The session-local
serving seed seals one named population and supplies fresh PgAdmin-owned clones; varied query,
coverage, write/race and cold-deployment cases retain their independent preparation. This is a
useful realization of UM's reuse principle, not permission for a universal fixture cache.

`test_prepare.py:562–635` runs actual uncached preparation in fresh interpreters and independently
checks fields, requiredness, values and refusals. It is a semantic-1 example, not evidence for all
generated call signatures, SQL recipes or alias products. Extend only materially different UM
contracts with independent cold-content obligations; use warm products for downstream consumers.
Retain static-negative generated-call cases and actual server-result refusal controls. Exact bytes
or two cold runs agreeing cannot alone establish semantic correctness.

Use current pytest fixture dependency/yield lifetimes and `PgAdmin.database` policy replay, not
another scheduler or janitor. Setup may use production constructors; malformed-input tests must
still reach the intended admission boundary. Expected facts/keys/results stay independently
authored at their assurance owner. Deliberate invalid SQL and native inspection are legitimate
test responsibilities; ordinary setup should reuse domain operations where they suffice.

**Closure:** changed relevant inputs invalidate reuse; unrelated scenario defaults do not change
the claim; clone identities differ and actual purpose policy is verified; wrong generated output
fails an independent expectation; publication/cancellation/deployment cases remain real. No
quantitative runtime target or blanket migration of tests into generated cases is selected.

<a id="I03"></a>
## I03 — Preserve current reference meaning and reach the intended failure

**Selected contract/acceptance amendment:** UM-01/02/03/04/05/11/13/14/15. FP-04/05/06.

TA now has full hand-authored fact/occurrence preimages and digests, statistics alias journeys,
toy attribution/time/ambiguity examples and trace counterparts. `query.py` normalizes strict
object operands through the existing `consolidation.plain` before `value_meaning`; `rule_views.py`
projects nested Formula values through the semantic structural path. These corrections should
be consumed and challenged, not copied into test-specific interpreters.

Keep fact identity, comparison grouping, occurrence provenance and source custody distinct.
Exact numeric lexical form, negative zero, nested roles and missing/null distinctions matter
through actual query/explain. Controlled authored proposals establish composed semantic behavior,
not recognition accuracy for the original HTML/PDF or complete historical negative-set replay.
Notice exclusion lacks current source classification; trace T3-D1 derivation lacks an admitted
rule. Retain those explicit boundaries and revisit owners rather than restore obsolete writers
or manufacture passing expectations. Future supported functionality needs its own model change.

Native refusal acceptance needs a valid committed baseline, the intended invalid change, exact
native cause and no partial effects. Psycopg `Error.sqlstate` plus `diag.constraint_name` or a
qualified structured diagnostic, obtained through SQLAlchemy `DBAPIError.orig`, discriminates
guards. A narrowly matched `message_primary` may characterize a retained guard test; it does
not become a stable domain failure-code mapping. Promised UM-02 codes still require the admitted
model/enforcer binding. Independent expected report fields must not call their producer.

**Closure:** extra/missing/wrong evidence and attribution produce different outcomes; catalog
reordering does not retarget mutations; an unrelated FK/privilege refusal cannot satisfy the
guard assertion; raw unmapped failures remain distinct through CLI/MCP. Use TA counterparts and
their scoped evidence; add only missing UM-specific controls, not duplicate reference datasets.

<a id="I04"></a>
## I04 — Compose observed qualification and operation-wide settlement

**Selected acceptance amendment and retained gap:** UM-09/10/14/15, UM-CA13. FP-03/05/06/07.

TA captures original acquisition credentials before installing a refused ambient application
target. `native_test_support.observe_engine:640–714` records requested versus actual database/OID,
principal, server lifetime and deployment/policy references through `record_native_context`.
Read the existing qualification events/classifier; do not create another UM evidence ledger.
Seed origin is setup provenance, distinct from each actual acquired clone and purpose session.

`test_runtime_entrypoints.py:315` uses real SDK `StdioTransport`, explicit environment/cwd and
`keep_alive=False`; accepted/refused/early/cancelled journeys observe actual child/session
settlement. `test_pdf_record_reader.py:351` observes the production formatter, per-chunk bytes,
exact content and result closure. These strengthen specific interface/lifetime claims. Neither
establishes arbitrary hard-kill recovery, provider correctness or the cross-backend export seam.
The stdio cancellation mode acts after listing tools, not during an active export. The formatter
case uses minimal native tables, a stub publication function and ScalarReader overrides: its real
formatter/cursor evidence does not establish complete admitted-artifact publication or ADBC behavior.

`serve/companion_export.py:109–127` still performs SQLAlchemy source/snapshot work before
`owned_adbc_read` registration at129–134. UM-CA13 remains an implementation obligation. Extend
existing operation ownership across backend-specific cancellation registrations; do not pass an
ADBC token as if it were a SQLAlchemy cancellation protocol. Preserve imported snapshot lifetime,
independent cleanup attempts, original errors and atomic destination publication.

**Closure:** actual in-flight SQLAlchemy metadata cancellation, handoff cancellation and ADBC
bulk cancellation each settle resources and leave no published destination. Reuse applicable
TA stdio/formatter/acquisition results only for their actual scopes and final source/context.
Keep native cold deployment in the existing serialized lane where shared locks constrain it.
No new server, seeded-cache service or shared-cluster termination authority is justified.

The same continuity inventory includes `analytics.capture_packet:991–1023`, which accepts an
ADBC handle but enters `read_session` without a caller SQLAlchemy token. Settle that actual
consumer's cancellation contract before closing UM-09/10; do not infer all capture has failed.
Existing `BorrowerCancellation.borrow()` uses Psycopg `cancel_safe`; `read_snapshot` and source
inspection accept that token. Compose those handles with `owned_adbc_read` under one sticky
operation request. Keep registration/return synchronized, check cancellation across handoff and
before publication, and retire registrations before harmless late cancellation. A cancel-request
timeout is distinct from a bounded complete-operation settlement contract.

An acquired-context event also does not prove that the asserted operation used its restricted
principal: the classifier can associate a complete maintenance event with a node. Keep explicit
operation/session observations for the SQLAlchemy and ADBC effects. Do not turn the classifier
into a semantic validator or retroactively fabricate provenance for historical receipts.

<a id="I05"></a>
## I05 — Include the new exact-object helper in named-query custody

**Newly exposed implementation obligation:** UM-04/03/14, FP-02/04/05 and DP-24.

Dirty `semantic/query.py:766,807` now calls `semantic.consolidation.plain` before exact object
meaning comparison. The finite `QUERY_SOURCES` in `corpus_structure/_query_custody.py:17–53`
includes query/value-codec/identity sources but omits consolidation. `installed_query_inputs`
hashes that same list before loading the registry (`query_compatibility.py:119–155`). A change
only to this newly answer-affecting helper can escape named-query implementation identity.
This contradicts the existing UM-04 source-custody guarantee; it is not merely optional typing
cleanup or a reason to restore arbitrary archived Python execution.

Extend the existing finite custody list with the helper's containing module and any actual
answer-determining delegates it requires. Cover source bytes of already loaded helper objects
as well as subsequent file acquisition through the existing source-custody mechanism. A generic
recursive import tracer would add unrelated dependencies; extracting a small shared semantic
projection may be considered later if it independently improves ownership, but is not required
to restore custody. Frozen query products remain unchanged; trusted compatibility or explicit
current-only refusal governs new bindings.

**Closure:** change the helper before first acquisition and after import, including a pre-imported
helper and changed file after load. Each incompatible path refuses before changed query logic
runs. Independently check exact nested-object values and omitted/null behavior through named
query, continuation and explanation. Keep alias-policy release identity separate from query-code
implementation identity; matching one cannot establish the other.

<a id="I06"></a>
## I06 — Bind projection preparation to its captured analysis runtime

**Selected preparation correction:** UM-08/03/12/14; FP-02/04/07 and DP-09/15.

`contracts.py:1042–1066` already captures SQLGlot in `libraries.json`; it is not missing from
ordinary acquisition identity. But `prepare_projection_analysis` (`projection_analysis_products.py:109–175`)
rebuilds retained sources with installed SQLGlot without comparing that captured producer version.
The generic `_compiler_stack` excludes SQLGlot (`determinants.BYTE_LIBRARIES`), while
`analyze_recipe` caches by recipe and reports the live version (`projection_analysis.py:264–265,373`).
Thus the inspected preparation/reuse boundary lacks an explicit check tying those two facts.
This is a source-established guard gap under a changed runtime, not observed artifact corruption
or permission to upgrade dependencies during this review.

Before cache lookup or producing new analysis, validate the captured analysis producer/runtime
tuple using the existing determinant owner. Include the actual analysis determinant in relevant
preparation and recipe-analysis cache identities. Missing or incompatible required analysis
provenance refuses new preparation with reacquisition/regeneration advice. A deliberate version
move reacquires inputs and creates a new release. Decoding supported immutable archived analysis
does not run today's analyzer and must not require its historical producer to be installed.
Do not put every library into every boundary's acceptance tuple or disable supported archive reads.

Reuse `MappingSchema`, strict `qualify`, `annotate_types`, `build_scope` and bounded `lineage`
under that qualified tuple, retaining existing unknown coverage. Add one materially distinct cold
semantic-2 composed-recipe case with independently specified output types, value versus WHERE
dependencies and artifact contents. Pair it with captured/runtime mismatch before a warm hit,
changed source and supported archived-product opening. The existing semantic-1 cold test remains
useful, but does not establish this composed-analysis contract. Broad recompilation on every
read would be simpler to describe and inappropriate for immutable reuse; the selected boundary
check protects only new production and reuse where the analyzer actually matters.

<a id="I07"></a>
## I07 — Extend typed operation adoption through shared scenario ports

**Selected bounded extension:** UM-03/05/14; FP-02/05/06.

New `operation_scenario_support.py:9–108`, `agent_scenarios.py:32–43,83–97`,
`domain_scenarios.py:48–76,509–510` and `reference_scenarios.py:29–47` expose consequential
untyped resource/identity tuple ports to many UM callers. `serving_scenarios` already shows
small typed scenario values. Extend these shared ports with existing Engine/Path and
PreparedRelease/RunId/TaskId/CutId types, concrete tuples or ordinary small return values and
meaningful inputs. Migrate their maintained domain/agent/operation/serving/reference consumers
together. This carries UM typing into real shared consumers without a second scenario schema.

Keep raw declarations, malformed proposals, invalid rows and wire bytes available when their
purpose is to challenge admission. Do not type every authored schema dictionary or replace
independent expectations with generated data. Prefer existing typed setup operations; retain
native SQL when its independent observation or deliberate invalidity is the claim.
Closure needs focused wrong-ID/resource type controls and actual valid/invalid consumer cases,
not annotation inspection alone. This can proceed alongside I05/I06 without waiting for every
TA package or opening a universal scenario abstraction.

## Integration, priority and evidence limits

Repair I05/I06 and UM-CA13 independently of the alias-report extension. First reconcile TA's current released
products and support; then implement I01 through UM-12/13 and its real consumers. I02/I03 shape
each affected package's checks; I04 shapes UM-14/15 evidence association. Neither all TA completion
nor all UM completion is a barrier to a ready bounded correction.

The UM coordinator schedules these amendments and alone owns their current disposition. TA
retains DTA-001–020; X2-01 and PDF/provider acceptance retain their existing owners. The earlier
UM improvement review's broad provider proposals and general dependency/report-fingerprint
investigations remain separately proposed. I01 is a bounded selected extension, not wholesale
adoption of those proposals.

Historical TA native receipts report212 required passing nodes and46 fixture-native contexts;
these overlap and are not summed. Their invocation/classification files were inspected, not rerun.
Pending TA remaining-scope receipts and UM's79-node math/provider/assembled union are not passes
by inheritance. This review runs no product tests, native probes, provider journeys or benchmarks.
Source inspection establishes the integration choices and gap, not final functional qualification.

**Closing refresh, 2026-11-02:** HEAD remained `af567228`; SHA256 comparison of the108
modified/untracked snapshot inputs found no intervening TA/source changes before final synthesis
(UM-owned document edits excluded). Independent challenge and document validation follow this
same inspected semantic snapshot; maintenance does not grant product qualification. Subsequent TA changes
require focused reconciliation at execution; no continuous watch or competing completion verdict
is introduced. Review publication and UM amendment checks are recorded at the coordinator.

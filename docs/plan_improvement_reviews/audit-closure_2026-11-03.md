# Audit-closure: targeted improvements after integration

**Reviewed 2026-11-03 · recommendations Proposed.** Independent design-reviewer contribution,
coordinator publication. Inspected source `75db93e1`, initially clean. The selected footprint is
remaining AC integration, transition, qualification and M1 handoff. Criteria: core3.3, efficient
architecture heuristics1.0, code-intelligence1.4 and test-assessment1.2 under the repository binding.
This is a `plan-improvement-review`, not a new diagnostic audit or assembled architecture acceptance.

## Combined judgment

Retain the accepted target and RC01–RC12. Existing shared authority, bounded reading, claim lifetime
and native transition mechanisms support three focused amendments to composition, acceptance and
handoff. A new engine, store or capability catalogue has no demonstrated benefit here.
The completion audit separately found AC-CA01: unsupported adjudication remains advertised by
`queue_next` and can return empty success. That is unfinished accepted retirement, not a new
improvement. Its disposition belongs to the [AC coordinator](../plans/audit-closure_2026-11-03.md#12-completion-audit--claimed-integrated-slices).
Paths below are relative to `python/corpus-structure/src/corpus_structure/`.

<a id="I01"></a>
## I01 — Carry bound authority through remaining integration scenarios

**Current approach.** `semantic/types.py:326–343` obtains operational reference splits from the
exact bound execution product; explicit domain-only behavior remains separate.
`semantic/contracts.py:668–683,1614–1623` carries this required product in execution24.
`semantic/coverage_contract.py` preserves historical recipe3 and derives recipe4's supported
producers from their owner. `semantic/query.py:900–1068` checks immutable named configurations,
parameters, versions, units and configuration hashes. Existing `test_reference_split_authority.py`
and `test_configured_coverage.py` exercise supplied subsets, domain collisions, general-only/mixed
populations, binding drift and historical behavior.

**Amendment.** Make these distinctions explicit at semantic/source/serving/evaluation boundaries.
Carry selected existing nondefault cases through the native and consumer seams still unqualified.
Connect machine reasons to actual stored assessments and consuming responses; reason classes alone
are insufficient. Reuse existing products and controls, without a second registry or conformance
framework. AC01/02/05/08/10/12 supply the mechanisms; AC14 owns assembled applicability.

**Benefit and burden.** FP-03/04/06, CI-04/10/12 and H18–H20 favor consuming the actual authority
rather than rediscovering it. This makes execution-schema and producer variation local. The added
work is focused scenario selection or extension at existing integration boundaries.

**Alternatives and challenge.** Default-schema/Opus-only journeys are cheaper but miss a domain
vocabulary incorrectly taking operational authority or complete Opus reports concealing a missing
general-producer unit. Applying current recipe4 requirements to recipe3 archives would instead
erase historical meaning; preserve that branch exactly.

**Closure and M1.** Account for applicable supplied-subset, general-only/mixed/drift and historical
cases on final source/context, leaving missing evidence open. M1-01/02/03/11/12/13 consume the bound
products and stored reasons. This adds no extraction/reference-authoring feature or new rule impact.

<a id="I02"></a>
## I02 — Describe bounded delivery by actual effect and transport

**Current approach.** `semantic/pdf_record_reader.py:40–109` performs scalar row/byte preflight
before transfer and canonical decoded-value accounting. `semantic/query.py:2020–2110` bounds
inventory items and the response envelope. `intervene/semantic_server.py:77–172,610–639` retains a
rendered artifact before inline delivery, retaining its reference on size refusal. `read_unit`
checks the full MCP envelope. The server registers tools; generic resource wording in the plan
does not establish a resource workflow.

**Amendment.** Describe upstream row/raw-payload admission and final encoded-envelope admission
for the affected routes. Separate committed rendering from refused inline transport: preserve the
artifact reference, rather than implying rollback. Keep explicit streamed export distinct from
bounded interactive demand. AC14 exercises actual registered CLI/MCP tools, continuations and
export; remove illustrative resource wording rather than inventing another capability.
AC-CA01 separately removes/refuses unsupported choices; empty success does not settle it.

**Benefit and burden.** FP-02/05/07, CI-08/11/13 and H6/H7/H17/H23 favor explicit effects and whole
live-state bounds. This prevents inner-payload accounting from understating base64, duplicate
text/structured data and metadata overhead. It also preserves durable render custody. The burden
is AC10/11/13 contract clarification and existing consumer controls, not a transport framework.

**Alternatives and challenge.** A single read-failed outcome loses the distinction between a
committed render and refused delivery; inner-body limits miss full-wire oversize. Conversely,
imposing an interactive whole-response limit on a deliberately streamed export removes a supported
separate demand. Preserve each route's actual effect and lifetime.

**Closure and M1.** Existing native-source, region and MCP controls must establish refusal before
oversized transfer, complete-envelope admission, artifact lookup after refusal and compatible
continuation. M1-05/12 reuse these distinctions for evidence/images/export. This is no measured
latency, RSS or universal document-capacity claim.

<a id="I03"></a>
## I03 — Finish transition and retirement from the frozen successor

**Current approach.** Frozen102 succeeds immutable101. Fresh install, predecessor-forward
transition and current-head reauthoring establish different properties. `semantic/alembic_indexes.py`
and its `native_candidate.py` registration enrich the pinned reflection context from actual
`pg_index.indcollation`, rather than copying desired values or suppressing drift.
`test_index_collation_reflection.py` distinguishes matching C collation from POSIX drift.
The root formatter excludes frozen revision files; lint remains enabled. The registered
`complete_unit_result` at `semantic/contracts.py:147` demonstrates why direct-call searches alone
cannot establish retirement.

**Amendment.** Start remaining AC13 work from frozen102. Any subsequent native meaning change
uses a new forward successor; historical draft scripts must not overwrite102. Account separately
for fresh/forward/current-head paths. Run full-chain disposable installs serially on the dedicated
cluster following retained shared-lock exhaustion; unrelated detached checks need no such barrier.
Retain the reflection adaptation while the pinned stack needs it; revisit on dialect/Alembic
changes and remove only when actual replacement reflection preserves collation, ordering and
covering-index differences. Retirement includes registrations, generated bindings and supported
archived readers, as well as ordinary callers.

**Benefit and burden.** FP-01/02/06/07 and H4/H19/H22/H24/H27 favor local library adaptation and
coherent transition ownership. This avoids repeated unsuccessful setup without changing server
settings or losing drift detection. Work stays within AC00/13/14's existing route.

**Alternatives and challenge.** Rewriting102 breaks frozen hashes and predecessor interpretation.
Suppressing index differences hides actual drift. Removing a dynamically registered operation
breaks a live consumer; retaining every unregistered old implementation defeats decommissioning.
Use actual consumer evidence to distinguish those cases.

**Closure and M1.** Identify exact source/native contexts for separate fresh/forward/current-head
controls and retain failed receipts. M1-00/02/03/11 consume that successor and bindings; later native
changes use ordinary forward authoring. This does not qualify M1 accuracy, CPU resources or adoption.

## Integration order and limits

Repair AC-CA01 under existing scope, incorporate I01–I03 into local target/acceptance explanations,
then establish the remaining final-source AC union. M1 documentation can be reconciled immediately
from amended contracts, retaining unfinished AC prerequisites for execution.

No new rule impact, dependency change, provider invocation, native installation, test or benchmark
is proposed as a prerequisite to publication. No new runtime check was run for this review.
Source inspection supports the recommendations; runtime correctness and quantitative benefits
retain their evidence obligations. The coordinator owns adoption and scheduled work; this review
is not a progress ledger or product-repair authorization.

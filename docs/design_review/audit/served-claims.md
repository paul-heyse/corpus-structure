# Served claims and evaluation

**Implemented source inspected, 2026-11-03.** See the [current baseline](README.md#baseline).
Paths below are relative to `python/corpus-structure/src/corpus_structure/`, unless prefixed
with `domains/`. This is static diagnosis, not native or consumer qualification.

<a id="da-035"></a>

## DA-035 — Unfiltered named pages repeat whole-realization coverage

**Principles:** FP-07/A4, DP-10/20/21, CI-08. **Subject:** implemented.

The October29 claim that absence is unreachable is withdrawn. `semantic/query.py:653–776`
now derives required coverage from an archived recipe, producer bindings and frozen effective
origin tasks. Document requests lift to required source units; missing bindings give an explicit
diagnostic. `serve/journey.py:250–275` consumes this requirement before claiming absence.
This is material counterevidence to the old vocabulary-mismatch diagnosis.

The remaining manifestation is narrower: `serve/journey.py:235–261` loads all coverage before
filtering, and no predicate means the entire coverage accompanies each named-query page.
An answer selecting a few entities can therefore repeatedly hydrate/serialize unrelated coverage.
The `max_chars` check occurs after construction and can refuse an otherwise small answer because
its envelope does not fit. The source establishes repeated work; old recorded byte counts are
historical, not measurements at this baseline. Full coverage has a legitimate explicit consumer
in the unsupported/coverage question; that does not establish its necessity on every page.

<a id="da-036"></a>

## DA-036 — Candidate-inclusive fact answers omit per-fact standing

**Principles:** FP-04/A2, DP-02, CI-02/11. **Subject:** implemented.

`semantic/query.py:161–174` defines QueryRow without selection or assessment standing.
`serve/results.py:22–24` embeds it unchanged. `serve/journey.py:211–215` changes the envelope
projection to `fact` when candidates are requested, but that identifies a mixed universe rather
than the standing of each returned fact. `domains/statistics/queries.py:363–370` hydrates path
facts with candidates/suppositions included; the nested ClaimAnswer has the same limitation.
A downstream consumer cannot distinguish selected from rejected/ambiguous facts from that row
alone. It must make an explanation request and interpret assessments separately.

This is not a claim that the default accepted filter admits every rejected fact. The explicit
projection and query parameters are useful contrary evidence. M1 record answers separately expose
admission and assertion relations (`serve/record_results.py:94–112`); this diagnosis is about the
ordinary fact answer, not that distinct source-record protocol.

<a id="da-037"></a>

## DA-037 — Legacy split assignment loses its policy provenance

**Principles:** FP-05, DP-21/24, CI-10/12. **Subject:** implemented; narrowed.

The earlier prediction-conditioned sampling and missing-prediction diagnosis is withdrawn:
`evaluate/semantic.py:100–143` selects source frames from the completed cut, including empty
reports; `:617–744` builds an empty prediction when no admitted occurrence exists. Scoring
retains reference denominators (`evaluate/semantic_alignment.py:969–974`). An undecided comparison
not earning a match is not itself an unstated error; explicit undecided/comparison records matter.
The October29 transfer grade is not current evidence of broken grading.

One supported older route still loses provenance. `evaluate/semantic.py:528–599` resolves a
release policy or explicit configuration and a possible seed override, but persists each
assignment through `eval.assign_document_split(project,uri,split)` only. Its returned seed is
not the persisted assignment; Assignment.reason is also dropped (`evaluate/split.py:86–91`). `model/semantic/physical.yaml:2228` declares document_split with
project/source_uri/split, without the producing policy, seed or release. `cli/golden.py:266`
still exposes this operation. A later reader cannot reconstruct why that split was assigned
from the authoritative stored row, especially after active release changes.

M1's distinct sample/origin protocol preserves its own additional provenance: `evaluate/record_references.py:556–659`
requires seed/strata/inclusion probabilities/provenance and persists frozen source-frame metadata
and policy versions. It still consumes legacy_split/document_split as a separate prerequisite
(`semantic/sql/record_references.sql:94–104`); that does not recover the older assignment provenance. Actual reference authoring, grading and fitting journeys remain outside this
static inspection; independence is not established merely by separate implementation modules.

<a id="da-038"></a>

## DA-038 — Prior private read-boundary diagnosis removed

**Source-inspected correction, 2026-11-03.** `serve/read.py:43–60` delegates scope, property,
selection and hydration semantics to public ReadSession methods, including fact_statement and
hydrate_rows. `serve/queries.py` composes those contracts. The fact that named query policy and
primitive QuerySpec remain distinct is insufficient to establish duplicate semantic authority.
The earlier diagnosis is recoverable in Git before this refresh. This does not certify every
plugin or every query's physical plan.

<a id="da-039"></a>

## DA-039 — Ordinary explanations and relation paths lack work bounds

**Principles:** FP-07/A4, DP-12/20/21, CI-08. **Subject:** implemented.

`semantic/query.py:1576–1801` loads all supports, evidence, source observation payloads,
derivations, assessments and whole-realization coverage for one fact. `serve/explain.py:60–142`
likewise materializes task bodies and observations for a unit. `cli/explain.py:16–47` has no
resource/output bound; `serve/read.py:236` obtains evidence by constructing that full explanation
before the evidence query applies its cursor. Every evidence page can repeat unrelated work.

`domains/statistics/queries.py:329–362` uses recursive UNION ALL to enumerate paths through
four edges, with no visited-set or frontier/work bound, and sorts paths for each request.
The returned depth is explicit, but the maximum traversal depth is implementation policy rather
than a declared answer-completeness field. A page bound limits emitted rows, not the expansion or
sort needed to obtain them. Cycles can generate repeated-node paths; dense input expands the
frontier despite shallow depth. `cli/query.py:139–140` defaults row/character bounds to None.
These sources establish structural amplification, not a measured latency or memory result.

Counterevidence: traversal anchors at the requested source; final rows filter to the target
after expansion. Depth four guarantees termination; fact selection/hydration is
batched, and named continuations are keysets. M1 record readers have explicit record/row/byte
and page bounds (`serve/record_results.py:49–74`), and native source requests have distinct
limits. Those strengths do not bound this ordinary explanation/path route.

<a id="da-050"></a>

## DA-050 — Prior missing pinned follow-up route removed

**Source-inspected correction, 2026-11-03.** `cli/explain.py:35–45` accepts a query token and uses
`cli/query.py:66` followup_context to resolve its pinned run/query compatibility before explaining.
`serve/explain.py:49–53` checks the producing release and returns its query binding. Explicit run
selection also remains supported. A fresh promoted request intentionally selecting current state
is not by itself a violation. Consumers must use the provided binding for continuation of an earlier
journey. Full actual multi-call transport qualification was not run here.

<a id="da-051"></a>

## DA-051 — Configured identity exceeds what some executing-provider boundaries establish

**FP-02/04/05, DP-05/21, CI-01/10; implemented, source-inspected 2026-11-03.**
Manual MCP leases match agent.opus/mode without establishing that the executing session matches
the configured model (`intervene/semantic_server.py:142–159`). Automation chooses --model and
retains raw receipts (`intervene/automated.py:184–185,249–265`), but returned provider/session
information is separate from task-bound proposal attribution (`:325–328`).

PDF recognition accepts configured weight/tokenizer digests (`ingest/pdf_recognition_methods.py:72–78,99–105`)
and publishes them in the provider binding (`ingest/pdf_recognition.py:608–623`). The worker sends
and records a model alias (`services/nemotron-parse/worker.py:49–57,72–83`, repository-relative),
checking local parser package versions (`:103–106`) rather than the endpoint's loaded model bytes.
A server changed under the same alias can therefore violate recorded producer/reuse premises.
This is a boundary-contract diagnosis, not an observed wrong-model run.

The dedicated service has pinned startup instructions, and submitted images/HTTP bodies/response
model are retained. Local GLiNER verifies artifacts before load (`methods/gliner.py:111–132,321–330`),
so the old system-wide claim that provider identity is never established is false. Manual sessions
also have an explicit operator trust premise; identity not measured at that boundary must not be
presented as independently authenticated execution identity.

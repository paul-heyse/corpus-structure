# Served claims and evaluation

**Implemented source inspected, 2026-11-03.** See the [current baseline](README.md#baseline).
Paths below are relative to `python/corpus-structure/src/corpus_structure/`, unless prefixed
with `domains/`. This is static diagnosis, not native or consumer qualification.

<a id="da-035"></a>

## DA-035 — Ordinary coverage envelope amplification corrected

**Source-inspected 2026-11-05.** `serve/journey.py:243–267` obtains a summary and requests bounded detail only for an explicit
predicate requirement. Ordinary unfiltered pages no longer append the cited whole-realization
coverage population. Full coverage remains a legitimate explicit consumer. No timing or capacity
result follows from source inspection.

<a id="da-036"></a>

## DA-036 — Ordinary fact rows now carry standing

**Source-inspected 2026-11-05.** `semantic/query.py:178–209` defines FactStanding and QueryRow.standing; hydration supplies it
at `:644`. Selection, assessment and establishment remain independent dimensions rather than one
aggregate verdict. The prior missing-row-standing premise is removed; this is not a claim that
every historical or third-party consumer displays every field.

<a id="da-037"></a>

## DA-037 — Split assignment now preserves immutable policy provenance

**Source-inspected 2026-11-05.** `evaluate/semantic.py:555–603` calls `eval.assign_document_split_decision` with frozen intent.
`evaluate/split_decisions.py:63–89` retains assignment reason/seed and ordered policy/seed origin.
The earlier write-path provenance omission is corrected. No evaluation population quality claim
or new database execution is implied.

<a id="da-038"></a>

## DA-038 — Prior private read-boundary diagnosis removed

**Source-inspected correction, 2026-11-03.** `serve/read.py:43–60` delegates scope, property,
selection and hydration semantics to public ReadSession methods, including fact_statement and
hydrate_rows. `serve/queries.py` composes those contracts. The fact that named query policy and
primitive QuerySpec remain distinct is insufficient to establish duplicate semantic authority.
The earlier diagnosis is recoverable in Git before this refresh. This does not certify every
plugin or every query's physical plan.

<a id="da-039"></a>

## DA-039 — Explanation and relation-path bounds corrected

**Source-inspected 2026-11-05.** `serve/explain.py:58–94` supplies explicit limit/max_bytes; unit metadata is paged at
`:141–199`. `domains/statistics/queries.py:34–40,353–446` bounds depth, examined edges, frontier and retained bytes; the
old blanket absence-of-bounds claim is removed. Limits constrain exposure and work; they alone
do not establish normal-workload feasibility or a measured performance benefit.

<a id="da-050"></a>

## DA-050 — Prior missing pinned follow-up route removed

**Source-inspected correction, 2026-11-03.** `cli/explain.py:35–45` accepts a query token and uses
`cli/query.py:66` followup_context to resolve its pinned run/query compatibility before explaining.
`serve/explain.py:49–53` checks the producing release and returns its query binding. Explicit run
selection also remains supported. A fresh promoted request intentionally selecting current state
is not by itself a violation. Consumers must use the provided binding for continuation of an earlier
journey. Full actual multi-call transport qualification was not run here.

<a id="da-051"></a>

## DA-051 — Provider attribution now exposes its actual assurance

**Source-inspected 2026-11-05.** `intervene/semantic.py:175–186` persists task/attempt/holder, producer binding and explicit
manual_operator/provider_reported assurance. `intervene/semantic_server.py:90–119` links task
receipt events to invocation. Recognition declares identity assurance and authenticates managed
generation manifests (`ingest/pdf_recognition.py:44–52,128–175`); the worker requires the same
generation header (`services/nemotron-parse/worker.py:78–92` (repository root)). Requested/response model and
configured digests are separately recorded (`ingest/pdf_recognition.py:647–656`). Configured
identity is no longer silently presented as measured model bytes in these paths. External service
execution and every third-party response shape were not qualified in this audit.

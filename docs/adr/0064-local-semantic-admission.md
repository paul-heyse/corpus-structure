---
id: ADR-0064
title: Publish independently judged local semantics through a later ordinary consolidation
status: accepted
date: 2026-11-05
supersedes: []
superseded-by: null
design: [§B1, §B2, §B5]
evidence: Proposed
revisit: A useful independently assessed local event cannot retain exact source, statement and producer custody through ordinary run reuse and consolidation.
---

## Context

ADR-0062 accepts qualified local publication before complete records. PCE-04 now implements
that target. Deterministic captured-source extent checks can qualify exact quotations, but
cannot qualify their semantic denotations. The existing operation assessor requires completed
runs; a run's first consolidation cannot consume a grade that exists only after it completes.
Completed task products, reference passes and realized results are immutable.

## Options

1. Publish lexical matching or retrieval confidence as semantic authority. Rejected: neither
   establishes what the source usage denotes, and quotation fidelity answers a different event.
2. Let grading append knowledge to an already completed result. Rejected: this adds another
   publication authority and changes the meaning of immutable completed-result snapshots.
3. Freeze protected grade bindings as publication-only dependencies of a later ordinary run.
   Selected: reuse the exact immutable producer origin, then use the existing consolidation,
   atomic publication, native custody, receipts and readers. This needs a second inexpensive
   run, but avoids repeated encoder work and a separate store or post-completion workflow.

## Decision

Local publication policies declare the precise event and applicable witness. Captured extent
and literal policies authenticate exact retained text; they claim neither original glyph fidelity
nor semantic role correctness. An independently judged contextual denotation policy requires
the protected current C snapshot, supported stated case, exact complete semantic statement,
source frame/anchors, question/version, rubric/context and captured grade contribution.
Producer confidence and a grade label without that closure are insufficient.

The later run freezes evaluation identity/digest in its full dependency manifest. Only that
publication setting is excluded from source-producer reuse determinants; source, configuration,
release and executable runtime custody still apply. Native publication confirms that the new
cut contains the same immutable producer origin/contribution assessed by the earlier completed
run. It recomputes expected-statement equality and rejects stale, foreign, ambiguous, partial
or inapplicable witnesses. All selected rows enter the same PublicationBatch and transaction.

Semantic statement identity excludes generated list/decision/producer IDs. Those IDs remain
exact derivation provenance. A semantic claim and its admitted source/producer witness have
separate identities. Public readers expose the event, policy, assessment basis, source closure
and standing without granting ordinary producers protected-label access. Whole-record admission,
canonical identity exclusions and scientific-support semantics retain their stronger boundaries.

## Consequences

Useful semantic contributions can become public after independent assessment without changing
historical bytes or complete-record acceptance. Target descriptors remain curated inputs;
admitted denotation does not assert a canonical entity, a mathematical theorem, calibrated
probability or uninspected corpus coverage. One protected grade read and set-oriented lowering
per selected publication avoid per-span transactions and repeated model calls.

Implementation and native/provider/query qualification remain owned by the
[PCE coordinator](../plans/progressive-corpus-enrichment_2026-11-04.md), not this decision's status.

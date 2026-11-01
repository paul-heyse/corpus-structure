# Plan improvement reviews

Reviews here assess the remaining change footprint of an implementation plan or coordinated
plan series. Use [plan-improvement-review](../../.claude/skills/plan-improvement-review/SKILL.md)
to identify design-principle alignment improvements, general enhancements and better execution
approaches across materially affected components and consumers. An improvement's value can
extend beyond the plan's functional target; recommendations are judged for coherent integration
and total burden.

## Publication and traceability

Use `<subject>_<YYYY-MM-DD>.md` for a review. Identify the reviewed coordinator and relevant
supporting plans, review date, inspected source and plan baseline, relevant uncommitted changes,
selected footprint and material coverage limits. Explain the combined judgment, recommended
amendments, their benefits, relevant principle references, enabling mechanisms, alternatives,
interactions and integration consequences. Flexible Markdown is sufficient; structure follows
the argument rather than a fixed schema or recommendation quota.

Give recommendations stable references such as `I01`, cited as `review-path#I01`, with explicit
anchors. Preserve them when recommendations change and link related source findings using their
existing identities. Distinguish alignment opportunities and optional enhancements from observed
defects or missing accepted obligations. Follow the repository's evidence vocabulary and preserve
the dates and limits of historical receipts.

## Review and adoption

Publishing a review is separate from updating the plan. Recommendations remain proposals until
selected through the existing planning and decision routes. The operator can request plan
revision directly from this document; no separate update skill or preparation artifact is needed.
The review itself does not amend accepted scope, progress or completion criteria, authorize
implementation, refresh a diagnostic audit or replace a formal design review due under the binding.

When recommendations are incorporated, retain their source references, rationale and concrete
mechanisms in the relevant plan target and packages. The owning plan holds current scheduled
scope, disposition and closure evidence. Unselected recommendations remain in the source review
with their material next decision or revisit condition; do not create another mutable register.

Retain a review while it has a current consumer. Carry surviving obligations and enduring knowledge
to their owners before retirement; Git preserves earlier accounts. Creating this collection
performs no review and changes no implementation plan.

## Published reviews

- [PDF/PostgreSQL capability integration](pdf-postgresql-capability-integration_2026-11-01.md):
  proposed shared model/transfer, nested Arrow compute, context/lifetime and native-authoring
  amendments for PDF-27/28 and affected owners; plans unchanged, no product qualification.

- [PDF structured data — Arrow payloads and PostgreSQL responsibilities](pdf-docling-structured-data_2026-11-01.md):
  proposed hybrid placement, Pydantic/Arrow contracts, validation boundaries and general PDF
  pipeline improvements; one bounded library probe, no adopted plan or production changes.

- [Semantic-model pivot — library-focused improvement review](semantic-model-pivot_2026-10-29.md):
  proposed coordinated amendments, current CBO-001–025 judgments and CA-01–CA-11 coverage,
  including improvements to completed capabilities.

- [PDF/Docling streaming improvements](pdf-docling-streaming-improvements_2026-11-01.md):
  functional-extension-focused proposals for native finalization, scheduling, custody, typed transfer
  and richer selective content; no accepted plan changes.

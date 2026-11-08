# Operational outcomes and evidence custody

**Proposed · 2026-11-08.** D8 and ADR-0069 govern the managed result boundary.
This plan supplies DMA-08. The [coordinator](../domain-model-alignment_2026-11-08.md)
owns disposition. [Source review](../../design_review/reviews/design_review_domain-model-alignment_2026-11-08.md#make-operation-receipts-durable-statements-about-outcomes-and-custody)

<a id="DMA-08"></a>

## DMA-08 · Preserve what happened and what is known about custody

The immediate error path can render a refusal that the managed result
records only as a generic failure. Deployment stdout can name a verified
target after the durable record retained only a candidate reference.
Evidence retention can copy a published artifact from a failed result
while losing the unresolved cleanup flag. These are different facts
and require different consumers.

Use the existing managed invocation and atomic manifest publication.
Add a versioned typed operation account for the affected model and
review routes. Preserve the safe refusal reason, execution outcome,
known settled effects, and verified target, predecessor and release when
applicable. Persist target and effects from the operation owner, using
DMA-02's verified target. Immediate and by-ID presentation consume the
same account. Preserve the existing command and result identifiers.
Scope refusal reporting to safe fields, and retain named artifact
delivery and leases. A legacy receipt with insufficient facts reports
unknown. It never fills them from the current checkout or an expired
candidate.

Track whether cleanup and artifact custody are established independently
of the terminal outcome and timestamp. The existing evidence promotion
command refuses promotion as settled when custody is unresolved. Use
ordinary by-ID inspection or authorized diagnostic artifact delivery to
investigate the unresolved result. Keep settled failed evidence eligible.
Avoid turning output streams, candidate holds or the existence of a file
into evidence of completed custody. The same by-ID view can report
DMA-09 routing progress from the native decision without a second
routing authority.
[Managed invocation](../../../python/corpus-structure/src/corpus_structure/cli/managed.py) ·
[Model operation](../../../python/corpus-structure/src/corpus_structure/cli/model.py) ·
[Evidence retention](../../../python/corpus-structure/src/corpus_structure/cli/operations.py#L299) ·
[CLI custody decision](../../adr/0069-cli-operations-custody.md)

**Closure.** Exercise a stale preview refused before writes and a failure
after independently observed partial effects. Compare immediate and
retained meaning. Verify that the deployment receipt identifies the
acquired target after candidate collection. Refuse settled evidence
promotion for a terminal-looking selection with cleanup unresolved and
accept a settled failed artifact with correct attribution. A legacy
receipt with no retained target keeps an explicit unknown.

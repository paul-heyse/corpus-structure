# PM2 learned extraction investigations

**Proposed; conditional · 2026-11-09.** This companion supplies decision designs for
[PM2-03](linguistic-referential-discourse.md#PM2-03), [PM2-07](gliner-and-d1-interpretation.md#PM2-07)
and [PM2-11](textbook-assessment-and-adoption.md#PM2-11). The
[coordinator](../production-milestone-two_2026-11-08.md#extraction-improvement-disposition)
owns disposition. The [improvement review](../../plan_improvement_reviews/pm2-extraction-gliner2-spacy_2026-11-09.md)
at `d4a40cd6e` supplies I05, I06 and I09. No fitting, new checkpoint, default change
or production dependency is selected. Complete the smaller producer and deterministic
repairs first; unavailable supervision is a reason to keep the incumbent.

## Choose the investigation from the diagnosed loss

Use the existing released source, operation, candidate and evidence owners. Prepare
the PM2-11 frame from authenticated source before reviewing new predictions. Decide
whether a gold extent could be represented under the selected token layout, whether
a source-produced proposal included it, whether it was labeled correctly, and whether
the correct typed relationship was selected. Track unavailable or unalignable examples
rather than conditioning the coverage measure on what a model could represent. Treat
reviewed-candidate injection as a diagnostic ceiling. The ordinary route still has to
find its own candidates.

| Diagnosed loss | Next bounded comparison | Stop or defer when |
| --- | --- | --- |
| Exact span exists in the proposal inventory but a label is wrong | Named rules versus GLiNER2 scoring and stock spaCy span classification on the same eligible extents | No independently judged labels, no gain at the consumer, or loss of a protected control |
| Alignable reference span is absent | Improve named rules or add a suitable parser proposal; compare bounded SpanFinder only on residual proposal loss | Missing source map or uninspected context explains the miss, or more spans do not recover a correct occurrence |
| Right focal and candidate roles exist but the wrong directed pair is chosen | Released deterministic binding and fixed-candidate model comparators, then a light pair scorer if errors recur | Simplest route settles the case, no repeatable error or insufficient independent binding/abstention labels |
| GLiNER2 still misses a released task after mapping and configuration repair | Same-task unchanged zero-shot comparator versus a bounded adapter; full tuning only for remaining material error | No suitable supervision, no injection-free gain, or unsupported lifecycle/custody |

## Span labeling and proposal recall

Use the existing named-rule `SpanRuler` and preset suggester seam as input, not as a
trained component. The reconciled group currently mirrors contiguous raw candidates and
does not supply complete named-role geometry. Build a scoring view of unique eligible
contiguous extents, with a separate provenance mapping to every original role, generator
and occurrence. An extent proposed by two rules is not two source occurrences; equal
strings at different offsets are distinct. Keep partial expansions and discontinuous
roles in their typed products rather than coercing them to a contiguous label.

With spaCy `3.8.18`, select `spacy.preset_spans_suggester.v1` for the prepared input group
and a different output key. Initialize the input group even when empty. Use `set_candidates`
to inspect the suggested population when diagnosing recall. Start with stock
`SpanCategorizer`: multilabel when the same span can express independent roles, single-label
with a negative class when meanings are exclusive. Compare fixed candidates with the current
rules and the same-question GLiNER2 arm. Inspect scores before output thresholding when
needed; an empty output group is not an empty input group. If the correct candidates
reach the head but the label is wrong, compare a configured encoder, reducer or scorer
before replacing the component. Stock span loss treats missing gold labels on offered
spans as negatives; use a fully adjudicated slice or a task with an explicit supervision
mask. NER's missing/outside/blocked states and `incorrect_spans_key` do not mask stock span loss.
[SpanCategorizer contract](https://spacy.io/api/spancategorizer) ·
[Prepared annotation rules](../../../python/corpus-structure/src/corpus_structure/methods/annotation_rules.py)

For a genuine proposal miss, compare bounded rule/parser alternatives with `SpanFinder`,
using canonical input scopes and an exact map back to source. Its thresholded start/end
pairs do not enforce source atom or sentence boundaries themselves. Compare only meaningful
length and threshold choices and retain out-of-scope reference cases; do not enumerate
unbounded spans or replace `Doc.ents` just to gain an alternative label. Require independently
correct extra spans, viable coverage on the ordinary path and preservation of overlapping,
nested and repeated cases at the qualified consumer. If labels rather than boundaries are
wrong, stop this proposal investigation. [SpanFinder contract](https://spacy.io/api/spanfinder)

## Typed binding scorer

The fair-coin host and gambler referent remained unresolved even with reviewed candidates.
Start with the current exact, released selector, scoped deterministic cues and d1 on the
same fixed list. A stronger span encoder alone cannot choose a directed relation between
two exact spans. Proceed only when a recurring fixed-candidate error has independently
judged positive, incorrect, ambiguous and no-supported-choice cases.

Compare a lightweight scorer over bounded features from retained roles and native syntax
before fitting a custom component. For a justified custom spaCy task, use a registered
factory receiving an injected Thinc model through `TrainablePipe`. The scoreable unit is
a typed focal role, candidate role and declared relation, within the released scope.
`predict` scores alternatives without mutating the source; `set_annotations` exposes only
private scores/proposals; the loss masks unjudged alternatives and the scorer checks exact
binding and abstention. Preserve ordered pieces for discontinuous roles. The relation
and independent witness remain with the release, contribution and admission owners.
Prefer separate pair scores and released compatibility checks to a joint decoder unless
a supported coupled-decision error warrants one.
[Custom spaCy components](https://spacy.io/usage/processing-pipelines) ·
[TrainablePipe](https://spacy.io/api/pipe)

Start with lightweight contextual features or `Tok2Vec`. Reuse a sourced encoder only
under its pinned annotation and listener contract. Pin configured sourced, frozen and
annotating components; use `replace_listeners` or freeze the shared upstream weights
when required to preserve an incumbent. Try curated or Hugging Face transformer
listeners only after held-out evidence shows a limitation of the lighter representation.
Qualify compatible companion versions, canonical token and subword alignment, input
bounds, artifact reload and device custody before any operational change.
[spaCy training and listeners](https://spacy.io/usage/training) ·
[Representation alternatives](../../libraries/parsing/spacy.md#6-neural-architectures-representations-and-transformers)

Use aligned `Example` objects and `DocBin` where it preserves supervised fields;
use a registered corpus reader for typed endpoint labels where needed. Retain exact
source IDs and label availability in the existing evidence owner, not only in
`Doc.user_data`. Train on the predicted upstream annotations the runtime will see;
keep a separate reviewed-candidate control. Group holdouts by source unit and keep
prompt examples separate. Use native config/data diagnostics and package the artifact
with the registered code, effective config, labels, tokenizer and pins. A new released
vocabulary can use the same adapter and eligibility path; learned labels with changed
meanings require their own model qualification.

Require an independently supported binding gain and correct abstention on the same
candidates, without regression on direction, passive, coordination, missing candidate
or competing-host controls. Carry the qualified result and unresolved alternatives
through PM2-08. A tie, missing evidence or unacceptable execution or replay burden
retains the simpler route.

## GLiNER2 specialization

[NCE-M03](../next-corpus-enrichment/model-candidates-and-clause-interpretation.md#NCE-M03)
and [NCE-M06](../next-corpus-enrichment/model-candidates-and-clause-interpretation.md#NCE-M06)
retain their investigation ownership. For a persistent PM2 error after exact alignment,
proposal and configuration repairs, use the same released task and pinned GLiNER2.5 Base
zero-shot comparator. Compare a task-specific LoRA/DoRA adapter only with sufficient
independent supervision; full tuning is a later alternative if a smaller intervention
leaves a material residual. Do not assume inference-time span attributes have independent
training support. Bind the checkpoint, adapter, PEFT and effective runtime to the task;
isolate mutable adapter state under concurrent requests.

Validate exact character spans, representability, relation consistency and capacity with
the native tools. Preserve repeated and nested labels, and inspect default contained-span
deduplication. Keep unknown labels separate from explicit negatives. Use gold injection
only for training or a separate diagnostic; measure proposal recall with injection off,
including long or rare exact spans. Prefer strict failures over silent sample loss.
Require a correct independently graded consumer result and preserved controls before
selection. Distributed training and broader pretraining stay outside the selected scope.
[GLiNER2 training and objectives](../../libraries/parsing/gliner2.md#8-training-and-model-specialization)

### Entry from structuring diagnostics

[Structuring I04–I05](../../plan_improvement_reviews/pm2-structuring-and-dma13_2026-11-09.md#I04) use the
[PM2-07 bounded controls](gliner-and-d1-interpretation.md#packed-boundary-and-attribute-comparisons)
before selecting a training investigation. Preserve the stock preset-span/SpanCategorizer
route for label loss, SpanFinder for residual proposal loss, and typed occurrence pairs for
binding loss after deterministic alternatives. Use a lightweight scorer before a custom
`TrainablePipe`; require independently judged pairs or complete/masked supervision.
For residual GLiNER loss use native alignment/capacity checks and
`dry_run_recall_steps` with gold injection off, then compare LoRA/DoRA with the pinned
unchanged checkpoint. A successful oracle arm or improved score alone does not warrant
training or selection. Unavailable supervision or no downstream gain retains the incumbent.

## Evidence and disposition

PM2-02 owns profile, resource and reuse qualification. PM2-11 owns the matched frames,
decisions and stop criteria. PM2-08 owns admission and delivery; a score cannot supply
a source witness or semantic standing. Record the selected mechanism and remaining
uncertainty in the existing package, or retain the incumbent and state what evidence
would reopen the investigation. Optional work becomes a qualification requirement
only for an explicitly selected release operation.

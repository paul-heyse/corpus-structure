# M1 native state inspection on three frozen development contexts

Date: 2026-11-04. Standing: **Tested** for the nine native API calls and their
reported outputs only; **Proposed** for the recommendation below. No accuracy,
calibration, source-absence, assembled-record or final-data qualification claim.

The question was whether richer natural-record state descriptions, or a separate
native classifier with label descriptions and a named record/role question, could
help with current M1 state proposals. A third passage tests whether changing an
assertion's natural anchor from `predicate` to `subject` restores candidate groups.
All source text came from the retained Grinstead–Snell development task 27 in run 10.
No reference labels, final data, Forbes or NIST material were read. There were no
DB writes, provider requests, PDF/OCR work, new dependencies or library patches.

## Frozen inputs and comparison

[`frozen-inputs.json`](frozen-inputs.json) contains the exact text, SHA-256,
context ID/digest, original piece selection, source-only selection reason, profile,
threshold, release, complete schemas and pack fingerprints. It was written before
new model outputs. Its SHA-256 is
`c2bcc19bb8cb8f5b22adafd48738ca41f14aab0de9a141d0c24a15bcd753d2d8`.

Reconstructed consumed-text hashes and baseline pack fingerprints matched the
retained task 27 reports before inference. The source text preserves the canonical
projection's joined words, formula spelling, context-piece order and synthetic
separators; this probe performs no cleanup. In particular, context 4's header and
formula follow the prose, and context 55's formula follows its prose.

| Context index | Family and source-only selection | Second variant |
| --- | --- | --- |
| 4 | Definition passage with literal `is defined to be`; named record `distribution functionm(\\omega)` | Same natural term anchor and actual described pack, with richer per-state field descriptions spelling out each label and same-term attachment |
| 55 | Naming passage with literal `is called`; named record `"memoryless" property` | Same richer state descriptions, term anchor unchanged |
| 57 | Explicit coin probability-of-heads clause; named record `a coin` | Same actual described assertion pack, changing only natural anchor `predicate` to `subject` |

Each context has three calls: (1) the exact task 27 natural pack, (2) the variant
above, (3) a separate `Schema.classification` pack. The third variant supplies
label-to-description mappings and explicit named-record questions about term and
defining text, or subject/predicate/object. Named records are source-selected
strings for this canary; no automatic candidate-to-question mechanism was tested.
The classifier uses the same exact context text, not cropped or rewritten text.

The definition baseline already had value-field descriptions. The second variant
therefore tests richer **state-field** descriptions; it is not a comparison of
all descriptions against no descriptions. The assertion second variant tests only
anchor choice, and subject/predicate/object remain necessary interpretation fields.

## Actual results

[`results.jsonl`](results.jsonl) retains each complete native `GlinerReport`, its
raw output/confidence, preparation, effective profile, schema identity, call wall
time and child CPU time. [`retained-baseline-reports.json`](retained-baseline-reports.json)
retains the selected earlier task 27 reports. Both the retained baseline and all
six newly executed natural-record variants returned `{}`. Thus this selection
does not reproduce the contradictory state/value groups from other passages and
does not identify whether their state fields took the per-record or fallback path.

The separate classifier returned:

| Context | Native classified role | Returned label | Native score |
| --- | --- | --- | --- |
| 4 | term | present | 0.9852361679077148 |
| 4 | defining_text | present | 0.9845519661903381 |
| 55 | term | present | 0.9382111430168152 |
| 55 | defining_text | present | 0.8942915797233582 |
| 57 | subject | present | 0.5316889882087708 |
| 57 | predicate | present | 0.7340756058692932 |
| 57 | object | present | 0.6090168952941895 |

These are actual native output scores, not calibrated correctness probabilities.
The classifier supplied state proposals but no source spans, defining clauses,
subject/predicate/object values or group associations. It cannot by itself restore
an assembled record. The named question supplies the candidate identity externally;
the results do not establish automatic record discovery. Only positive-wording
source canaries were selected, so no result here supports absence/inapplicability
behavior or specificity. Selection on source wording also prevents a general
precision/recall interpretation.

**Proposed disposition: defer production adoption of the separate classifier.**
Its native named-record state-question mechanism executed successfully and remains
a credible development alternative. This bounded comparison did not show richer
state descriptions or subject anchors recovering value/group output. It leaves
candidate extraction and association unresolved. Neither a `present` classifier
answer nor empty natural output can replace independent semantic fit/calibration
or establish source absence. Production integration remains the coordinator's
decision; no production recipe changed.

## Execution and reproduction

The existing `GlinerWorker` executed nine serial calls in its CPU4 child with the
task 27 profile: `gliner2==2.1.0`, CPU FP32, standard attention, whitespace splitter,
local `fastino/gliner2.5-base-v1` snapshot revision
`54785d51df8d86a0d8f2eb212fec15871aad2c4d`, threshold 0.5, flat overlap and
`include_spans=True`, `include_confidence=True`, `max_len=None`. Exact artifact
hashes and preparation bounds are frozen. The child uses the existing offline
environment and credential removal. No server setting changed.

`uv run python docs/design_review/evidence/2026-11-04_m1-state-inspection/freeze_inputs.py`:
**passed** on the final attempt. Earlier preparation attempts failed before
inference because current policy/release changed; their errors are retained in
[`preparation-attempts.json`](preparation-attempts.json). The successful route uses
the archived run 10 release through the read-purpose runtime rather than current
domain regeneration.

`uv run python docs/design_review/evidence/2026-11-04_m1-state-inspection/run_probe.py`:
**passed**, nine of nine API calls returned; process joined. The runner's exclusive
output creation prevents accidental overwrite/re-run of this evidence. See
[`run.log`](run.log) for native warnings and per-call execution entries, and
[`receipt.json`](receipt.json) for the complete receipt.

Measured whole-run wall time was 16.168532664996746 seconds; child user CPU was
31.045346 seconds and system CPU was 8.515093 seconds. Peak child RSS was
2,458,864 KiB. These are this probe's measurements, not a performance prediction.
Per-call child CPU comes from Linux `/proc/<pid>/stat` utime+stime; cold-call cost
includes child startup/model loading and preparation. Native inference wall time
is separately retained in each `GlinerReport`.

Product tests, integrated qualification and DB/model bootstrap: **not_run**; outside
this bounded capability question. No further calls were made after the nine-call
limit in this first comparison. The root owns evidence-record integration,
formatting and handoff. A separately authorized three-call follow-up is below.

## Separately authorized threshold follow-up

After examining the first nine outputs, the coordinator authorized exactly three
additional actual calls with the same frozen inputs and **baseline schemas only**,
changing only threshold from 0.5 to 0.15. No passages were reselected and no schema,
anchor, profile or text changed. The original nine-call evidence is untouched.
[`attempt-low-threshold001/request.json`](attempt-low-threshold001/request.json)
freezes this follow-up before its calls; [`run_low_threshold.py`](run_low_threshold.py)
executes it through the same worker.

The three calls **passed** and the child joined, verified 2026-11-04. Contexts 4
and 57 still returned `{}`. Context 55 returned one group with these actual fields:

| Field | Native output | Native score |
| --- | --- | --- |
| term | memoryless | 0.3513393700122833 |
| defining_text | memoryless | 0.20745094120502472 |
| alias | null | none |
| relation_type | definition | 0.962374210357666 |
| term__state | present | 0.3099428117275238 |
| defining_text__state | inapplicable | 0.710545539855957 |
| alias__state | present | 0.9970716238021851 |
| relation_type__state | unresolved | 0.3597358465194702 |
| relation_type__cue | exponential distribution | 0.44514310359954834 |

The `defining_text` output is the same `memoryless` span as the term, rather than
an extended defining clause. Its simultaneous `inapplicable` state is a conflicting
value/state proposal. The alias state proposes present while no alias value is
returned; that omission does not establish source absence or by itself disprove
the state proposal. Native enum offsets are not source evidence for those labels.

This establishes that the 0.5 cutoff suppressed at least this returned candidate.
It does not establish whether proposal recall, grouping, schema conditioning or
model fit accounts for the two remaining empty contexts. High-level output exposes
no reason trace; no additional inference, threshold retry or hidden model run was
used to invent an explanation. Lowering the cutoff does not settle the observed
clause/value/state issues, nor does this canary establish an appropriate cutoff.
The proposal remains to defer the classifier's production adoption and retain the
candidate-generation/semantic-fit questions for their owning work.

Full raw output, spans, confidences and per-call CPU/wall times are in
[`attempt-low-threshold001/results.jsonl`](attempt-low-threshold001/results.jsonl).
The [receipt](attempt-low-threshold001/receipt.json) records 10.18320923599822
seconds whole-run wall, 14.406552 child user CPU seconds, 3.865652 child system CPU
seconds, 2,459,444 KiB peak child RSS, and joined process. The
[log](run-low-threshold001.log) preserves native warnings.

Command: `uv run python docs/design_review/evidence/2026-11-04_m1-state-inspection/run_low_threshold.py`:
**passed**, exactly three native calls, no additional threshold calls.

## Separately authorized core-only schema follow-up

The coordinator subsequently authorized exactly three more native calls on the
same frozen contexts, removing **only** fields whose names end with `__state` or
`__cue` from each baseline schema. Core fields, descriptions, cardinality, original
natural anchors, threshold 0.5 and the pinned profile remain unchanged. This is a
native configuration/candidate-capture diagnostic, not a waiver of source inspection
or semantic admission and not a change to the production recipe. The preceding
nine-call and three-call artifacts are unchanged.

[`attempt-core-only001/request.json`](attempt-core-only001/request.json) freezes
complete schemas and their SHA-256 values before model output. Definitions remove
five fields; the assertion removes eleven. A structural comparison with each
original baseline confirmed that no other schema content changed. Request SHA-256:
`f425b9f15c981786bc30a40848a49c4590e0bf68b1cc1984d38b2a301c9f7aa9`.

All three API calls **passed** and the worker process joined, verified 2026-11-04.
Contexts 4 and 57 still returned `{}`. Context 55 returned:

| Field | Actual native output | Native score | Character span |
| --- | --- | --- | --- |
| term | memoryless | 0.8599505424499512 | 213:223 |
| defining_text | null | none | none |
| alias | qs | 0.9525741338729858 | 405:407 |
| relation_type | definition | 0.9786954522132874 | none |
| group confidence | native group score | 0.8599505424499512 | none |

The alias points into the retained formula suffix. No defining clause was emitted.
No state fields were requested or returned; their absence is not an unstated or
inapplicable source-state proposal. This supports a concrete schema-dependent
capture difference for the memoryless canary: the baseline with auxiliary fields
returned `{}` at 0.5, while this core-only schema produced a group at 0.5. It does
not isolate a specific neural cause or establish an adequate definition record.
The explicit uniform-definition and coin-assertion canaries still produced no group;
the high-level API provides no reason trace for those empty results.

Core-only native preparation used 369, 311 and 370 subwords respectively for
contexts 4, 55 and 57; the same contexts with baseline auxiliary fields used
792, 734 and 1261 subwords. Exact preparation is retained in both result sets.
Any later separation of value extraction and inspection would need its
own versioned contract and fit assessment; this diagnostic alone does not authorize
or establish that design. The production recommendation remains deferred to the
coordinator. No further calls were made.

Raw outputs, confidences, exact preparation and effective profile are in
[`attempt-core-only001/results.jsonl`](attempt-core-only001/results.jsonl).
The [receipt](attempt-core-only001/receipt.json) records 8.827994077997573 seconds
whole-run wall, 11.906769 child user CPU seconds, 0.884686 child system CPU seconds,
2,460,964 KiB peak child RSS and joined process. The
[log](run-core-only001.log) retains native warnings.

Command: `uv run python docs/design_review/evidence/2026-11-04_m1-state-inspection/run_core_only.py`:
**passed**, exactly three authorized calls. Product qualification: **not_run**.

## API grounding and limits

Context7 was consulted first for schema classification syntax. Its official
[classification tutorial](https://github.com/fastino-ai/GLiNER2/blob/main/tutorial/1-classification.md)
shows label-description dictionaries; consequential syntax was checked against the
installed 2.1.0 `inference/schema.py:291–340` and `processor.py:1211–1284`.
Ordinary `Schema.classification` accepts `prompt`; the separate constrained
`ClassificationSchema.single` API uses `instruction`. This probe uses the former,
with no constrained decoder and no hidden language-model invocation.

In installed 2.1.0 `models/boundary/engine.py:1241–1319`, prefix enum candidates
selected by the record head retain their instance-conditioned assignment. The
fallback at `:1454–1465` calls `_decode_choice_field` (`:813–861`) without a record
or anchor representation. No high-level disabling switch was found in schema,
runtime, boundary configuration or record formatting. This bounded probe did not
instrument that route; empty groups do not explain the other passages' conflicts.
The installed engine matched upstream
[v2.1.0 source](https://github.com/fastino-ai/GLiNER2/blob/v2.1.0/gliner2/models/boundary/engine.py)
byte-for-byte during preceding read-only research.

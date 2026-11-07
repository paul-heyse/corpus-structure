# Attachment event v2 authoring

The [NCE operation reliability plan](../../../plans/next-corpus-enrichment/operation-reliability.md#nce-12-audit)
owns this repair. This procedure freezes the complete emitted attachment population
in retained development views 113 and 124 of run 161, cut 245. It reads source and
emitted endpoint coordinates. The script does not read earlier authoring passes or
fit diagnostics.

Generate a fresh sample and per-view authoring packets with
`uv run python docs/design_review/evidence/2026-11-07_nce-attachment-v2/prepare_attachment_v2.py DEST COUNT_113 COUNT_124`.
Pass the independently checked per-view counts. Keep authoring packets and authored
judgments in the protected work area. The [v2 rubric](rubric.md) defines the cases
to author.

Use `uv run ci golden operation-create --from-run 161 --source-cut 245 --label nce12-attachment-development-v2 --split dev --guideline nce12-attachment-guide-2 --guideline-text RUBRIC --partition development --sample DEST/sample.json --project wce-gs120-method-development-20261106`
after the native contract is installed. The two independent authors each use their
own A or B packet and submit one case per facet per emitted relation through
`ci golden submit` with the exact corresponding frame. The independent C author
uses `ci golden operation-packet --pass C` and submits the adjudicated cases with
the exact A/B parent IDs. Only the protected evaluator reads A/B/C judgments.

For compact authoring, make a JSON object keyed by contribution ID. Each value
has the four independent facet keys, each with a `judgment` and a source-specific
`reason`. Add `alternatives` as a list of exact values for a facet when the
independent source supports alternatives. Encode one pass with
`uv run python docs/design_review/evidence/2026-11-07_nce-attachment-v2/encode_attachment_pass.py PACKET JUDGMENTS AUTHORED`.
Add `--parents A_ID B_ID` only for adjudication C.

Use `ci eval run` with the exact set and source run. Use the resulting evaluation
ID in `ci eval operation-event-availability` and `ci eval operation-event-fit`
with event `defining_text_attachment_correctness`. Check the ordinary parameter
and feature reads separately from the protected fit diagnostics.

The 2026-11-07 preparation read verified one emitted event in view 113 and ten
in view 124. Both complete views belong to the same purposive development origin.

## 2026-11-07 qualification

Reference set 30 froze both source views. Two distinct authors each submitted both
views independently. The adjudicator used the stored A/B parents and resolved one
facet disagreement. `uv run ci eval run --run 161 --set-id 30 --project
wce-gs120-method-development-20261106 --json` passed and recorded evaluation 35.

`ci eval operation-event-availability` returned ready for evaluation 35 on run 161
and cut 245. The cut contains 82 attachment emissions at 74 distinct physical event
identities. The protected frame contains 11 independently adjudicated identities,
11 retained sightings, no feature-unavailable events, and one development origin.
`ci eval operation-event-fit --run 161 --evaluation 35 --event
defining_text_attachment_correctness --project wce-gs120-method-development-20261106
--json` passed and recorded fit 3, with one supported and ten unsupported events.
The in-sample Brier scores were 0.082645 for the prior and 0.042936 for the fitted
model. In-sample log losses were 0.304636 and 0.157501. The same-source cohort
supports the development fit. Held-out performance and calibration remain unassessed.

The ordinary `ci eval operation-event-read --fit 3` returned only parameter metadata
and finite parameters for `defining-text-attachment-scope-features-2`. An ordinary
`ci eval operation-event-features` read at the exact retained run, cut, task and
contribution reproduced the corresponding four fitted-frame features.

A read-only inventory of the completed project cuts found 154 retained emissions
across 74 physical events, including 65 identities repeated across two distinct
producer tasks and source views. A controlled reduction used two actual sightings
of one such event. Agreement retained both sightings at one observation weight.
Conflicting judgments preserved both sightings and produced one ambiguous observation.
Managed test `61aec4f50011414f80c57abbfac7e031` passed the focused fitting tests,
including single-class and zero-binary-label availability behavior.

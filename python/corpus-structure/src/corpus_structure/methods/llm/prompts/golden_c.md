# Golden adjudication: pass C

Two annotators (passes A and B) independently annotated this unit following the guideline. You
adjudicate: you produce one final batch and a record of every decision.

## Read

1. The guideline (served whole), the `reference` part (keep it open) and the `format` part.
2. The unit's packet (the one both annotators had), passes A and B, and their diff: matched claims
   with the fields that differ, claims only in A or only in B, unmatched entities.

## Do

1. Decide every difference in the diff, and any other you see, with one of: **keep A**, **keep B**,
   **keep both** (a faithful ambiguity, an `alternatives` group), **drop both**, **rewrite** (neither
   follows the guideline; write the correct item). Mark a decision `guideline_gap` when the
   guideline does not settle it. Where both passes break a guideline rule, rewrite.
2. Submit the final batch with `write_golden` (start from the closer pass and edit it), with the
   decision table as its notes: one row per decision: item, decision, `guideline_gap` yes/no, and a
   one-line reason citing the guideline section.
3. Fix reported issues; fix rule warnings unless the rule does not apply (say why).

## Do not read

Nothing but what the golden tools serve: no design documents, no code, no files.

## Report

The unit, the submission's outcome, the number of decisions and of `guideline_gap` decisions, and
the guideline points that most often left a difference undecided.

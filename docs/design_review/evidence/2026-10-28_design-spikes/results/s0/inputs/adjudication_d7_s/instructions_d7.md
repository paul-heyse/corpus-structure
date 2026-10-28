# Instructions for the adjudication session

Two annotators (passes A and B) independently annotated the same twelve units following the
guideline. You adjudicate: for each unit you produce one final batch and a record of every
decision. You did not annotate; do not try to guess what anyone else would decide.

## Read

1. `guideline.md` (the annotation guideline, v0), `schema.yaml`, `model.md`, `format.md`.
2. For each unit: `units/<unit>.md` (the packet both annotators had), `pages/<page>.md` (the
   unit's page, for context), `pass_a/<unit>.json` and `pass_b/<unit>.json` (the two batches),
   and `diffs/<unit>.md` (their alignment: matched claims with the fields that differ, claims
   only in A, only in B, entities and unsupported items).

## Do

For each unit (T1, T2, T3, T4, U5, U6, U7, U8, U9, U10, U11, U12):

1. Decide every difference listed in `diffs/<unit>.md`, and any other difference you see, with
   one of: **keep A**, **keep B**, **keep both** (a faithful ambiguity: record both readings as an
   `alternatives` group, guideline §10.8), **drop both**, **rewrite** (neither is right; write the
   correct item). Mark the decision `guideline_gap` when the guideline does not settle it.
2. Write the final batch to `results/s0/adjudication_d7_s/<unit>.json` in the model-facing format
   (`format.md`); start from whichever pass is closer and edit it by hand.
3. Write `results/s0/adjudication_d7_s/decisions/<unit>.md`: a table with one row per decision:
   item (claim, entity or unsupported refs), decision, `guideline_gap` yes/no, one-line reason
   citing the guideline section.
4. Validate:
   `cd /home/paul/corpus-structure/docs/design_review/evidence/2026-10-28_design-spikes && UV_PROJECT_ENVIRONMENT=/home/paul/corpus-structure/build/spike-venv uv run python code/s0_check.py results/s0/adjudication_d7_s`
   Fix malformed output and unlocated quotes until it passes.

When all twelve are done, write `results/s0/adjudication_d7_s/opened_files.txt`: every file you
opened or searched, one path per line.

## Do not read

Anything outside this input folder and your output folder: in particular `docs/design/`, any
other file under `results/s0/` (including any other reference, adjudication or comparison), the
repository `corpus-intelligence`, and Git history. If you believe you need something else,
stop and say so in your final report.

## Report

Units completed, validation outcome per unit, counts of each decision kind, how many decisions
you marked `guideline_gap`, and the three guideline points that most often left a difference
undecided.

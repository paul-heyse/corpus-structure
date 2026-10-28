# Instructions for the adjudication session

Two annotators (passes A and B) independently annotated the same units following the guideline.
You adjudicate: for each unit you produce one final batch and a record of every decision.

## Read

1. `guideline.md`, `reference.md` (keep it open), `format.md`.
2. For each unit: `units/<unit>.md` (the packet both annotators had), `pass_a/<unit>.json` and
   `pass_b/<unit>.json`, and `diffs/<unit>.md` (their alignment: matched claims with the fields that
   differ, claims only in A or only in B, unmatched entities).

## Do

For each unit (H1, H2, H3, H4, H5, H6, T1, T2, T3, T4, U10, U11, U12, U5, U6, U7, U8, U9):

1. Decide every difference in `diffs/<unit>.md`, and any other you see, with one of: **keep A**,
   **keep B**, **keep both** (a faithful ambiguity, an `alternatives` group), **drop both**, **rewrite**
   (neither follows the guideline; write the correct item). Mark a decision `guideline_gap` when the
   guideline does not settle it. Where both passes break a guideline rule, rewrite.
2. Write the final batch to `results/s0r2/adjudication_v1/<unit>.json` (start from the closer pass and edit it).
3. Write `results/s0r2/adjudication_v1/decisions/<unit>.md`: a table with one row per decision: item, decision,
   `guideline_gap` yes/no, one-line reason citing the guideline section.
4. Validate: `cd /home/paul/corpus-structure/docs/design_review/evidence/2026-10-28_design-spikes && S0_SAMPLE=results/s0r2/sample.json UV_PROJECT_ENVIRONMENT=/home/paul/corpus-structure/build/spike-venv uv run python code/s0_check.py results/s0r2/adjudication_v1 --rules`. Fix issues; fix rule warnings unless the rule does not apply (say why).

When all are done, write `results/s0r2/adjudication_v1/opened_files.txt`: every file you opened, one per line.

## Do not read

Anything outside this input folder and your output folder: no design documents, no other results,
no code, no Git history, no directory listings outside these two folders.

## Report

Units completed, validation outcome, the number of decisions and of `guideline_gap` decisions, and the
three guideline points that most often left a difference undecided.

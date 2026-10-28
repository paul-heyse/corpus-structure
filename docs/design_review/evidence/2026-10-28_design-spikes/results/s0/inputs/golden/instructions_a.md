# Instructions for annotation pass A

You are one of several independent annotators. Annotate the core units of this spike following
the guideline exactly. Your work is compared with other annotators' later; do not try to guess
what anyone else would write.

## Read

1. `guideline.md` (the annotation guideline, v0) — this governs what you capture.
2. `schema.yaml` (core and statistics schema v0: classes, predicates, qualifiers, enums).
3. `model.md` (the knowledge model: entities, claims, qualifiers, values, conditions, statuses).
4. `format.md` (the output format).
5. For each unit: `units/<unit>.md` (the unit packet; lines like `--- Details: ---` are headings
   inside the unit, such as the summary of a collapsible proof or solution) and `pages/<page>.md` (the unit's whole page, for context: read the page, annotate only the unit, guideline §10.2).

## Do

For each of the twelve units in `units/` (T1, T2, T3, T4, U5, U6, U7, U8, U9, U10, U11, U12):

1. Annotate the unit into one model-facing `ClaimProposalBatch` and write it to
   `results/s0/pass_a/<unit>.json` (e.g. `results/s0/pass_a/T1.json`).
2. Write `results/s0/pass_a/notes/<unit>.md`: every point where you had to guess, naming the guideline
   section that was unclear; any text that looks mis-rendered (garbled, missing words, odd
   markers); anything the schema could not express beyond what you recorded as `unsupported`.
3. Validate your batch and its quotes:
   `cd /home/paul/corpus-structure/docs/design_review/evidence/2026-10-28_design-spikes && UV_PROJECT_ENVIRONMENT=/home/paul/corpus-structure/build/spike-venv uv run python code/s0_check.py results/s0/pass_a`
   Before fixing anything, copy your first version of each batch to `results/s0/pass_a/first/<unit>.json`.
   Then fix malformed output and unlocated quotes, and validate again.

When all twelve are done, write `results/s0/pass_a/opened_files.txt`: every file you opened or searched,
one path per line.

## Do not read

Anything outside this input folder and your output folder, in particular: `docs/design/` (all
design documents, including the worked trace), any other annotator's output under
`results/s0/`, the repository `corpus-intelligence`, and Git history. The unit packets and page
texts here are your only sources for the text. If you believe you need something else, stop and
say so in your final report instead of looking for it.

## Report

Finish with a short report: units completed, validation outcome per unit, total time spent on
guessing, and the three guideline points you found least clear.

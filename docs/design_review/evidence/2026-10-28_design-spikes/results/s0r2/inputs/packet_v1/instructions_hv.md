# Instructions for annotation pass HV

You are one of several independent annotators. Annotate each unit following the guideline exactly.
Your work is compared with other annotators' later; do not try to guess what anyone else would write.

## Read, in this order

1. `guideline.md` — what to capture and the rules for roles, modality, conditions and bindings.
2. `reference.md` — entity types, every predicate with how it takes roles and conditions, qualifiers,
   value shapes, and three complete worked examples. Keep it open while you annotate.
3. `format.md` — the output format.
4. `units/<unit>.md` — one packet per unit: its standing context (`cN`) and its text (`sN`).

`schema.yaml` and `model.md` are the sources `reference.md` is generated from; open them only if the
reference does not answer a question, and say so in your notes.

## Do

For each of the 18 units in `units/` (T1, T2, T3, T4, U5, U6, U7, U8, U9, U10, U11, U12, H1, H2, H3, H4, H5, H6):

1. Annotate the unit into one model-facing `ClaimProposalBatch` and write it to `results/s0r2/pass_hv/<unit>.json`.
2. Write `results/s0r2/pass_hv/notes/<unit>.md`: every point where you had to guess, naming the guideline section
   that was unclear; anything the schema could not express beyond what you recorded as `unsupported`.
3. Validate: `cd /home/paul/corpus-structure/docs/design_review/evidence/2026-10-28_design-spikes && S0_SAMPLE=results/s0r2/sample.json UV_PROJECT_ENVIRONMENT=/home/paul/corpus-structure/build/spike-venv uv run python code/s0_check.py results/s0r2/pass_hv --rules`. It reports format and invariant issues (fix them) and guideline-rule
   warnings (fix them unless you are sure the rule does not apply, and then say why in your notes).
   Before fixing anything, copy your first version of each batch to `results/s0r2/pass_hv/first/<unit>.json`.

When all are done, write `results/s0r2/pass_hv/opened_files.txt`: every file you opened or searched, one per line.

## Do not read

Anything outside this input folder and your output folder: no design documents, no other results
folders, no other annotator's output, no code, no Git history, no directory listings outside these two
folders. If you believe you need something else, stop and say so in your final report.

## Report

Finish with a short report: units completed, validation outcome per unit, and the three guideline
points you found least clear.

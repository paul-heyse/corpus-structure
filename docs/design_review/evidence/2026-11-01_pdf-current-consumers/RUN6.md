# Run6 source and knowledge handoff

**2026-11-03 · Source preparation and actual non-Claude consumers Tested.**
Run6 is `awaiting_agent`; tasks27–31 are ready over the five intact descendant sections.
No agent task has been claimed, no Claude session has run, and no completed result is selected.
The database remains online. The owned Nemotron service has been stopped; queued knowledge work
uses the already published source and does not require another PDF/Nemotron pass.

## Exact source and evidence

- Database: `corpus_pdf_20261102`, OID16934542, dedicated18/corpus on5434.
- Project: `pdf-docling-adoption`; release `release:a13bbbd140a8586951a328a1fd261d17a2feb8a4810c3075243da0685bb3f9f7`.
- Native head: `semantic_um_section_20261103` (native99).
- Product: task6 / `integrated` / `1882a372985949584bc3c15a3df8b2c6a9f21a1b610dd2b583cea70dc44975ac`.
- Analysis views1–5: Sets, Functions, Relations, Combinatorial Structures and Normal Distribution.
- [Exact selection](selection-run6-20261103-00002.json),
  [CLI](cli-run6-20261103-attempt-00002/result.json),
  [external stdio MCP](mcp-run6-20261103-attempt-00002.json),
  [exports and detached roundtrip](exports-run6-20261103-attempt-00002/result.json).
- Reference inputs: [current manifest](references-run6-20261103-00003/manifest.json).
  Complete canonical frames stay local for validation; the separate provider source view retains
  all text, rich structure and exact citation quotes without duplicate reconciliation graphs.

The functional required union has3318 distinct nodes,563 native, zero unresolved under its
explicit source/context applicability. Historical failed receipts remain failed. These facts
establish no extraction accuracy, reference agreement, corpus fidelity or evaluator result.
Native perception was qualified retained-observation reuse, not fresh inference. Its original
unknown candidate/OCR inventory and partial/unknown health remain explicit.

## Inspect or attach without claiming work

Run from the repository root:

```bash
export CORPUS_DATABASE__URL='postgresql://corpus_sem_writer@/corpus_pdf_20261102?host=/var/run/postgresql&port=5434'
export CORPUS_RUNTIME__DEFAULT_PROJECT=pdf-docling-adoption
uv run ci status 6 --project pdf-docling-adoption --json
uv run ci mcp serve --semantic-run 6
```

The last command is the tested stdio server entry point for a client attachment. It is an
alternative to starting the automated driver below, not a second worker to run against the same
claimed task. No workstation MCP configuration was changed.

## Complete the Claude-dependent workflow

The immutable queued configuration names `claude-opus-5-5`; actual model availability,
authenticated inference and model/context capacity have not been qualified. Resume the existing
run, preserving the published source and queued task identities:

```bash
uv run ci regenerate --domain statistics --corpus docs/statistics_corpus/corpus \
  --project pdf-docling-adoption --resume-run 6 --automated --leave-unselected --json
```

For independent source-only A/B/C references, use the already prepared current bundle. A and B
run in distinct fresh tool-free sessions; C starts after both complete source/citation admission.
No extractor predictions or frozen expected answers enter their inputs. This command has not run:

```bash
uv run python docs/design_review/evidence/2026-11-01_pdf-current-consumers/author_source_references.py author \
  --run-id 6 --model claude-opus-5-5 \
  --input docs/design_review/evidence/2026-11-01_pdf-current-consumers/references-run6-20261103-00003
```

After extraction and all three reference batches finish, register them and grade using the
existing evaluator. Registration refuses incomplete/mismatched inputs:

```bash
uv run python docs/design_review/evidence/2026-11-01_pdf-current-consumers/register_source_references.py \
  --input docs/design_review/evidence/2026-11-01_pdf-current-consumers/references-run6-20261103-00003 \
  --output docs/design_review/evidence/2026-11-01_pdf-current-consumers/reference-registration-run6-00001.json

SET_ID="$(uv run python -c 'import json; from pathlib import Path; print(json.loads(Path("docs/design_review/evidence/2026-11-01_pdf-current-consumers/reference-registration-run6-00001.json").read_bytes())["set_id"])' )"
uv run ci eval run --run 6 --set-id "$SET_ID" --project pdf-docling-adoption --json
  --project pdf-docling-adoption --json
```

Use a fresh registration output name if a prior attempt exists. Reference agreement, extraction
grading and the six original-PDF challenges are distinct results. The challenge comparison retains
its documented partial/undecided source-condition boundary; no string or arbitrary accuracy gate
replaces the evaluator. Keep failed/interrupted outputs and assess those outcomes before selecting
the result. Selection remains a separate final action:

```bash
uv run ci regenerate --domain statistics --corpus docs/statistics_corpus/corpus \
  --project pdf-docling-adoption --resume-run 6 --automated --select-result --json
```

No fresh corpus intake, schema migration or whole-book publication is needed for this continuation.

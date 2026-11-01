# Current PDF consumer qualification

**2026-11-01 · Implemented helpers; actual consumer and provider journeys not_run.**
This folder owns fresh receipts for the current published source. Earlier raw outputs,
run6 references and frozen six-fact expectations remain unchanged. The remaining external,
provider and evaluator scope is authorized; execution awaits successful current source/run
preparation. The coordinator owns assembled acceptance and final adoption.

The current selector reads the newest selected source-view rows for an explicit run and
refuses a mismatch with the supplied immutable product pin. It requires exactly the five
intact descendant sections, chooses a formula/cell from their actual selected content,
and obtains occurrence identity through the published record reader. Failed recognition
raw-response custody is retained as a separate artifact challenge. The full native graph
is requested only for the explicit complete export and detached roundtrip.

`readiness.json` records only helper import/help, current CLI argument shape, frozen-input
hashes and syntax readiness. It gives no credit for database attachment, external MCP,
rendering, provider authoring, extraction, reference registration or semantic grading.
These helpers replace the stale positional export CLI and version2 MCP assumptions for
this new journey; the prior evidence files retain their original contents and outcomes.

Run from the repository root after the coordinator publishes the new book and prepares
the five-section run. `PIN.json` must contain `task_id`, `product_key`, `content_digest`.
`RUN_ID` and `CORPUS_DATABASE__URL` must name that exact source-bound run and owned database.
Every output path below must be fresh.

```bash
uv run python docs/design_review/evidence/2026-11-01_pdf-current-consumers/select_current_source.py \
  --run-id "$RUN_ID" --expected-pin PIN.json \
  --output docs/design_review/evidence/2026-11-01_pdf-current-consumers/selection.json

uv run python docs/design_review/evidence/2026-11-01_pdf-current-consumers/qualify_native_cli.py \
  --selection docs/design_review/evidence/2026-11-01_pdf-current-consumers/selection.json \
  --database "$CORPUS_DATABASE__URL" \
  --output docs/design_review/evidence/2026-11-01_pdf-current-consumers/cli-attempt-00001

uv run python docs/design_review/evidence/2026-11-01_pdf-current-consumers/qualify_native_mcp.py \
  --selection docs/design_review/evidence/2026-11-01_pdf-current-consumers/selection.json \
  --database "$CORPUS_DATABASE__URL" \
  --output docs/design_review/evidence/2026-11-01_pdf-current-consumers/mcp-attempt-00001.json

uv run python docs/design_review/evidence/2026-11-01_pdf-current-consumers/qualify_native_exports.py \
  --selection docs/design_review/evidence/2026-11-01_pdf-current-consumers/selection.json \
  --database "$CORPUS_DATABASE__URL" \
  --output docs/design_review/evidence/2026-11-01_pdf-current-consumers/exports-attempt-00001

uv run python docs/design_review/evidence/2026-11-01_pdf-current-consumers/author_source_references.py prepare \
  --run-id "$RUN_ID" \
  --selection docs/design_review/evidence/2026-11-01_pdf-current-consumers/selection.json \
  --output docs/design_review/evidence/2026-11-01_pdf-current-consumers/references-attempt-00001
```

The source-only author command below starts three fresh, tool-free provider sessions.
A and B run concurrently in a two-worker `ThreadPoolExecutor`, with separate session IDs,
temporary directories and per-pass input/output files. Neither sees the other's output.
C starts only after both complete batches pass schema and source-placement admission;
source-placement validation retains its main-thread deadline owner. C receives their full
batches and the same frozen source input.
Only the source frames, archived annotation/model contract and two original images enter
those sessions. Expected six-fact answers and extractor predictions do not. No provider
call has been run for this folder. The explicit `MODEL` is chosen by the coordinator.
The configured extractor model is currently `claude-opus-5-5`; availability and provider
authentication remain untested until the authorized actual session.

```bash
uv run python docs/design_review/evidence/2026-11-01_pdf-current-consumers/author_source_references.py author \
  --run-id "$RUN_ID" --model "$MODEL" \
  --input docs/design_review/evidence/2026-11-01_pdf-current-consumers/references-attempt-00001
```

An A/B failure, timeout or main-thread interruption cancels the sibling request and settles
owned process groups using SIGTERM, then SIGKILL if necessary, with bounded pipe draining.
The executor does not wait for the 1800-second request timeout during shutdown. Per-pass raw
and partial output remain retained; `independent-authors-interrupted.json` records each
future's status/error, any unsettled cleanup, and which batches completed admission. The
original failure is propagated, and C does not start after an A/B refusal.

The 2026-11-01 controlled subprocess receipt
`author-concurrency-controls-attempt-00003/receipt.json` covers the successful A/B-to-C
barrier, one refusal, simultaneous refusals, main-thread interruption and request timeout.
It checks distinct sessions/directories, actual image message bytes, exact prompt custody,
both complete inputs reaching C, partial-output retention and reaping of a child that ignores
SIGTERM. Its scripted children use a small control schema and local admission stub; this
establishes no actual provider, rich reference validation, database, semantic grade or
performance result. Earlier control receipts remain intact. Explicit control-module Ruff,
author-helper F checks and both helper Pyrefly checks passed (0 errors).

```bash
uv run python docs/design_review/evidence/2026-11-01_pdf-current-consumers/check_author_concurrency.py \
  --output docs/design_review/evidence/2026-11-01_pdf-current-consumers/author-concurrency-controls-attempt-00004
```

After the exact five-section extraction is completed, the evaluator-only operation below
can register retained A/B/C batches and calculate agreement. It first verifies the prepared
input hashes. Registration and agreement are distinct from grading the completed extraction;
the existing evaluator remains responsible for that result.

```bash
uv run python docs/design_review/evidence/2026-11-01_pdf-current-consumers/register_source_references.py \
  --input docs/design_review/evidence/2026-11-01_pdf-current-consumers/references-attempt-00001 \
  --output docs/design_review/evidence/2026-11-01_pdf-current-consumers/reference-registration-attempt-00001.json
```

The CLI/MCP runners retain partial receipts and refusals. The MCP runner retains the actual
rendered PNG and exact chunked failed-response artifact with SHA-256 verification. The export
runner exercises JSONL/Parquet row equality, complete Docling validation/tree roundtrip,
current version2 record export, mandatory companions, actual serialized-byte digest and
wrong-pin refusal. Any failure remains a failure; select fresh attempt output paths for a
later justified retry.

`frozen-comparison.json` preserves every expected/authored string as lexical diagnostics.
After all three sessions finish, it also assesses each frozen mathematical value against
the actual linked C claim designated by its assertion summary. The helper composes existing
`canonical_operand`/`token_form` and `semantic_alignment.equivalent`; it contains no new
mathematical kernel. Each operand uses its own macro interpretation. Canonical notation,
symbolic equivalence, differences, unsupported domains and interpretation exceptions are
reported separately. Written-value comparison does not establish binding or source meaning.

The overall outcome stays `partial`. Complete actual linked claims, qualifications and
authored-batch hashes are retained. The frozen facts supply prose meaning and conditions,
without independent typed binding/qualification trees, so their source-context/condition
assessment stays `undecided`. C's assumptions are never copied onto expected operands.
There is no string gate, provider retry, arbitrary accuracy threshold or human-step gate.
Full extraction grading separately uses the existing evaluator over complete typed batches,
qualifications and evidence; that grade does not by itself settle an independent disagreement
between the frozen original-PDF facts and pass C.

The DB/provider-free helper controls reuse the retained comparator pairs and unchanged
frozen facts. They exercise exact decimals, differing values, TeX braces/spacing, symbolic
binomial equivalence, unsupported domains, exception retention and actual-claim linkage:

```bash
uv run python docs/design_review/evidence/2026-11-01_pdf-current-consumers/check_frozen_semantics.py \
  --output docs/design_review/evidence/2026-11-01_pdf-current-consumers/frozen-semantics-controls-attempt-00004.json
```

The 2026-11-01 bounded final-helper control receipt is
`frozen-semantics-controls-attempt-00003.json` (passed: ten retained pairs, linked-claim
control and unsupported cross-challenge). Earlier receipts remain intact. New helper/control
modules passed explicit Ruff and Pyrefly checks; evidence folders are normally excluded,
so explicit checks used `--no-force-exclude` and the helper folder as an extra search path.
These controls do not establish actual source/run attachment, C authoring or extraction grade.

The test-only streaming fixture repair has a separate 2026-11-01 receipt:
`streaming-fixture-controls-attempt-00003.jsonl` (passed, one actual private PostgreSQL/IPC
test with a scripted native provider). The controlled provider supplies a real PIL raster
at the native formula stage's actual scale; production capture/release guards stay active.
The test checks exact producer callback receipts plus the segmented runtime-report field
receipt. Focused Ruff and file Pyrefly checks passed (0 type errors).

```bash
uv run python -m pytest python/corpus-structure/tests/orchestrate/test_pdf_streaming_integration.py \
  --report-log=<fresh-output.jsonl>
```

Attempt 00001 retains a console-script launch failure (`uv run pytest`: spawned test module
unavailable). Attempt 00002 used the qualification runner's `python -m pytest` launch and
retains the stale receipt-count assertion failure exposed after fixing the raster. The
original full-suite raster failure remains in qualification receipt
`20261101T184252Z-3529667`. This focused control does not claim OCR/model/source fidelity
or any of the waiting live consumer/provider journeys.

Two further test-only repairs preserve the full-suite failures and their boundaries:

- `historical-migration-controls-attempt-00002.jsonl`: passed, one authentic
  historical producer → frozen migration case. Original parent/child rows remain byte
  identical, structural edges/cell inventory backfill correctly, and retained contract,
  document, original, schema and recipe bytes are checked directly. Current context/read/
  publication explicitly refuse `unsupported_execution_abi`; no old compiler is relabelled.
  Attempt 00001 retains the diagnostic wrong-principal read refusal before the check moved
  to the existing runtime writer role.
- `selected-source-fixture-controls-attempt-00001.jsonl`: passed, one real selected-source
  export/offline formula preparation case. An actual outer chapter replaces the invalid
  body pointer in section-qualified recognition coverage. All three recognition rows,
  five selected records, ancestor/general coverage, repeated endpoints, outside-value
  requirements and wrong-project refusal remain checked. The production section guard
  remains active.

Both commands used `uv run python -m pytest <case> --report-log=<fresh-output.jsonl>`.
Focused Ruff and file Pyrefly checks passed (0 type errors). These bounded results do not
replace the coordinator's final-source affected qualification union.

I24's current-page journey is ready in `qualify_candidate_page.py`; actual execution waits
for the new integrated source/run. It selects a formula's physical page from validated native
regions, retains that page's exact published payload locators/IPC, and closes every database
borrower before detached use. Existing Arrow/DuckDB consumers check list counts, original
candidate ordinals and availability; explicit reconstruction/re-encoding is limited to that
one page. The receipt keeps the source page and OCR word address when present, released schema/
logical bindings, actual storage policy and all copy/materialization boundaries. Earlier
encode/shared-COPY/adoption/frozen-validation receipts belong to the native build owner and
can be linked without duplicating that operation or writing an alternate store.

```bash
uv run python docs/design_review/evidence/2026-11-01_pdf-current-consumers/qualify_candidate_page.py \
  --selection "$SELECTION" --database "$DATABASE" \
  --producer-receipt "$NATIVE_BUILD_RECEIPT" \
  --output docs/design_review/evidence/2026-11-01_pdf-current-consumers/candidate-page-attempt-00001
```

IPC re-encoding byte equality is diagnostic; logical identity remains separate from physical
framing/compression. Catalog TOAST policy does not measure actual compressed storage or speed.
This journey supplies a concrete operation account, without a synthetic codec ranking or
performance claim. Helper help, explicit Ruff and Pyrefly checks passed before live execution.

After source run 7 refused the legacy serializer/grid comparison before publication,
the export helper uses the settled shared native validation route:
`derive_retained_native_projection` verifies any supplied computed grids, and
`validate_native_callbacks` returns the strictly validated typed Docling document.
Explicit supplied values/presence, geometry, lists and tree/global constraints remain checked;
the helper retains the original export bytes and manifest checksums. Vendor
`export_to_dict()` equality is not used as an oracle for the field-only record profile.
Helper Pyrefly (0 errors), F checks and help passed against that returned-model API.
The failed source receipt stays intact; actual journeys require the successor integrated run.

The bounded frozen-payload efficiency slice has a separate functional receipt,
`payload-validation-efficiency-attempt-00003.jsonl`: **passed**, 40 DB-free cases,
with two PostgreSQL cases deliberately deselected for the coordinator's final-source union.
The command selected `test_pdf_payload_validation.py`, `test_pdf_ocr_contracts.py` and
`test_pdf_inline_reports.py` with `-m 'not db'`. Scoped Ruff and Pyrefly passed (0 errors).
Earlier attempt receipts remain intact.

The store now indexes companion family/kind/page selectors, folds and consumes each metadata
stream in one part traversal, and prepares validators once per encountered kind in a validation
invocation. It fuses page-local OCR and inline-report checks while retaining compact global
availability/scope/outcome state. Tests retain invalid byte/schema/logical/locator/encoding,
coverage, word/geometry and merged-region controls; they also establish that unrelated malformed
rows are not decoded, one page decodes once across multiple original candidate indices, and a
previous successful validation never authorizes subsequently changed captured data. Captured
publication policy is used instead of installed policy, with actual metadata kinds derived from
the local index. This is work removal with bounded functional evidence, not a speed measurement,
new validity cache, full-source qualification or provider credit.

After registration produces `set_id`, run the actual evaluator under its existing role:

```bash
uv run ci eval run --run "$RUN_ID" --set-id "$SET_ID" \
  --project pdf-docling-adoption --json
```

Keep the final result unselected until the coordinator assesses extraction, independent
source challenges, evaluator results and the required qualification. `ci regenerate`
defaults to starting the provider and selecting the result, so source preparation uses
both explicit switches:

```bash
uv run ci regenerate --domain statistics --corpus docs/statistics_corpus/corpus \
  --project pdf-docling-adoption --scope pdf-qualification \
  --integrated-source "$INTEGRATED_PIN" --prepare-only --leave-unselected --json

uv run ci regenerate --domain statistics --corpus docs/statistics_corpus/corpus \
  --project pdf-docling-adoption --resume-run "$RUN_ID" \
  --automated --leave-unselected --json
```

The second command runs the configured extractor and finalizes the same run. Never add a
source-pin argument when resuming; the original source binding stays immutable. Its normal
provider receipts live beneath `build/data/automated-extraction/run-$RUN_ID/` unless
`CORPUS_PATHS__DATA_DIR` supplies another explicitly retained directory.

After acceptance, the coordinator can use the same completed run for atomic release/result
selection and then configure the operator's process defaults:

```bash
uv run ci regenerate --domain statistics --corpus docs/statistics_corpus/corpus \
  --project pdf-docling-adoption --resume-run "$RUN_ID" --automated --select-result --json

export CORPUS_DATABASE__URL='postgresql://corpus_sem_writer@/corpus_pdf_20261101?host=/var/run/postgresql&port=5434'
export CORPUS_RUNTIME__DEFAULT_PROJECT=pdf-docling-adoption
uv run ci status --json
uv run ci query claims --max-rows 5 --json
```

`ci promote` remains a placeholder; there is no `ci config` setter. Persistent workstation
defaults require a separately recorded surgical edit to the existing environment owner
(such as `.envrc.local`), preserving its unrelated contents. The `export` commands above set
only the current process environment and do not establish persistent cutover.

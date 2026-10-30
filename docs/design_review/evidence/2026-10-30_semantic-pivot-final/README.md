# Final semantic-pivot regeneration and qualification

**Implemented and required-union qualified (Tested), 2026-10-30.**
SP-09/SP-10 and coordinator §13 own completion and remaining obligations. This folder retains
actual operational receipts, including failures; it does not introduce another acceptance system.

## Operational context

Fresh target: `corpus_semantic_pivot_20261030`, dedicated PostgreSQL `18/corpus` on port5434,
bootstrap head `semantic_0033`, forward upgraded to `semantic_0034`. The extension-only `cs_template` contained pg_textsearch1.5.1,
vector0.8.7 and pg_stat_statements1.12. Four independently authenticated purpose principals
passed their native runtime posture checks. Database creation's first invalid token refused;
the valid creation-only ownership token then succeeded without adopting an existing database.

Historical `corpus_semantic` remains unchanged at0030. Source at Git `ad4593f`, its own frozen
uv lock and Python3.14.10 environment in `build/sp09-historical/ad4593f` successfully read
statistics run1 and transfer run2, explained a transfer fact and exported JSONL. Commands set
`PGOPTIONS='-c default_transaction_read_only=on'` and explicitly use the reader principal.
Reconstruct the isolated source with `git archive ad4593f`; never run current writers against it.
The historical run3 is preserved; the agreed replacement is a fresh current-model source-frame run.

## Reproduction

Set `CORPUS_DATABASE__URL` explicitly to the fresh target before every current operational command.
Use `uv run --project python/corpus-structure ci regenerate` with:

- `--domain statistics --project semantic-pivot --corpus fixtures/trace/corpus --slice trace`
- `--domain toy --project semantic-pivot-transfer --corpus fixtures/toy/corpus --slice transfer`
- `--domain toy --project semantic-pivot-frame --corpus fixtures/toy/corpus --slice one_owner`

Initial commands use `--automated --leave-unselected --json`. Resume recorded identities with
`--resume-run`; do not manufacture replacement occurrences. Extraction uses actual authenticated
Claude Opus5.5 through a fresh run-bound MCP server and no reference access.

`code/read_consumers.py --project PROJECT --run RUN --out DIRECTORY` runs actual CLI claims,
explanation, JSONL and Parquet consumers. `code/evaluate_sources.py` requires explicit project,
run, fixture and label, and uses evaluator credentials for independently authored references.
Transfer fixture bytes and historical grades stay unchanged. Statistics expectations are the
source-only five-unit trace fixture; Weibull packets are not trace references.

## Qualification boundaries

The math harness uses importable spawn workers, bounded submission, public whole-pool kill on
failure/interruption and reading-only coverage. Seven focused worker controls passed, including
actual spawned vendored processing. Legacy production readers/writers moved to explicit historical
test support; independent repository/registration/loader/registry controls passed 34 tests.
These counts overlap other selections and do not establish full qualification.

Actual evaluation exposed unsupported date serialization and sampling/native custody derived
from prediction observations. Canonical Pydantic JSON serialization preserves typed values;
completed-cut immutable source frames now define reference membership even when the producer
returned no observations. Revision0034 applies the corresponding native guards and Pglast-derived
custody descriptors. `code/readmit_archives.py` reverifies and re-admits the exact unchanged
archives after this deployment; it does not activate or select anything.

Independent automated transfer grade1 and statistics grade2 persisted; the latter covers all five
trace units, including empty producer work. Allthree runs completed and selected generation2.
Their actual claims/explanation/JSONL/Parquet consumers passed. Selected default answer rows
are identical before/after0034, the table inventory is unchanged, and historical selected/run
snapshots are unchanged. Failed dated-value, source-pool and native-guard attempts stay retained.
The final broad run and hygiene have their own outcomes; focused controls do not imply them.

A bounded read-only integration review found no concrete gap in completed-cut/reused-origin frame
custody, project/split/release guards, locked exact snapshots and mandatory operation lookup.
This is implementation feedback, not a separate completion audit.

## Worker implementation choice

The supplied Python concurrency guide §§3.2–3.3,
4.1/4.4 and10 distinguish bounded submission, wait timeouts and worker termination.
The harness uses explicit spawn because the pytest parent already has threads/native state.
`wait(FIRST_COMPLETED)` consumes results without input-order blocking and retains a separate
submission deadline for each active page. `map(buffersize=...)` would bound ordered delivery,
but would not supply those per-page completion/deadline semantics. A failed page fails the full
oracle, so public whole-pool `kill_workers()` fits; per-task replacement/retry is unnecessary.
The repository runs Python3.14.10: newer3.15/3.16 features in the guide are not assumed available.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**semantic-model-pivot**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Final semantic-pivot regeneration and required-union qualification](records/pivot.final.json) | SP-10 | passed | SP-09, SP-10 | 2026-10-30 |
<!-- evidence-index:end -->

## Final qualification —2026-10-30

**Required-union Tested; no single final full zero-exit command is claimed.** Final default
collection2325: the original full invocation recorded2295 passed/24 failed. The final affected
selection passed242, covering all24 failures and six new regressions. Required unresolved nodes0.
The classifier deliberately retains failed aggregate status for the failed original invocation.
All applicable process/protocol/provider/nonfunctional obligations are resolved; empty Rust
selection establishes no Rust functional coverage. The78-page oracle passed172.1857s.

Final corrections were socket-URL reporting, generated model defaults projected into rule-engine
primitives, the pglast literal guard and missing-source-frame refusal/hash-verified backfill.
The tail covers their validate/pool/consolidate, CLI/settings, reference/source-frame/anchor,
native-product and regeneration consumers. The other valid-path results remain applicable;
source differences are exposed in raw receipts. No test/typing repetition followed lint-only edits.
Warning-aware Pyrefly passed zero errors/warnings. All remaining hygiene checks passed; typing was
reused separately. Evidence validation has zero errors/37 preserved historical warnings.

`raw/full/` retains the failed invocation and native reports; `raw/tail/` retains the passing
final selection. `raw/operational/required-union.json` uses the final collection manifest and both
receipt sets. `raw/operational/` also retains source workflows, consumers, historical snapshots,
failed grading attempts and actual retries. The record's outcome answers the applicable-union
question; it does not relabel either aggregate classifier or original command status.

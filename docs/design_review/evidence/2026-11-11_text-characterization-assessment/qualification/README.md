# Whole-book source and execution accounting

This dated account distinguishes retained source presence, exact source selection, execution coverage and independently judged semantic correctness. It neither reads reference answers nor runs models. Source reference set 40 and its selection remain immutable in the sibling `panel/` folder.

## Source account — passed, 2026-11-11

```sh
uv run python docs/design_review/evidence/2026-11-11_text-characterization-assessment/qualification/account_book.py source
uv run python docs/design_review/evidence/2026-11-11_text-characterization-assessment/qualification/inspect_source_ownership.py
```

The protected published record reader selected task 1627, product `integrated`, digest `35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb`. Source capture 496/cut 614 contains 316 distinct direct SourceViews of that exact original, project `nce-grinstead-snell-full-book`. All 518 native physical-page map entries are present, with exact keys 1–518. All captured views contain text; none is zero-text or whitespace-only.

[source-coverage.json](source-coverage.json) retains the exact original publication/release/recipe/schema/source digests, all 316 projection pins, per-view source health, and all 518 page dispositions. Its initial dispositions deliberately count **own recorded regions only**. [source-page-ownership.json](source-page-ownership.json) then accounts for exact original parent links separately:

| Native item provenance | Count |
|---|---:|
| Own recorded page region | 8,589 |
| Exact native ancestor has a recorded region | 18,957 |
| No own or ancestor region; structural nodes with zero text | 687 |
| Total native projected items | 28,233 |

The initially textless body containers on physical pages 4 and 82 contain selected inline text through their native children: 22 pieces/637 characters and 18 pieces/1,442 characters respectively. Page 119 similarly has six selected pieces/192 characters through native ownership. Pages 412 and 506 have furniture only in recorded regions. Thus 516 pages have selected real text under either own or exact ancestor region provenance; this does not assert that every original page contains recoverable language. An inherited multi-page region set remains a set and supplies no child bounding box or unique child-page assignment.

The remaining unmapped nodes are 315 sections, 358 lists, 12 key-value containers and two unspecified structural nodes. None has own nonempty text or projected real characters. The sole body item absent from focal membership is the zero-text root `#/body`. All 21,653 items with nonempty body `text` have focal capture membership. This protected inventory inspection found no omitted nonempty body item requiring an extra root-residual capture. Table/picture cell projections use their own retained fields, so their character totals are not compared to a nonexistent container `text` field. Two formulas on physical pages 416/418 explicitly retain `source_field=orig` instead of truncated native `text`; this is not evidence that the original formula was completely recognized.

The inherited health is retained verbatim in the JSON account. In particular:

- Conversion reports `success`; whole-document source scope, `display_coverage=partial`, `inline_coverage=unknown`, `cell_coverage=unknown`.
- Mapping/execution report `partial` and `source_fidelity=conflict`.
- The original validation report says: “Native document/tree validated; private companion replay does not establish frozen-union closure or source completeness”.

The conflict is an observed inherited source-health category. The private replay statement leaves frozen-union assurance and source completeness unresolved; it is not an independently established diagnosis of text corruption. Page-map presence, source membership and model execution cannot discharge these limits.

`raw/native-item-coverage.jsonl` stores narrow original item metadata, focal membership and selected piece counts. `raw/native-page-ownership.jsonl` adds the exact parent chain and separate own/ancestor pages. `raw/previously-textless-page-source-items.json` retains only the bounded original-node inspection for the five initially textless pages. `raw/source-field-selection.json` records the actual selected field counts (21,651 `text`, two `orig`, 2,520 table-cell, 2,813 chart-cell and 21 chart-title pieces), plus exact original `orig` correspondence for the two formula substitutions. Raw files use the repository's existing LFS rule.

## Primary family account — not_run

The first primary attempt failed construction run 504; the coordinator owns that failure and the whitespace-participant repair. Publication-boundary repairs and qualification precede the coordinator's resumed network-enabled whole-book execution on 2026-11-11. No final whole-book combined view has been supplied to this account yet; the active execution log is `build/tc11-book-execution.log`. Failed/interrupted regional attempts are not a substitute for the exact final view.

```sh
uv run python docs/design_review/evidence/2026-11-11_text-characterization-assessment/qualification/account_book.py primary
```

This command refuses to select a regional or latest output in place of `../book-result.json`. When that final result exists, it authenticates its exact combined view and every active sealed layer manifest, checks the exact 316-view membership and projection/recipe pins, and obtains the selected full-characterization family inventory from the view's archived release.

It writes every original eligible/examined/unexamined selector and outcome once in `raw/family-scopes.jsonl`. `raw/source-view-family-account.jsonl` enumerates every captured-view × required-family pair, including `not_recorded` and incomplete outcomes. It also records observed optional families separately from required families, and distinguishes a declared layer with no attributable selectors from a complete examined scope. Attribution requires a unique exact projection digest within the declared layer scope; it does not infer ownership from equal text or fill missing selector coordinates. The summary retains actual runs, task statuses, active versus dependency-only layers, final result digest and demand readiness. These are execution and coverage facts, not semantic grades, source-completeness or adoption claims.

## Actual combined-view consumers — not_run

`verify_consumers.py` is gated on the same exact final `book-result.json`. It prepares bounded requests for summary, exact coverage pagination, spaCy annotations and formal.math annotations, plus exact predicate-term and native-container membership requests when those objects exist in the frozen output panel. It never invokes the primary producers or reads reference answers/grades.

```sh
uv run python docs/design_review/evidence/2026-11-11_text-characterization-assessment/qualification/verify_consumers.py prepare
uv run python docs/design_review/evidence/2026-11-11_text-characterization-assessment/qualification/verify_consumers.py live
```

`live` calls the actual `inspect_characterization` owner, executes the installed `ci source enriched` command for the same immutable request, and invokes `inspect_enriched_document` through the real `build_semantic_server` registration using FastMCP's client and an ordinary project-bound reader. It compares the entire typed response, including exact pins, coverage totals/truncation/continuations, source extents/items, membership scope, choices and private standing. Requests are two-item pages with an explicit 1 MiB response bound. It retains each bounded native/CLI/MCP response and command receipt in `raw/`, reports each route separately, and returns failure if any route or equality check fails. A bounded page is not reported as the complete node population; full required-family accounting remains separate.

Detached delivery uses the existing managed export owner, without recreating closure or verification logic:

```sh
uv run ci review export docs/design_review/evidence/2026-11-11_text-characterization-assessment/qualification/review-selection.json --exact-closure --json
uv run ci review inspect --result RESULT_ID --json
```

`review-selection.json` names the exact final view/run and all 316 source rows. The default 128 MiB total package bound comes from the owning `CharacterizationReviewSelection` contract. If the actual whole-book closure exceeds it, retain that refusal and ask the coordinator to choose the explicit operational byte bound; `prepare --export-max-bytes BYTES` records that choice without changing the product or truncating its closure. No size or throughput estimate is substituted for the actual result.

For an intentionally detached delivery, provide its destination to the same owner and retain its managed receipt. Use that exact resulting directory for offline verification and replay:

```sh
uv run ci review verify BUNDLE_PATH --json
uv run python docs/design_review/evidence/2026-11-11_text-characterization-assessment/qualification/verify_consumers.py replay --bundle BUNDLE_PATH --request-name summary --request-name native-annotations
uv run ci review inspect BUNDLE_PATH --request docs/design_review/evidence/2026-11-11_text-characterization-assessment/qualification/REQUEST.json --json
```

The last optional CLI request is one exact request object from `consumer-requests.json`, delivered as a deliberate request artifact. The script uses the existing `verify_characterization_review` and `inspect_characterization_review` owners, which authenticate the entire archived view, exact layer/dependency closure, source products/companions and contracts before replay. It compares requested detached responses with the actual live native responses. A package's `original_source_completeness=complete_native_document_and_companions` means those retained native objects were captured; it does not strengthen inherited OCR/inline/display health or resolve frozen-union source assurance. No model or database inference is needed for offline replay.

## Operating account while the book runs

```sh
uv run python docs/design_review/evidence/2026-11-11_text-characterization-assessment/qualification/observe_progress.py
```

This read-only command **passed on 2026-11-11**. [operating-account.json](operating-account.json) binds existing task/run/source metadata to the exact created run IDs in the coordinator's resumed invocation log; `raw/operating-task-source-scopes.json` retains stage statuses, stored start/finish timestamps and original source cardinalities. It separates observed, locally composed and not-yet-composed SourceViews and keeps failed tasks explicit. It adds no runtime instrumentation and never substitutes regional work for the exact final combined pin or a required-family examination account. The file's acquisition timestamp states its observation boundary; later progress does not retroactively change that snapshot.

The invocation beginning at run 513 is preserved separately in [interrupted-invocation-513.json](interrupted-invocation-513.json), with its raw task/source metadata and execution log. At the settled 2026-11-11 21:59:37 UTC observation it contained runs 513–523, source views 469/470, one completed local compose (469), no active or failed tasks, and cancelled context-evaluation task in run 523. The coordinator intentionally sent SIGINT before correcting repeated dependency decode/hash and per-production term scans. The resulting `KeyboardInterrupt` is an intentional operational interruption, not provider failure. Final whole-book qualification and output-first selection remain `not_run` for this invocation; no regional pin replaces them.

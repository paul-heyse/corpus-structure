# Source-product implementation qualification

**Scoped Tested · 2026-10-30.** Product commits `799d894`, `3bc09bc` and `334da0f`
implement PP-00–PP-04 under ADR-0036. This account qualifies the selected source-product
capability, not the entire parsing series, every HTML input, mathematical interpretation,
operational adoption or performance. The earlier nine-case investigation remains a separate
partial feasibility record; its limitations are not silently promoted to implementation results.

## Delivered behavior and selected mechanisms

- Trusted LinkML effective slots and discriminated Pydantic node variants feed the existing
  JSON Schema/runtime and native contract routes. Execution compiler 10 admits actual
  decomposition, HTML recognition, projection and publication/read operations. Future text,
  mathematical interpretation and assessment operations are explicit unbound declarations;
  requiring one refuses before effects. They are not claimed as implemented algorithms.
- html5lib 1.1 tokenization and HTML5 tree construction remain upstream through lxml 6.1.3.
  Per-operation tokenizer/stream/tree-builder hooks preserve lexical distinctions, pre-dedup
  attributes, native final structure and text/tail contribution custody. The table-text buffer
  wrapper retains original contributing token IDs. Private hooks are version-bound upgrade
  responsibilities; no second HTML parser or global monkeypatch is used.
- Original bytes, native decoded code points and canonical code points have separate complete
  partitions. Decoder contribution groups retain BOM, replacement, newline and zero-output
  stateful input. The actual native selected codec is used; a same-length decoded-content
  disagreement refuses. Canonical normalization/serialization emit mappings at the operation,
  including exclusions and synthetic separators/markers. NFC and replacement are transformed,
  never relabelled exact byte copies. Binary-safe decoded NUL retains its UTF-8 byte value.
- Complete provenance means the declared `canonical_output` universe is rooted through admitted
  mappings to original bytes or admitted synthetic production. It does not claim a bijection,
  an exact origin for every repaired DOM node, or that all raw input appears in canonical output.
  Unknown origin stays partial. Canonical self-copy cannot establish original provenance.
- PostgreSQL retains content-addressed original `bytea` during document registration before
  parsing. Fixed Core metadata, normalized occurrence/endpoint tables and restricted bulk
  publication preserve build-specific products separately from shared canonical renditions.
  Existing unit completion publishes atomically; direct publication locks run before task.
  Prepared runtime contracts come from the exact archived execution input bundle and are
  reused at the reader/operation boundary, without per-token database policy lookups.
- Typed bounded component, relationship and mapping queries support multi-hop origin tracing.
  Limits/cycles/partial coverage are explicit. Reader reuse follows the producing task;
  competing builds require an explicit pin, and matching corruption refuses reconstruction.
  Native 0042 extends immutable 0041. The derivation CLI emits the current forward delta while
  retaining full changed-model/Core-view products in its review output.

## Functional receipts and failure accounting

[Raw receipts](raw/implementation/) retain stdout and native pytest report logs unchanged.
[Selections](commands.txt) reconstruct reproducible pytest selections from those report node IDs;
parameterized node IDs are preserved. `uv run pytest` is the command route for the rows below.
There is no relabelled aggregate pass for an invocation that failed.

| Receipt | Outcome | Scope and applicability |
|---|---|---|
| `affected` | **failed**: 451 passed, three failed | Entire ingest test directory and 24 affected semantic modules, 454 cases. Frozen-product generation used an obsolete family, physical comparison found two missing indexes, and a historical rejection assertion still expected compiler 9. |
| `affected-repairs` | **failed**: nine passed, one failed | Ten affected/CLI cases. Corrected generator/CLI, emitted the missing indexes and updated the diagnostic. Remaining frozen-generation failure exposed nondeterministic CheckConstraint order. |
| `deterministic-authoring` | **passed**: one case | Sorting constraints by name made frozen forward rendering deterministic. |
| `publication-final` | **failed**: eight passed, one failed | Final native SQL/descriptor: restricted writes, typed HTML/NUL products, actual M01 journeys, physical comparison, exact generation and preservation migration passed. The concurrent test's observer used unavailable cross-role activity details and timed out. |
| `lock-order` | **passed**: one case | Observer now uses supported `pg_blocking_pids()` and prepares archived context before blocking. Actual concurrent publication waits on the run without holding the task. Production SQL was unchanged after the eight preceding passes. |
| `assembled-native` | **passed**: four cases | Actual M01 with math/profile outputs, reused source reads, separate builds sharing one rendition, ambiguous selection, and 0040→0042 preservation including historical fallback. |
| `corpus-products` | **failed**: one case | New test called a removed preparation helper; this was a test integration error. |
| `corpus-products-current` | **passed**: one corpus case | All 78 current pages satisfy source-product contracts, complete raw/decoded/canonical partitions and rooted canonical-output provenance. This is neither a benchmark nor universal HTML qualification. |
| `reader-port` | **passed**: one case | Prompt identity consumer after the Reader protocol extension; unsupported fake-reader ports refuse explicitly. |

Earlier [foundation receipts](raw/foundation/) retain the initial product/custody/source-read
slice. `pp01-worker-native-history.jsonl` is an explicitly labelled worker summary of earlier
failed/repaired invocations, **not raw stdout**. The final root native receipts supersede its
pre-integration authoring hashes. An independently failing NBSP extent example was repaired to
use HTML5 ASCII whitespace; the regression passes within the affected source tests. Existing
native-versus-instrumented trees, independent literal category/extent expectations, invalid
products and all-page canonical invariants provide complementary evidence; validator agreement
alone is not a semantic oracle.

## Documentation and maintenance

**passed:** `just turn-end`, `uv run ruff format --check`, `uv run ruff check --output-format
concise` and `just docs-check`. The initial docs-check **failed** on the new execution-section
fragment; an explicit stable anchor fixes it and the complete publication then **passed**. Both
logs are retained. No functional/type rerun was triggered by formatting-only maintenance.

## Diagnostics, integrity and remaining boundaries

**passed:** `just types` (`types-publication.log`), warning-inclusive Pyrefly with zero reported
errors/warnings and no suppressions added. Earlier failed FakeReader typing remains in
`types.log`; the asserting refusal ports repair its actual contract. Existing library deprecation
warnings in pytest and LinkML ambiguous-attribute generation diagnostics remain visible in raw
logs; they are not Pyrefly warnings. **passed:** `just ready` after an environment-shaped disk
failure. Formatting-only final maintenance does not invalidate functional or type results.

Final native authoring receipt `final-publication-authoring.log` identifies:

- `semantic_0042_parsing.sql`: `32d70ce39fa7ac90877b90746dc3b0c4e779e35d27da99dd8b2e5ec5aba7eebb`.
- `semantic_0042_admission.sql`: `72a3ee389e9f6a8b0f9d07f6637229174b5fa917ba83c641b93d8a11c272ea42`.
- Admission descriptor: `7b99baa18cac9695732d77ea8d14f98ede8912271efb045f48d95a783903dcf0`.

The 451 unaffected broader passes remain applicable to their covered behavior; the generator,
physical/index, compiler-diagnostic, CLI and final publication changes have the affected native
reruns above. No broader or whole-series qualification is inferred. `just test-all`, Rust
functional qualification, LLM/provider grading and operational database adoption are **not_run**
for this source-product scope. Test-owned native databases were used; existing operational
`corpus_efficiency_20261030`, historical answers and grades were not advanced or rewritten.

PP-05–PP-07 and PP-10 remain future packages. PP-08/PP-09 have only the source-ingest lifetime,
atomic completion/replay and pinned-reader prerequisite slice here; broader cancellation,
demand-driven math, extraction views and adopted-consumer acceptance remain with those owners.
No audit premises, grading policy, testing architecture or quantitative performance claims changed.

# PDF13/PDF15 integration worker receipt

**Tested — 2026-10-31 (America/New_York); archived 2026-11-01T02:14Z.**
Final implementation baseline: worker commit `017ecaf`, following the runtime and consumer
contributions through `4251939`. The coordinator owns assembled qualification and book adoption.
These checks ran in `/home/paul/corpus-structure-pdf-integration` using the coordinator's shared
Python environment and this checkout's source through `PYTHONPATH`.

## Bounded functional result

**passed:** 68 tests, including fresh PostgreSQL deployment through `semantic_0058`, protected
publication, immutable replay, retained older native products, scoped companion reads, 1,589-page
coverage manifests, exact-custody 64 KiB artifact reads, current source views/search, and qualified
PDF read ABI acceptance/refusal. Fixtures independently exercise table grids/spans, rich cells,
chart cells/panels/captions, inline math, selected order/section containment, transformed geometry,
retained alternatives, raw failures and lazy symbolic comparison.

```sh
env -u BASH_ENV PYTHONPATH=python/corpus-structure/src .venv/bin/python -m pytest \
  python/corpus-structure/tests/semantic/test_pdf_integrated.py \
  python/corpus-structure/tests/semantic/test_pdf_reconciliation.py \
  python/corpus-structure/tests/semantic/test_native_adapter_contracts.py \
  python/corpus-structure/tests/semantic/test_source_views.py \
  python/corpus-structure/tests/semantic/test_integrated_consumers.py \
  python/corpus-structure/tests/semantic/test_source_search.py \
  -q --disable-warnings --tb=short
```

[Raw passing output](raw/functional-0058.log). The inherited `BASH_ENV` hook rejected the delegated
worktree's unapproved direnv activation inside test subprocesses; the command disables that hook
for this process. The root environment is reused without synchronization or installation.

An earlier expanded run failed the new rich-document publication fixture because its synthetic
transform omitted required normalization/source-space/target-space fields. The fixture was
corrected to supply the actual typed contract. [Failed output](raw/fixture-transform-failure.log)
remains separate from the passing final run.

**passed:** scoped Pyrefly checks for the mapper, companion reader and new mapper controls:

```sh
PYTHONPATH=python/corpus-structure/src .venv/bin/python -m pyrefly check \
  python/corpus-structure/src/corpus_structure/ingest/pdf_reconciliation.py \
  python/corpus-structure/src/corpus_structure/semantic/pdf_storage.py \
  python/corpus-structure/tests/semantic/test_pdf_reconciliation.py
```

[Raw typing output](raw/targeted-types.log). Repository formatting, global diagnostics and full
qualification belong to the coordinator's final source/context.

## Actual retained provider responses

**passed:** all eight actual retained responses for physical pages 85, 596 and 614 map and validate
under the final mapper: five content observations and three evidence-only B layout observations.
The responses are the runtime worker's original A/B/C request records beneath
`../runtime/pages/e98fe358e74d8905b3491654c8db2354c859dcbbcc4cfe096186f25aa4bb63f9/1ae6edde387a15354e3ffc75085ef514272cf7e9bcdaa6f891d31e69b350efd1/`,
each at `page-NNNNN/attempt-00001/observation-NNN.json` and its exact `request-NNN.raw.txt`.
Mapping verifies the raw response digest, preserves raw blocks, applies the declared transform,
and runs native document/tree validation. [Raw result inventory](raw/retained-provider-mapping.log).
This receipt establishes replayed mapping of actual observations; the coordinator owns live
provider, whole-book and knowledge-pipeline acceptance.

## Integration boundaries

The final content graph remains a Docling document with mandatory typed companion relations.
Generated cells/formulas use inherited coarse parent witnesses. Distinct source readings and
selection decisions remain available through selected occurrences and paged manifests. PDF read
ABI 1 uses the exact archived contract, supported operation binding/body version and native
schema rather than helper source-file byte identity.

Migration `0057` remains byte-identical to the deployed `5fb11cd` baseline. The later function,
view and admission update is the forward `0058` migration. Historical `0047`–`0056` files remain
unchanged. The generalized HTML representation/product runtime and its producer-specific tests
were retired; current text/TeX/math kernels and native PDF reuse remain.

## Bulk removal correction

**Tested — 2026-10-31 (America/New_York); archived 2026-11-01T03:04Z.**
Worker baseline `62eddf0` replaces the selected graph's single public deletion call. Actual book
retry 3 repeatedly sampled inside Docling 2.105.0's `ref in refs` linear membership scan after
six minutes; reference renumbering also sums all deleted indices for each surviving reference.
Context7 and the exact pinned public API exposed no arbitrary-node filter alternative:
`filter` supports page selection and rebuilds objects, while range deletion delegates to the
same deletion implementation. The coordinator authorized a typed bulk adapter for this workload.

The adapter expands containment subtrees once, builds surviving per-collection ranks, and updates
public typed `RefItem` edges and `NodeItem.self_ref` fields. It preserves surviving object identities,
pages, text and geometry. Dead list references disappear; the public optional graph-cell reference
becomes `None`. Required scalar references into removed subtrees refuse before mutation. Public
document and tree validation run afterward. The helper is an archived implementation input; this
correction changes no schema, read ABI or frozen migration.

**passed:** 32 focused functional controls, including five exact-output comparisons with public
deletion, independent expected references and identity checks, rich cells, captions, footnotes,
lists, repeated/shared references, optional scalar references, pages and rotated tables. Independent
controls also require references to removed descendants to disappear: upstream's list cleanup uses
only the requested roots and can accidentally rebind such references to another surviving item.
The combined run includes the existing mapped-rich-document PostgreSQL publication control.

```sh
env -u BASH_ENV PYTHONPATH=python/corpus-structure/src .venv/bin/python -m pytest \
  python/corpus-structure/tests/semantic/test_pdf_bulk_remove.py \
  python/corpus-structure/tests/semantic/test_pdf_reconciliation.py \
  -o addopts='' -q --disable-warnings --tb=short
```

[Functional output](raw/bulk-removal-controls.log), [scoped Pyrefly output](raw/bulk-removal-types.log)
and [new-file Ruff output](raw/bulk-removal-lint.log) all passed. These bounded results do not
establish whole-book publication, runtime improvement measurements or assembled qualification.

## Frozen forward-product reproduction

**Tested — 2026-10-31 (America/New_York); archived 2026-11-01T03:10Z.**
Worker baseline `3a1ad58` corrects native generator authoring inputs. The coordinator's broad run
found that current source changes altered only the deployed 0058 admission descriptor's
`model_id` and release `inputs` fingerprints; generated function SQL and all enforcement fields
still matched. The old generator implicitly substituted today's Python release provenance for
the immutable revision's original authoring event.

Head reproduction now explicitly reads those two authoring fields from the recorded 0058
admission witness. The predecessor 0057 witness is never substituted. SQL bodies, privileges,
tables, triggers, physical checks, ABIs, effects and every other enforcement field still derive
from current owners. New candidate derivation through `ci schema derive` explicitly acquires
current release provenance instead. Deployed 0057 and 0058 files and the runtime descriptor
hash remain unchanged; no new deployment guard or migration is needed.

**passed:** all 15 native-closure controls, including the unchanged exact frozen-byte oracle,
database admission and drift refusals, and new counterfactual controls. A changed current SQL
function or physical constraint changes generated products; an unsupported current effect
refuses generation. A current candidate's full descriptor equals the recorded descriptor with
its two authoring fields explicitly replaced by current values. No fields are dropped from
the frozen-byte comparison. **passed:** four actual schema-CLI controls, including the current
reconciliation artifact name and explicit current candidate provenance.

```sh
env -u BASH_ENV PYTHONPATH=python/corpus-structure/src .venv/bin/python -m pytest \
  python/corpus-structure/tests/semantic/test_native_closure.py \
  -o addopts='' -q --disable-warnings --tb=short
env -u BASH_ENV PYTHONPATH=python/corpus-structure/src .venv/bin/python -m pytest \
  python/corpus-structure/tests/semantic/test_schema_product_cli.py \
  -o addopts='' -q --disable-warnings --tb=short
```

[Closure output](raw/forward-provenance-controls.log), [CLI output](raw/forward-provenance-cli.log)
and [scoped Pyrefly output](raw/forward-provenance-types.log) all passed. The coordinator owns
final-source formatting, assembled qualification, migration receipts and whole-book publication.

## Native identity-exclusion custody — forward 0059

**Tested — 2026-10-31 (America/New_York); archived 2026-11-01T03:31Z.**
Worker baseline `a417be0`, with the consumer's native fixture migration `25b18fa` and coordinator's
native custody/coverage correction `d13c0d2`, admits located native identity-exclusion evidence.
Two former checks joined only `kb.span`, omitting legitimate native SourceView evidence: primary
custody and exact citation multiplicity. Both now obtain projected coordinates through the existing
canonical `ops.native_source_address` authority and preserve observation, role, locator and count
matching. No synthetic spans or new address meanings are introduced.

The forward `semantic_0059` migration redeploys current PDF functions/views and the corrected
exclusion function with an exact trusted admission descriptor. Frozen 0057 and 0058 bytes remain
unchanged. The coordinator owns deployment; the worker deployed only isolated pytest databases.

**passed:** 39 controls covering actual primary/supporting native exclusion finalization, independently
expected quote coordinates and source pins with no `kb.span` rows, known-input reuse, restricted
tampering refusals, snapshot/columnar reads, native deployment/drift checks, frozen head reproduction,
function/effect/constraint counterfactuals and actual candidate CLI generation. The negative controls
preserve missing-primary, missing-supporting, extra-citation, forged-locator and endpoint/policy attacks.

```sh
env -u BASH_ENV PYTHONPATH=python/corpus-structure/src .venv/bin/python -m pytest \
  python/corpus-structure/tests/semantic/test_native_identity_custody.py \
  python/corpus-structure/tests/semantic/test_identity_exclusions.py \
  python/corpus-structure/tests/semantic/test_identity_exclusions_native.py \
  python/corpus-structure/tests/semantic/test_identity_exclusion_reads.py \
  python/corpus-structure/tests/semantic/test_native_closure.py \
  python/corpus-structure/tests/semantic/test_schema_product_cli.py \
  -o addopts='' -q --disable-warnings --tb=short
```

[Final passing output](raw/native-exclusions-0059-confirmed.log) and
[scoped Pyrefly output](raw/native-exclusions-0059-types.log). The earlier
[19-passed/1-failed output](raw/native-exclusions-0059-controls.log) remains intact: native SQL
publication and tamper controls passed, but that checkout's old `SourceCustody.rendition_id: int`
rejected native `None` during reading. The coordinator's existing `d13c0d2` correction supplied
the current native custody DTO/read route before the final combined pass. No SQL guarantee was
relaxed to resolve that reader mismatch. Whole-book integrated publication and full qualification
remain coordinator-owned and are not established by these bounded controls.

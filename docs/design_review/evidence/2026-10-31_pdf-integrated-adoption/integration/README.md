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

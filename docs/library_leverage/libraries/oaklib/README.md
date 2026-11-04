# oaklib and linkml-term-validator

**Realization assessed:** oaklib 0.7.4 and linkml-term-validator 0.4.5, the latest on PyPI as of
2026-10-29.

**Research:** done on 2026-10-29 by the R3 cluster, at low priority because the pivot gives these
libraries little weight.
- Overviews read end to end: [oaklib](../../../libraries/data_model/oaklib.md) and
  [linkml_extension_libraries](../../../libraries/data_model/linkml_extension_libraries.md) §2.2.
- Follow-ups: the installed source and the PyPI listing.

These two related libraries share one account; each type keeps its own namespaced handle.

## Reusable opportunity types

<a id="linkml-term-validator-enum-expansion"></a>

### `linkml-term-validator/enum-expansion`

**Expansion order in 0.4.5:**
1. `reachable_from`
2. `matches`
3. `concepts`
4. `include`
5. `minus`
6. `inherits`
7. static permissible values

Because `minus` runs before `inherits` and the static values, it never removes inherited or static
members (`plugins/base.py`). Membership checks through `is_value_in_enum` do not consult `minus` at
all.

**Adapters.** The plugin resolves them through `oak_utils.get_adapter` from configured selectors. The
default selector is `sqlite:obo:`, which downloads. Offline mode builds no adapter. The
`_adapter_cache` is private.

<a id="oaklib-in-memory-pronto-adapter"></a>

### `oaklib/in-memory-pronto-adapter`

**Mechanism.** `ProntoImplementation(wrapped_ontology=pronto.Ontology(BytesIO(data), import_depth=0))`
builds an adapter from bytes at the constructor level, with no temporary file.

**Condition.** Pronto follows imports by default (`import_depth=-1`); set `import_depth=0` to stop
this ([LOP-X006](../../assessment-patterns.md#lop-x006)).

## Applicability at source `d739b88`

<a id="applicability-cbo-024"></a>

### CBO-024 — enum composition order and ontology reparsing: **workaround still needed (light)**

Opportunity: [CBO-024](../../codebase/release-preparation.md#cbo-024).

- **Enum composition.** 0.4.5 is still the latest release. It still applies `minus` before `inherits`
  and the static values, and its membership check ignores `minus`. The project's hand composition
  therefore remains necessary. The LOP-11 trigger to revisit is a new release.
- **Ontology loading.** OAK can build adapters from bytes held in memory. Handing those adapters to
  the term-validator plugin, however, requires its private `_adapter_cache`.

## Coverage limits

No production model uses dynamic enums, so these findings serve only the capability that tests
exercise.

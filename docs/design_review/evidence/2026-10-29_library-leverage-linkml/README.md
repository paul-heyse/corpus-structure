# LinkML model-stack semantics for library applicability (2026-10-29)

Library-research evidence for the first `leverage-library-assessment` pass, cluster R3
(LinkML model stack). These probes settle semantic questions that documentation and installed
source left open or that are consequential enough to observe directly. They are evidence, not
authority. The library collection under `docs/library_leverage/libraries/` owns the conclusions.

## Questions

- **P1.** Can `SchemaView(importmap=…)` with in-memory schema dictionaries compose a release
  without filesystem or network access? What happens on a missing import, a `linkml:` import or a
  duplicate element? Are source-relative URIs preserved after `merge_imports()`?
- **P2.** Does `linkml_runtime.processing.referencevalidator.ReferenceValidator` report a dangling
  non-inlined class reference or a duplicate identifier?
- **P3.** How do `type_ancestors`, `induced_type`, `induced_slot` and
  `materialize_derived_schema()` combine patterns and numeric bounds along a type chain? Is this
  conjunctive?
- **P4.** Does induced-slot resolution, or handing a `SchemaDefinition` to a generator, mutate the
  asserted schema?
- **P5.** Does linkml-runtime 1.12.1 load structured (list, mapping, nested) annotation values?
- **P6.** Does a `curies.Converter` built from a prefix map match release-scoped expansion,
  longest-namespace compaction and refusal of unknown prefixes?

## Environment

- Python 3.14.10 through `uv run --no-sync python`, repository root, tree at
  `d739b883e322adef7a3202e2896766ff71bcac5d`.
- linkml 1.12.1, linkml-runtime 1.12.1, curies 0.15.5, pyoxigraph 0.5.13 (as printed by the probe).
- No database, network service or schema file is used. P1 replaces
  `linkml_runtime.utils.schemaview.load_schema_wrap` with a spy that records and refuses any
  filesystem or network load.

## Command

```
uv run --no-sync python docs/design_review/evidence/2026-10-29_library-leverage-linkml/probe.py \
  > docs/design_review/evidence/2026-10-29_library-leverage-linkml/probe-output.txt 2>&1
```

Outcome: `passed` (exit 0, 2026-10-29). Raw output: [probe-output.txt](probe-output.txt).

## Observations

- **P1.**
  - Importmap dictionaries composed the closure `['mod_a', 'https://example.org/b', 'root']`
    with no loader fallback, and the dictionaries were left unmodified.
  - A missing import fell back to `load_schema_wrap('not_supplied.yaml')`, which is filesystem
    or network resolution, rather than refusing.
  - With an empty importmap, `linkml:types` resolved to the installed metamodel file.
  - A class duplicated across modules was not refused. The unmerged view returned the *last*
    module's definition; `merge_imports()` kept the *first*.
  - The unmerged view expanded `Other` with its own module's prefix (`https://example.org/b/Other`).
    After merging and opening a new view, the same class expanded with the root's prefix
    (`https://example.org/root/Other`).
- **P2.** `ReferenceValidator.validate` returned no results for a dangling reference
  (`ref:missing`) or a duplicate identifier (`ref:a` twice).
- **P3.**
  - `type_ancestors` returned the ordered `typeof` chain, ending at the declared primitive.
  - `induced_type` applies most-specific-wins, not conjunction:
    - `ShortCode` kept only its own pattern;
    - `Looser` got `minimum_value = -5`, overriding its ancestor's 0.
  - `induced_slot` combines slot-level bounds by min/max, but does not fold in the range type's
    bounds.
  - `materialize_derived_schema()`:
    - inherited patterns only where the child type has none;
    - did not inherit numeric bounds between types;
    - overwrote a slot's own pattern with the range type's pattern (`^S` became `^.{1,3}$`).
  - `type_ancestors` raised `ValueError: No such type: "string"` when the primitive type was not
    declared in the schema.
- **P4.**
  - `class_induced_slots('A')` populated the asserted slot's `domain_of` with `['A', 'B']`.
  - Constructing and serializing a `JsonSchemaGenerator` changed the `SchemaDefinition` it was
    given: `domain_of` was populated and `metamodel_version` set.
- **P5.**
  - A list value loads as a Python `list`.
  - A mapping placed under an explicit `value:` key loads as a `JsonObj`.
  - A bare mapping value is rejected (`Annotation.__init__() got an unexpected keyword argument`).
  - Nested `annotations` on an annotation load.
  - `json_dumper` round-trips all three accepted forms.
- **P6.**
  - **Expansion:** strict `expand` matched for known prefixes, an empty local part and refusal of
    unknown prefixes. It differs on inputs without a delimiter (`NoCURIEDelimiterError` rather
    than refusal under the same error type), and it refuses `http(s)://` and `urn:` strings that
    the release contract passes through.
  - **Compaction:** `compress(passthrough=True)` matched longest-namespace compaction, including
    `prefix:` for an exact namespace and passthrough of unknown IRIs.
  - **Duplicate URI prefixes:** a strict converter raises `DuplicateURIPrefixes`. A non-strict
    converter chose `d2`, the same answer as the release contract's `max()` tie-break in this
    case; the general tie-break rule was not established.

## Limits

- **P3.** The "materialize left source unchanged" observation was taken after earlier
  `induced_slot` calls had already populated `domain_of`. It shows only that materialization
  added no further change.
- **P1.** URI relabeling was observed through `get_uri` on a fresh view over the merged schema.
  Generator output was not inspected.
- **P5.** Loading was observed. Whether a consumer's annotation reader preserves structure is a
  consumer question; readers that stringify values lose it.
- **P6.** The release-contract functions are transcriptions of the inspected expansion and
  compaction code, not calls into the product. Unicode, case-insensitive matching and
  prefix-synonym records were not exercised.
- No timing or capacity claim is made.

## Files

- `README.md` (this file)
- `probe.py`
- `probe-output.txt`

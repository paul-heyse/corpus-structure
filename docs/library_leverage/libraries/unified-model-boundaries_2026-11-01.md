# Unified-model boundaries: focused applicability

**Interface-checked and source-inspected, 2026-11-01; applications Proposed.** Source
`1cb8e620`, diagnostic publication `cc2998d9` / UM-20261101-r2; core 3.3, heuristics 1.0,
code-intelligence 1.4. Concurrent PDF/status/evidence and analytical guide edits were preserved.
The [principal review](../../design_review/reviews/design_review_unified-domain-model_2026-11-01.md)
owns comparative preference. Tests, compatibility probes and measurements were not run.

## Version and source evidence

| Library | Current manifest/installed version | Research boundary |
|---|---|---|
| Pydantic | 2.14.1 | Context7 `/pydantic/pydantic/v2.14.1`; installed `main.py:410–451`, `fields.py:931–948`. Guide addendum 2.14.2 is separate. |
| pydantic-settings | 2.16.1 | Context7 `/pydantic/pydantic-settings`; source execution checked in installed `main.py:559–591`. Guide addendum 2.16.2 is separate. |
| jsonschema | 4.26.0 | Context7 `/python-jsonschema/jsonschema/v4.26.0`; installed `validators.py:225–242,307–316,1335–1405`. |
| PyArrow | 26.0.0 | Context7 `/apache/arrow` current/main; installed `table.pxi:6460–6497` checks row-construction semantics. |
| DuckDB | 2.0.0 | Context7 `/duckdb/duckdb-python` current/main; installed `_relation.py:2524–2529,2584–2602` checks delayed/reader behavior. |

Installed distribution METADATA and the product manifest were read without executing imports.
All five guides and advanced addenda were surveyed. Primary sources include
[Pydantic models](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/models.md),
[schema generation](https://github.com/pydantic/pydantic/blob/v2.14.1/docs/concepts/json_schema.md),
[settings acquisition](https://github.com/pydantic/pydantic-settings/blob/v2.16.1/pydantic_settings/main.py),
[JSON Schema references](https://github.com/python-jsonschema/jsonschema/blob/v4.26.0/docs/referencing.rst),
[Arrow table implementation](https://github.com/apache/arrow/blob/apache-arrow-26.0.0/python/pyarrow/table.pxi)
and [DuckDB migration](https://duckdb.org/docs/2.0/clients/python/migration).
Current-main retrieval is not exact-version qualification; unsupported advanced families retain
their guide's evidence limits. Existing LOP-X004/X006/X008/X009 suffice; no new pattern is needed.

## Reusable capability types

| Type | Mechanism and discharged work | Residual contract |
|---|---|---|
| pydantic/compiled-boundary | `create_model`, `Annotated`, `Field`, discriminated unions, `model_rebuild`, reusable `TypeAdapter` compile structure into validation/serialization. | Identity, cross-record integrity, lifecycle and effects need explicit domain owners; JSON/Python modes differ. |
| pydantic/presence-projection | `MISSING`, `model_fields_set`, `model_dump(exclude_unset=True)` retain supplied fields and native Python values. | Aliases, serializers, subclass/computed fields and tuple/list distinctions must match; reference rewriting remains a separate semantic operation. |
| settings/validated-resource-snapshot | `BaseSettings`, nested models, `settings_customise_sources` resolve typed acquisition. | Precedence does not skip source execution; operations must actually receive the snapshot. More sources or caching cannot repair missing propagation. |
| jsonschema/retained-portable-validation | `validator_for`, `check_schema`, reusable validators, explicit `referencing.Registry`, `iter_errors`. | Dialect and format policy, callback semantics and external-state invariants remain explicit. Schema assertions do not coerce or serialize. |
| arrow/typed-columnar-realization | Explicit nested schemas, safe casts, IPC/Parquet, compute/scanner/reader interfaces. | Metadata and physical validation do not prove domain invariants. `from_pylist` maps missing fields to null; presence may need explicit encoding. |
| duckdb/scoped-relational-operation | Relations/expressions/macros, Arrow registration, joins/grouping, `to_arrow_reader`. | Ordering, blocking operators, ownership and active results matter. `iter_rows` is delayed and retains a materialized result; it is not bounded-memory streaming. |

## Contextual applicability

Source paths below are relative to `python/corpus-structure/src/corpus_structure/`.

**Generated boundaries are a strength.** `semantic/boundary.py:54–90,154–239` builds strict,
frozen, extra-forbidden variants with supplied-field semantics. `prepare.py:731–741` enables
finite float fields for compiler 12/13. `types.py:379–430` caches field adapters under a release
lock using public `rebuild_annotation`, and separates structural/accepted validation context.
Earlier CBO-013 per-call/private-type premises cannot be reused unchanged.

**Shared reference traversal is implemented.** `semantic/reference_positions.py:31–221`
uses compiled positions, retains paths/duplicates, distinguishes fact/class references and
explicitly handles keyed collisions. Domain operations and evaluation share it. CBO-016's old
independent-walker premise is substantially superseded. Mechanical `_plain`/`_native` dumps
remain (`domain_operations.py:328–352`, visitor `:67–76`); prepared Pydantic serialization fits
conditionally after output-equivalence inspection, not as a replacement for the semantic visitor.

**Settings acquisition is coherent; operation propagation is incomplete.** `settings.py:117–143`
uses constructor/environment sources deliberately. `AnalyticsSettings:98–108` exposes resource
choices, but `domain_operations.consolidate_cut:2050–2075` opens `AnalysisScope(packet)` with
separate defaults (`analytics.py:1018–1025`). DA-020 now owns that narrowed diagnostic. Export
does consume capture settings (`cli/export.py:50–57`); no new settings root or provider framework
is implied by the missing consolidation input.

**Portable structural validation has retained-resource custody.** `pdf_payloads.py:320–347`
and `pdf_records.py:167–194` prepare checked cached validators with explicit local registries.
`pdf_payload_validation.py:90–231` separately checks metadata projections and domain/native
semantics. `pdf_contracts.py:107–171` retains producing schema custody and rejects external
references before validation. Absence of FormatChecker does not establish a defect where formats
are deliberately outside the retained structural profile (`model/semantic/pdf-records.yaml:9–10`).

**Arrow derivation and exactness already compose.** `analytics.py:498–507,637–700` derives
types/nullability/order from shared physical metadata; `:481–495` carries scoped identity.
`:712–781` retains exact lexical values alongside bounded analytical projections.
`analytical_profile.py:70–118` owns scale/rounding/refusal; a native decimal cast is not an
equivalent replacement merely because the result type matches. `pdf_payloads.py:45–169`
derives nested IPC layout with presence bitmaps and tagged integer/binary64 values; `:266–317`
checks framing/metadata/physical validity before separate semantic validation.
`companion_projection.py:82–163` derives SQL/Arrow return shapes. Intentional finite lowerings
should be extended through those owners, not replaced by arbitrary schema inference.

**Lazy lifetime coverage needs a bounded decision.** `analytics.py:429–462,1170–1183` guards
DuckDB method calls and wraps relations/connections/Arrow readers. It does not wrap Python
generators. Installed DuckDB `iter_rows` submits on first iteration, so a retained iterator's
later consumption bypasses the scope's explicit guard. Whether the closed native connection
refuses consumption or retained results remain accessible is unprobed. This is a source-established
support-boundary question, not an observed successful post-close escape. The selected guarded
Arrow reader route is useful contrary evidence. Explicitly supporting or refusing delayed iterator
results can fit the existing owner; no new lifetime framework is justified by this observation.

## Follow-up conditions

An added reference-bearing field should exercise shared construction and traversal; changed
decimal policy should retain exact lexical meaning; changed schema formats/dialects should have
explicit enforcement; non-default resources should reach actual consolidation; supported lazy
results should retain owner checks through consumption. These scenarios qualify adoption decisions,
not claims that the assembled product was tested in this assessment.

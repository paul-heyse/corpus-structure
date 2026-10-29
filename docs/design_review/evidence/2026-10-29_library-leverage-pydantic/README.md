# Pydantic applicability probe: release adapters, dumps and shared-$defs schemas

**Date:** 2026-10-29. **Assignment:** library applicability research, cluster R4 (validation,
serialization and settings), for the first `leverage-library-assessment` pass. **Source baseline:**
`d739b883e322adef7a3202e2896766ff71bcac5d` (clean apart from an untracked
`semantic/regeneration.py` that this probe does not import).

## Questions

1. **P1.** `PreparedRelease.property_adapter` builds `TypeAdapter(field.rebuild_annotation())` from
   the private `adapter._type`. Does that bare adapter keep the generated model's
   `ConfigDict(strict=True, allow_inf_nan=False)`? Is there a public route that does, built from the
   model class kept at preparation? Where is passing `config=` refused?
2. **P2.** Do `model_dump(exclude_unset=True)` and `TypeAdapter.dump_python(exclude_unset=True)`
   reproduce the hand projections `domain_operations._plain` / `_native` and `consolidation.plain`
   on compiler-generated models? This covers nested, keyed-map, list-inlined, alias, `MISSING` and
   Decimal fields.
3. **P3.** Does `models_json_schema` (or `TypeAdapter.json_schemas`) produce one shared-`$defs`
   document whose definitions equal the per-class `adapter.json_schema()` artifacts? Does the
   conditional-rule `__get_pydantic_json_schema__` fragment stay on the right definition?
4. **P4.** Would `PostgresDsn` accept the socket-only libpq URL form used by the default settings?

## Environment

- Python 3.14.10 via `uv run --no-sync python`. pydantic 2.14.1, pydantic-core 2.50.1. The other
  libraries are those in `uv.lock`; the installed `.venv` matches.
- The probe uses the repository's real compiler (`prepare_release`, profile `semantic-2`) on a
  small inline LinkML schema with these fields:
  - float and multivalued float;
  - a Decimal field with a bound;
  - a multivalued string;
  - inlined, keyed-map and list-inlined classes;
  - a non-inlined reference;
  - an aliased slot;
  - a class with a conditional rule.

  No database, network or installation is involved.

## Command

```bash
uv run --no-sync python docs/design_review/evidence/2026-10-29_library-leverage-pydantic/probe.py
```

Output: [`probe-output.txt`](probe-output.txt). The first three lines are LinkML generator warnings
written to stderr.

## Outcome: passed (each check ran and printed an observation)

**P1. Adapter configuration.**
- After `model_rebuild`, `model_fields[...].annotation` holds resolved types, not ForwardRefs. The
  resolved forms include `Thing`, `dict[str, Thing]` and `tuple[Thing, ...]`.
- The generated model refuses NaN (P1a).
- The current `property_adapter` accepts `nan` for a scalar float field, and `inf` for a
  multivalued float item, even with `strict=True` (P1b, P1c). `allow_inf_nan=False` is model
  configuration and does not travel with a bare annotation.
- A public route keeps the generated model classes at preparation and builds
  `TypeAdapter(annotation, config=ConfigDict(strict=True, allow_inf_nan=False))` per field. It
  refuses NaN and inf (P1d, P1e).
- On that route:
  - the `ge=0` bound and strictness are kept (P1i, P1j);
  - keyed-map member types and the keyed-member validator are kept (P1l, P1m).
- Passing `config=` is refused only when the annotation itself is a model, `dataclass` or
  `TypedDict` (`type-adapter-config-unused`, P1g). Those types carry their own configuration (P1f).
  It is allowed for `tuple[Model, ...]` (P1h).
- `TypeAdapter` exposes no public attribute for the adapted type; only `_type` exists (P1n).

**P2. Dump parity.**
- On this schema, `model_dump(exclude_unset=True)` equals `_native` exactly, tuples included (P2e).
- With tuples converted to lists, it equals `_plain` and `consolidation.plain` (P2d, P2f).
- Keys are field names, not aliases. `by_alias=True` gives the alias instead (P2g, P2h).
- `TypeAdapter.dump_python(exclude_unset=True)` matches `_native` on an adapter output (P2i).
- Decimal values stay Decimal, with scale kept, in Python mode.

**P3. Shared schema.**
- `models_json_schema` returns a `$ref` per model and one `$defs` holding every class (P3e, P3f).
- The shared `Thing` and `Holder` definitions equal the per-class schemas, minus their local
  `$defs` (P3h, P3j).
- The conditional `if`/`then` fragment sits on the `Thing` definition, both per-class and shared
  (P3a, P3c, P3g).
- `TypeAdapter.json_schemas` over the same adapters produces the identical definitions document
  (P3i). It also accepts union-boundary adapters, which `models_json_schema` (model classes only)
  does not take.

**P4.** `PostgresDsn` rejects `postgresql:///corpus?host=/var/run/postgresql&port=5434`, because it
declares `host_required=True` (P4a). It accepts a host URL (P4b).

## Limits

- One small schema. No abstract `kind`-discriminated boundary was exercised. Abstract boundaries
  were inspected only in source: their adapter wraps a union, so `property_adapter` refuses them
  today.
- No consumer route was changed or run. This probe establishes library behaviour on compiler
  output, not that the NaN gap is reachable through a production path.
- Downstream, `identity._meaning` and `canonical_bytes` refuse non-finite floats. That refusal is a
  `ValueError` raised later, not a validation error at the adapter.
- Parity is on the shapes listed above. Computed fields, extras and serializers do not occur in
  compiler output at this baseline (searched in `semantic/prepare.py` and
  `semantic/conditional_rules.py`).
- No timing was taken. No performance claim follows.

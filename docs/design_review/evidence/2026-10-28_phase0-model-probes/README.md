# Phase 0 model probes, 2026-10-28

**Status, 2026-10-28: environment built; probes Q-1 to Q-5 and Q-7 not yet run.**

These are bounded investigations that decide between the stated variants of the phase 0 model
foundations. They are owned by the [phase 0 series](../../../plans/phase-0_2026-10-28.md), whose §11
holds the row for each probe, and they implement the probes of the
[domain-model alignment review](../../reviews/design_review_domain-model-alignment_2026-10-28.md) §10.
A probe outcome selects a variant; it never reopens a decision. The folder writes no product code.

## The probes

| Probe | Package | Question | Decides | Record |
|---|---|---|---|---|
| Q-1 | P0-M-Q1 | Can a `PydanticGenerator` subclass, or an own emitter, over S4's `core.yaml` produce the core shapes? Discriminated `t`/`op` unions with a named recursive `Condition`, `MISSING`, frozen tuples, both `ci:form` variants and prefixed aliases | M5's variant: Stage B or the fallback | `p0q.stage-b` |
| Q-2 | P0-M-Q2 | Do permissible-value `in_subset` member properties pass `linkml-lint` and read back through `SchemaView`? | M1's declaration form: `in_subset` or `ci:properties` | `p0q.member-properties` |
| Q-3 | P0-M-Q3 | `MetaData` generated from a LinkML sketch of five D3 tables plus an overlay, compared with S6's DDL through a pglast-normalized projection; Alembic autogenerate with a `CreateView` table | M2's overlay/compiler split | `p0q.port-check` |
| Q-4 | P0-F-Q4 | COPY at run scale on `18/corpus`, with and without same-run composite FKs and per-version vocabulary FKs, paired with the `s6.volume` rerun | INV-03/INV-08 enforcement: FK or bulk writer | `p0q.fk-cost` |
| Q-5 | P0-P-Q5 | ADBC `fetch_record_batch` → DuckDB relation → Arrow → psycopg `Copy.set_types` and pgpq: absent versus null, JSONB, numeric, `timestamptz`, and the memory of one join | P1's loader, P3's writer, whether pgpq is adopted | `p0q.pool-roundtrip` |
| Q-7 | P0-P-Q7 | Declared must-link order against `USING KEY` components with a cannot-link anti-join, over shuffled inputs | F03's closure; the phase 2 merge implementation | `p0q.merge-order` |
| — | P0-F-5 | Validating a `BaseSettings` reads the environment | Coordinator decision 26's evidence | `p0q.settings-env` |

## Environment

The project in this folder is `pyproject.toml` with `uv.lock`, pinned exactly on 2026-10-28:
- linkml 1.12.1 and linkml-runtime 1.12.1;
- pydantic 2.14.1 and pydantic-settings 2.16.1;
- sqlalchemy 2.1.5 and alembic 1.20.0;
- pglast 8.7;
- psycopg 3.3.6;
- pyarrow 26.0.0, adbc-driver-postgresql 1.13.0, duckdb 2.0.0 and pgpq 0.12.0;
- jsonschema 4.26.0.

It is synced to `build/probe-venv`. Run a probe from the repository root:

```sh
UV_PROJECT_ENVIRONMENT=$PWD/build/probe-venv uv run --project docs/design_review/evidence/2026-10-28_phase0-model-probes python docs/design_review/evidence/2026-10-28_phase0-model-probes/code/<probe>.py
```

Check that the environment still matches its lock with
`UV_PROJECT_ENVIRONMENT=$PWD/build/probe-venv uv sync --project … --locked --check`.

Probes that need a database use their own databases on the `18/corpus` cluster (`p0q_*`) and drop them
afterwards. The `main` cluster is never touched.

## Layout

- `code/`: probe scripts.
- `results/<probe>/`: their outputs.
- `records/<id>.json`: evidence records (ADR-0010). Finalize with `just evidence finalize
  2026-10-28_phase0-model-probes <id>`, then run `just evidence`.

## Q-2: member properties (`p0q.member-properties`)

**Question.** Can member properties (modality `premise_forming` `{supposed}`, `attribution_identifying`
`{cited}`, `conflict_bearing` `{asserted, defined}`; statement-kind `claim_bearing`; segment-kind
`annotation_unit`, `statement_anchor`, `search_block`, `container`) be declared as native
permissible-value `in_subset`, linted, and read back through `SchemaView`? Otherwise, does one scalar
`ci:properties: "a b"` annotation per member round-trip?

**Method.** `code/q2_member_properties.py` reads S4's `core.yaml` and writes, under `results/q2/schema/`:
- `core_in_subset.yaml`, with the eight subsets declared;
- `core_ci_properties.yaml`;
- `core_seeded.yaml`, in which one member names an undeclared subset;
- an unchanged baseline copy, `core_s4_baseline.yaml`.

A probe `SegmentKind` enum (D3's twenty kinds) is added. S4's `ci:claim_bearing` annotations are
replaced by the property. Each file is linted on its own with S4's `.linkmllint.yaml`, and the
membership read back is compared with a hand-written expectation table in the script. The table is
derived from neither file. The yaml/JSON dumps, `gen-json-schema` and `gen-pydantic` are also run.
Output: `results/q2/result.json`.

**Result (Tested, 2026-10-28, linkml 1.12.1).**
- **Lint.** Both forms lint with 0 errors. The only findings are the baseline's own two
  `standard_naming` warnings, on `t` and `v`. `no_undeclared_subsets` checks enum members, so the seeded
  undeclared subset is an error.
- **Readback.** `get_enum(E).permissible_values[m].in_subset` returns the subset names
  (`SubsetDefinitionName`), and so does `induced_enum`. All 8 properties equal the expectation table.
  The fallback annotation reads back as a string, and splitting it gives the same 8 of 8.
- **Round trip.** `yaml_dumper` and `json_dumper` keep `in_subset`, so the canonical JSON behind the
  revision hash carries the declarations. Both stock generators accept both files.
- **Accessors the plan named.** `permissible_value_ancestors` is the members' `is_a` closure and
  returns `['supposed']`: it does not expose subsets. `annotation_dict` addresses elements only, and a
  member raises `AttributeError`. A consumer reads `pv.in_subset` directly.
- **Shared namespace.** Member-property subsets share the schema's single subset namespace with the
  element subsets `structural` and `unsupported`. The declaration check (§3.1) must tell the two apart,
  for example by the set of names used on members.
- **Not tested.** A pack adding members with properties to a core enum: LinkML has no in-place enum
  extension.

**Feeds.** P0-M-1 (M1's declaration form). `in_subset` is viable, and `ci:properties` is not needed as
a fallback.

## P0-F-5: validating a `BaseSettings` reads the environment (`p0q.settings-env`)

**Question.** Coordinator decision 26 keeps operations models (run options, method `params`) frozen
plain `BaseModel`s, never `BaseSettings`. Its premise is that validating a `BaseSettings` from stored
data reads the current environment. Does it, under pydantic-settings 2.16.1?

**Method.** `code/settings_env.py` defines a `BaseSettings` with `env_prefix="P0Q_SETTINGS_ENV_"` and
two `int` fields `a` and `b` (default 0), and a plain `BaseModel` of the same shape. With
`P0Q_SETTINGS_ENV_A=1` set, it calls `model_validate({})`, `model_validate({"b": 2})` and
`model_validate_json("{}")` on each and compares the results with a hand-written expectation.
Output: `results/settings-env/result.json`.

**Result (Tested, 2026-10-28, Python 3.14.10, pydantic 2.14.1, pydantic-settings 2.16.1).**
- All three calls on the `BaseSettings` returned `a=1` from the environment; a supplied `b=2` was
  kept.
- The plain `BaseModel` kept `a=0` in all three.

**Feeds.** Coordinator decision 26 (foundations §3.5): a stored payload re-read through a
`BaseSettings` would mix in the current environment, so only `Settings` is one.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 2 current, 0 superseded.


**Phase 0 model probes**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Validating a pydantic-settings BaseSettings reads the environment](records/p0q.settings-env.json) | P0-F-5 | passed | coordinator decision 26, foundations §3.5 operations models, foundations §3.9 | 2026-10-28 |
| [Member properties on enum members: native in_subset versus a scalar ci:properties annotation](records/p0q.member-properties.json) | P0-M-Q2 | passed | P0-M-Q2, model-and-projections §3.1 member properties | 2026-10-28 |
<!-- evidence-index:end -->

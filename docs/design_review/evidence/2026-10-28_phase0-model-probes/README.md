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

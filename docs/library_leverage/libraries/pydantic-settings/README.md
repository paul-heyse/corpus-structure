# pydantic-settings

**Realization assessed:** pydantic-settings 2.16.1.

**Research.** The R4 cluster did this work on 2026-10-29. It read the
[overview](../../../libraries/data_model/pydantic-settings.md) end to end, then inspected the installed source
(`pydantic_settings/main.py`; `pydantic/networks.py`) and ran one probe
([evidence](../../../design_review/evidence/2026-10-29_library-leverage-pydantic/README.md), probe
P4).

## Reusable opportunity types

<a id="pydantic-settings-nested-section-resolution"></a>

### `pydantic-settings/nested-section-resolution`

**Need.** Typed process configuration made of nested sections, read from the environment and the
constructor.

**Mechanism.**
- `BaseSettings` with nested `BaseModel` sections. Nesting a `BaseSettings` inside another is
  discouraged.
- `env_nested_delimiter`, which works at any depth.
- `settings_customise_sources` to control source ordering.
- Deep merge across sources.
- `settings_cached()` and `settings_clear_cache()`, available in 2.16.

**Conditions.**
- `extra="forbid"` does not refuse unknown environment variable names.
- A nested alias limits which names merge.
- `PostgresDsn` sets `host_required=True` (installed source), so it rejects socket-only libpq URLs
  such as `postgresql:///db?host=/var/run/...` (probe P4a).
- A settings object is a snapshot; it does not track later environment changes.

## Applicability at source `d739b88`, re-checked at `3d97504`

<a id="applicability-cbo-004"></a>

### CBO-004 — per-principal connections: **fits with conditions; premise updated**

Opportunity: [CBO-004](../../codebase/engineering-workflows.md#cbo-004).

**What changed.** Commit `3d97504` landed during this assessment. `DatabaseSettings` now has flat
`url` (writer), `maintenance_url` and `evaluator_url` fields. `semantic/runtime.connection_settings`
derives the reader URL from them.

**Assessment.**
- Nested per-principal sections are supported. Environment names reach them through `__` at any
  depth. The repository's `known_env_names`, however, enumerates only two levels and would need
  extending.
- `PostgresDsn` is ruled out for the socket-URL form. The current default,
  `postgresql://corpus_sem_writer@/...`, was not probed.
- Declaring which principal each command uses is application code.
- The comparative review should decide between flat fields and nested sections.

## Coverage limits

Only the DSN refusal was probed. No settings change was run.

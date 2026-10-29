# Typer

**Realization assessed:** Typer 0.27.3, which ships a vendored Click.

**Researched:** 2026-10-29 by the R6 cluster. The [overview](../../../libraries/typer.md) was read
end to end. Follow-ups were Context7 (`/websites/typer_tiangolo`) and the installed source:
`core.py`, `main.py`, `exceptions.py` and `__init__.py`.

## Reusable opportunity types

<a id="typer-central-exception-exit-mapping"></a>

### `typer/central-exception-exit-mapping`

This type is a negative result, followed by the routes that remain.

**Finding.** Typer has no registry that maps exceptions to exit codes.
- The main loop catches only the vendored `ClickException`, `Exit`, `Abort`, `EOFError` and
  `KeyboardInterrupt`.
- A bare `TyperException` subclass is not caught and prints a traceback.

**Routes.**
1. **Override the root group.** Pass `typer.Typer(cls=<subclass of typer.core.TyperGroup>)` and
   override `invoke`. This covers every subcommand and works under `CliRunner`. The drawbacks:
   `TyperGroup` is not exported at the top level, and subclassing Click classes is a weaker contract
   now that Click is vendored.
2. **Wrap the entry point.** Call `app(standalone_mode=False)` inside the entry function. The caller
   must then show usage errors itself, and `CliRunner` tests bypass the wrapper.
3. **Use a shared context manager or decorator.**

**Residual.** A per-command output shape, such as a JSON envelope that depends on `--json`, is not
visible from the root group.

<a id="typer-command-tree-resource-scope"></a>

### `typer/command-tree-resource-scope` (light)

**Mechanism.**
- `add_typer` for sub-apps.
- Group callbacks with `invoke_without_command`.
- `ctx.obj`, reached via `ctx.find_root()`.
- `ctx.with_resource(cm)` and `ctx.call_on_close`, which tie an engine or connection to the
  command's lifetime.

**Limit.** Typer supplies no atomicity or transaction semantics.

## Applicability at source `d739b88`

<a id="applicability-cbo-012"></a>

### CBO-012 — CLI refusal mapping: **fits with conditions**

**Opportunity:** [CBO-012](../../codebase/consumers-and-operations.md#cbo-012).
**Type:** [central-exception-exit-mapping](#typer-central-exception-exit-mapping).

- Every CLI site already exits with code 1. What varies is the message channel and its shape:
  - `refused:` on stderr;
  - bare messages;
  - a JSON envelope only in `query.py`.
- A root `cls=` group can centralize the mapping, but the JSON-envelope shape stays per command.
- The `cls=` route was not probed; its behaviour is inferred from the installed source.

<a id="applicability-cbo-004"></a>

### CBO-004 (informs) — command path composition

**Type:** [command-tree-resource-scope](#typer-command-tree-resource-scope).

- Sub-app composition already exists: `mcp_app` uses `add_typer`.
- An engine can be scoped to a command's lifetime through `ctx.with_resource`.
- A refusal-safe prepare → persist → activate sequence is a domain and transaction property. Typer
  supplies only the command boundary.

## Coverage limits

The `cls=` route was not probed.

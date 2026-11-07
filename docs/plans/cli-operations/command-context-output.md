# Command surface, context and output

**Accepted target.** Companion to the [CLI operations coordinator](../cli-operations_2026-11-07.md).
Owns the CLI-01 contract consumed by testing, model changes, corpus reads and host operations.
The coordinator owns status and dispositions.

<a id="CLI-01"></a>
## CLI-01 · Establish the installed command contract

### Typer 0.28.0 transition

Begin with the I01 dependency-only slice. Change the declared pin from 0.27.3 to exactly
0.28.0 and update the lock for that dependency. Preserve other pins unless the resolver
establishes a specific compatibility requirement. Review the lock diff, run `just ready`
and exercise the current installed grammar before changing command registrations. Keep
this slice independently reviewable so an unrelated route migration cannot obscure
framework regressions.

Typer 0.28.0 infers the option name from the Python parameter even with a case-matching
custom `metavar`. In the paired fixture, the accepted spelling changed from
`--ITEM-COUNT` to `--item-count`, while the explicit alias and display label still worked.
Check actual option declarations, callers and generated help. Declare explicit names where
spelling is part of the contract. Use `typer.testing.CliRunner.invoke()` for grammar controls
and fresh subprocesses for root/nested help, unknown-option exit and stderr, and reference
generation under invalid DB settings. Record the installed versions and exact check scope.
[Typer 0.28.0 release](https://github.com/fastapi/typer/releases/tag/0.28.0) ·
[Tagged option inference](https://github.com/fastapi/typer/blob/0.28.0/typer/main.py#L1361-L1365) ·
[Tagged test runner](https://github.com/fastapi/typer/blob/0.28.0/typer/testing.py) ·
[Isolated comparison evidence](../../design_review/evidence/2026-11-07_cli-typer-028/README.md)

### Routes and invocation intent

Keep the existing explicit `REGISTRY`, `CliState`, `emit` and `failure_boundary` as the starting
point. First migrate installed `ci status` through lazy context, refusal rendering and provenance.
Use its existing typed settings and domain status. Add `ci context show` and `ci doctor` as bounded
reads. Map commands by operation intent and update affected documentation with each migration.
Public spellings may stay where the same operation and consumer exist. Remove inert `Planned`
entries when adopting the surface and link future product work to its owner.

| Journey | Command and responsibility |
|---|---|
| Environment | `ci doctor`, `ci context show`, `ci setup`. Zero operands in a configured checkout. Setup is an explicit effect. A fresh checkout still uses the first-install script before `ci` is available. |
| Repository automation | `ci test`, `ci check`, `ci format`, `ci docs check`, `ci evidence check`, `ci evidence retain RESULT`, and named ADR actions. Each maps to an owned recipe or uses the established owner through a recipe where a new use is needed. |
| Managed output | `ci results list/show/watch/export/gc`. Selection or deletion is explicit where it changes the effect. Delivery path is optional. |
| Model and deployment | `ci model check`, `ci model change preview REQUEST`, `ci model change apply CHANGE`, and explicit native/deployment effects. Preserve `ci schema` operation names where existing consumers use the same meaning. |
| Product and host | Project, source, ingest, run, read, review, database and release journeys from CLI-06/07. Put local cluster administration behind named routes to its existing recipes. A production target is independently configured. |

**Recipe boundary.** CLI-RC01 places `ci` above `just` for existing recipe classes. Invoke an
allowlisted recipe with an explicit argv from the resolved checkout, using `just --justfile PATH
--working-directory PATH RECIPE …` when needed to anchor selection. Product operations continue
to call their application owners. A recipe in this adapter's call graph must reach the native
tool or application operation directly. Refactor a recursive edge before adoption. Preserve useful
direct recipe invocations and their established defaults. Keep operator-selected operands typed and
validate paths or selectors before use. An outer argv alone cannot prevent shell interpretation of
interpolated recipe parameters. Use `[positional-arguments]` and quoted `"$@"` for multi-argument
handoff. For `ci test`, recognize the explicit `--` at the entry boundary for that command,
parse its prefix with the normal strict grammar, and carry the literal suffix to the named
recipe after the test owner validates it. `Context.args` under `allow_extra_args` cannot
establish whether an extra positional token followed `--`, as the paired Typer fixture
showed. Apply CLI-03 policy before executing the child. Other commands use their declared
grammar and recipe mapping. [just 1.58.0 positional arguments](https://just.systems/man/en/positional-arguments.html) ·
[just invocation options](https://github.com/casey/just/blob/1.58.0/src/config.rs) ·
[Python 3.14 `subprocess.Popen`](https://docs.python.org/3.14/library/subprocess.html#subprocess.Popen)

**Typer 0.28.0.** Compose explicit named groups with `Typer.add_typer(..., name=...)`.
Use `Annotated` with `typer.Argument` or `typer.Option` and Enum/Literal or `parser=`
for finite choices and local conversion. Reserve paired optional Boolean flags for distinct
inherit, enable and disable intent. Keep parameter callbacks to local conversion and
presentation. Defaults can invoke callbacks and an explicit later option can run before an
earlier default, with partial `ctx.params`. Build and validate the owned request after
parsing. Use `expose_value=False` only for a concrete adapter control with a compatible
callback signature. Accept complex requests via validated file, stdin or stored equivalent
where the operation supports those forms. Use `rich_help_panel` and concise examples for
defaults. Generate the command reference via
`typer --app app corpus_structure.cli.app utils docs --name ci`. Keep journey examples
in documentation and compose workflows in their owners.
[Typer group construction](https://github.com/fastapi/typer/blob/0.28.0/typer/main.py#L1213-L1286) ·
[Parameter processing](https://github.com/fastapi/typer/blob/0.28.0/typer/_click/core.py) ·
[Custom types](https://typer.tiangolo.com/tutorial/parameter-types/custom-types/) ·
[Typer Markdown generation](https://github.com/fastapi/typer/blob/0.28.0/typer/cli.py#L278-L312)

**Invocation context.** Anchor generated and managed paths to the selected checkout. Resolve
the locked toolchain once for headless Codex and support machine-local overrides via the existing
`.envrc.local` boundary. A launcher may resolve a prepared checkout and pass its environment
without repeating inline variables. Activation performs no installs, builds or service starts.
The settings owner retains constructor, environment and default precedence through
`Settings.settings_customise_sources()` and `SettingsConfigDict`. Typer `Context.get_parameter_source()`
distinguishes actual shell input from parser defaults. Only applicable explicit overrides become
constructor values. Provenance records where a value came from. The operation resolves target
authority and acquires invocation resources through `Context.with_resource()` after validation. Project effective target/role, project, workspace, interpreter, source/release and
managed results root via the redacted `settings_report()` boundary. Keep secrets and ambiguous
targets out of diagnostics. Missing prerequisites name the field or effect and a direct remedy.
`default_map` may project an already resolved setting if needed. Help and completion acquire no DB,
provider or model state. Use bounded local `autocompletion=` for profiles, choices or readily available IDs. The
0.28.0 Bash probe received empty callback `args` and potentially partial parsed context.
Use safe context where present and fall back to static suggestions or none when a selector is
ambiguous. Keep prompts optional for a named interactive journey and preserve headless use.
[Typer context](https://typer.tiangolo.com/reference/context/) ·
[Typer 0.28.0 completion adapter](https://github.com/fastapi/typer/blob/0.28.0/typer/core.py) ·
[pydantic-settings 2.16.1 source precedence](https://github.com/pydantic/pydantic-settings/blob/v2.16.1/pydantic_settings/main.py) ·
[Settings owner](../../../python/corpus-structure/src/corpus_structure/settings.py) ·
[Bootstrap](../../../scripts/setup-env)

### Safe output and progress

Project safe diagnostic fields from the operation owner and the
[managed-results contract](managed-results-and-testing.md#action-driven-diagnostics).
The current failure adapter renders interpolated external fields on a markup-enabled console.
Redact at the field owner before output or capture, then sanitize untrusted terminal controls
before rendering. Use Rich 15.0.0 `Text` or `Console.print(markup=False, highlight=False)` to
preserve bracketed text literally and apply trusted styles separately. Literal rendering alone
still passed SGR and OSC controls in the bounded probe. Keep the typed serializer as the machine
boundary. Under `--json`, stdout carries the final typed result or operation refusal. Usage errors
remain stderr with exit 2. Preserve different exits and remedies for usage, refusal, tool failure
and interruption. A structured usage envelope requires a demonstrated machine consumer and
qualification of the parser boundary.

Use one scoped `Console(stderr=True)` and `Table` or `Tree` projections for human output.
Use `Progress(console=stderr, auto_refresh=False, redirect_stdout=False, redirect_stderr=False)`,
`add_task()`, `update()` and a bounded batch `refresh()` over owner events. Use `total=None`
for unknown work and quiet/plain headless presentation. An injected `get_time=` can make
presentation tests deterministic. Choose `Syntax(..., start_line=…, highlight_lines=…)`
only for authorized, already selected excerpts. Use opt-in
`Traceback.from_exception(show_locals=False)` only after reviewing messages and notes for
exposure. The supervisor owns settlement, and grouped presentation preserves each failure's
identity.
[Rich 15.0.0 Console](https://github.com/Textualize/rich/blob/v15.0.0/rich/console.py) ·
[Text](https://github.com/Textualize/rich/blob/v15.0.0/rich/text.py) ·
[Progress](https://github.com/Textualize/rich/blob/v15.0.0/rich/progress.py) ·
[Syntax](https://github.com/Textualize/rich/blob/v15.0.0/rich/syntax.py) ·
[Traceback](https://github.com/Textualize/rich/blob/v15.0.0/rich/traceback.py)

**Acceptance.** Use `typer.testing.CliRunner.invoke()` for grammar, result and refusal checks in
isolated test processes. Use installed subprocesses for true stream/exit behavior, fresh and
headless startup, completion and cancellation. Exercise two checkouts, bad settings provenance,
missing database and stopped provider. Confirm help stays usable and that terminal width, color
and child warnings leave the same JSON meaning and clean stdout. Exercise one direct recipe and
the corresponding installed route with spaces, literal metacharacters and option-looking tokens.
Reject extra tokens before the separator and reserved options after it. Show the adapter cannot
re-enter itself or silently select another checkout. In an installed subprocess, verify literal
brackets, Unicode and controlled multiline output, suppress untrusted OSC/SGR and credentials,
and assert clean JSON stdout independently. Compare generated command reference to
registered commands. The recipe remains independently usable for recovery.
[Typer testing](https://typer.tiangolo.com/tutorial/testing/) ·
[Invocation and output owner](../../../python/corpus-structure/src/corpus_structure/cli/output.py) ·
[Failure adapter](../../../python/corpus-structure/src/corpus_structure/cli/failures.py)

### Completion audit follow-up

**CLI-CA01 · Invocation context and safe output.** The Typer pin, workspace override, lazy help
and reference generation have bounded installed evidence. `ci context show` reports resolved
values and environment names, but cannot say which source won or resolve the interpreter,
operation purpose and source/release binding or their absence. Move these projections through the
existing settings and operation context owners. `ci status --json` sends command refusals to
stderr alone, and its Rich tables pass external strings directly to markup-enabled rendering.
An invalid `CORPUS_GPU__MODE` produced a traceback and empty machine output. The active
`CORPUS_CI_RESULTS` override appeared in `unknown_env` even while selecting the results directory.
Recipe reports cut their raw streams before sanitizing. An installed command returned a synthetic
URI credential when only its prefix fell outside the excerpt. Apply the safe rendering boundary
before truncating, and use the typed refusal route for status. Qualify real redirected output,
literal text and control handling, environment precedence and checkout isolation. Retain the
existing distinction between usage errors and typed operation results. Live test progress and
unavailable diagnostics belong to [CLI-CA02](managed-results-and-testing.md#completion-audit-follow-up).
[Context and recipe reports](../../../python/corpus-structure/src/corpus_structure/cli/operations.py#L27) ·
[Settings report](../../../python/corpus-structure/src/corpus_structure/settings.py#L158) ·
[Status rendering](../../../python/corpus-structure/src/corpus_structure/cli/status.py#L15) ·
[Output owner](../../../python/corpus-structure/src/corpus_structure/cli/output.py#L56)

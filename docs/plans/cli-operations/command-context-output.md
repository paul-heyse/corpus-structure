# Command surface, context and output

**Proposed.** Companion to the [CLI operations coordinator](../cli-operations_2026-11-07.md).
Owns the CLI-01 contract consumed by testing, model changes, corpus reads and host operations.
The coordinator owns status and dispositions.

<a id="CLI-01"></a>
## CLI-01 · Establish the installed command contract

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
handoff where required. Bound tool-specific passthrough to its owned command. Never expose a generic
recipe or shell forwarding surface. [just 1.58.0 positional arguments](https://just.systems/man/en/positional-arguments.html) ·
[just invocation options](https://github.com/casey/just/blob/1.58.0/src/config.rs) ·
[Python 3.14 `subprocess.Popen`](https://docs.python.org/3.14/library/subprocess.html#subprocess.Popen)

**Typer 0.27.3.** Compose named groups with `Typer.add_typer(..., name=...)` and explicit registration.
Use `Annotated` with `typer.Argument` or `typer.Option` and Enum/Literal or a native `parser=`
for finite choices and value conversion. Put cross-field rules in the typed request owner.
Complex requests can be a validated file, stdin or a stored equivalent. Use `rich_help_panel`
and concise examples for defaults. Generate the command reference from the registered surface via
the pinned `typer --app app corpus_structure.cli.app utils docs --name ci` route. The current
app generates Markdown with an invalid database setting. Recheck the changed app with invalid
settings and providers stopped. Keep journey examples in documentation. The pinned group construction
assembles commands by name and does not pass `chain=True` to the constructed group. Compose
workflows in their owners and keep registered names unambiguous.
[Typer group construction at 0.27.3](https://github.com/fastapi/typer/blob/0.27.3/typer/main.py#L1213-L1286) ·
[Custom parameter types](https://typer.tiangolo.com/tutorial/parameter-types/custom-types/) ·
[Typer CLI reference generation](https://github.com/fastapi/typer/blob/0.27.3/typer/cli.py#L278-L312)

**Invocation context.** Anchor generated and managed paths to the selected checkout. Resolve
the locked toolchain once for headless Codex and support machine-local overrides via the existing
`.envrc.local` boundary. A launcher may resolve a prepared checkout and pass its environment
without repeating inline variables. Activation performs no installs, builds or service starts.
The settings owner retains constructor, environment and default precedence through
`Settings.settings_customise_sources()` and `SettingsConfigDict`. Typer `Context.get_parameter_source()`
distinguishes actual shell input from parser defaults. Only applicable explicit overrides become
constructor values. Use `Context.with_resource()` for invocation-owned resources when acquisition
is needed. Project effective target/role, project, workspace, interpreter, source/release and
managed results root via the redacted `settings_report()` boundary. Keep secrets and ambiguous
targets out of diagnostics. Missing prerequisites name the field or effect and a direct remedy.
`default_map` may project an already resolved setting if needed. Help and completion acquire no DB,
provider or model state. Enable documented completion for real consumers, with bounded local
`autocompletion=` for profiles, choices or readily available IDs.
[Typer context](https://typer.tiangolo.com/reference/context/) ·
[Typer completion callbacks](https://typer.tiangolo.com/tutorial/options-autocompletion/) ·
[pydantic-settings 2.16.1 source precedence](https://github.com/pydantic/pydantic-settings/blob/v2.16.1/pydantic_settings/main.py) ·
[Settings owner](../../../python/corpus-structure/src/corpus_structure/settings.py) ·
[Bootstrap](../../../scripts/setup-env)

**Rich 15.0.0 and machine output.** Use one scoped `Console(stderr=True)` for diagnostics and
`Table` or `Tree` for human results derived from the typed result. Use `Progress.add_task()` and
`Progress.update()` on truthful supervisor events, with `total=None` when unknown. Set
`redirect_stdout=False` and `redirect_stderr=False` on `Progress` or `Live`. Where updates are
sparse, use `auto_refresh=False` and explicit `refresh()`. Headless output uses quiet or plain
progress. Use `Text`/markup-disabled rendering for external strings and sanitize terminal controls
separately. `RichHandler(console=…, markup=False, tracebacks_show_locals=False)` is available for
ordinary stderr logging. Under `--json`, emit one final result or typed operation refusal on
stdout. Announce the result ID, progress and child diagnostics separately. Typer usage errors
retain stderr and exit 2 even under `--json`. A later structured usage mode requires a concrete
machine consumer and proof of compatibility with the public parser boundary. Keep refusal, stale
selection, interruption and child tool failure actionable and distinguishable.
[Rich console](https://rich.readthedocs.io/en/stable/reference/console.html) ·
[Rich progress API](https://rich.readthedocs.io/en/stable/reference/progress.html) ·
[Rich 15.0.0 Live source](https://github.com/Textualize/rich/blob/v15.0.0/rich/live.py) ·
[Rich handler](https://rich.readthedocs.io/en/stable/reference/logging.html)

**Acceptance.** Use `typer.testing.CliRunner.invoke()` for grammar, result and refusal checks in
isolated test processes. Use installed subprocesses for true stream/exit behavior, fresh and
headless startup, completion and cancellation. Exercise two checkouts, bad settings provenance,
missing database and stopped provider. Confirm help stays usable and that terminal width, color
and child warnings leave the same JSON meaning and clean stdout. Exercise one direct recipe and
the corresponding installed route with literal metacharacters, and demonstrate the adapter cannot
re-enter itself or silently select another checkout. Compare generated command reference to
registered commands. The recipe remains independently usable for recovery.
[Typer testing](https://typer.tiangolo.com/tutorial/testing/) ·
[Invocation and output owner](../../../python/corpus-structure/src/corpus_structure/cli/output.py) ·
[Failure adapter](../../../python/corpus-structure/src/corpus_structure/cli/failures.py)

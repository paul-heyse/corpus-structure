# Complete Typer workflows and Rich presentation

**Status:** Proposed; 2026-11-01. [Coordinator](../structured-logging-observability_2026-11-01.md)
owns state. This plan develops LOG-06/08, O02/O03/O04/O09 and consumes LOG-01 configuration,
LOG-03 queries, LOG-04 incidents and LOG-07 metrics. CLI work begins with those contracts; final
acceptance consumes the implemented services. MCP is not a prerequisite for local development UX.

<a id="LOG-06"></a>
## LOG-06 — One discoverable diagnostic command surface

Compose ordinary named Typer groups. Explicit public names decouple Python refactoring from CLI
compatibility. `ci diagnostics --help` explains profiles, formats, scope and offline operation.
Root diagnostic options precede subcommands; retain current per-command --json behavior. Do not
use external Click extensions, unsupported chain=True, arbitrary generated nested-model signatures,
or unnamed groups whose lost callbacks would break lifecycle. Aggregate cross-field validation
belongs in shared typed requests, not only Typer callbacks.

| Command family | Resulting behavior |
|---|---|
| `ci diagnostics config` | Safe effective settings, source provenance, profiles, instrumentation and destinations; --json uses typed result |
| `ci diagnostics check` | Explicit destination/path/instrumentation preflight with classified outcomes; help performs no connectivity check |
| `events`, `follow`, `trace`, `explain` | Scoped filters, paginated snapshot reads, live JSONL following, causal history and stable event explanations |
| `summary`, `compare`, `incidents` | Coverage-aware run summaries/comparisons and retained occurrence groups |
| `metrics`, `assess` | Properly scoped measurements and declared threshold assessments for existing automation |
| `destinations`, `export` | Configured safe routes, selected local/remote export and qualified remote query options |

Selected export formats are jsonl, otlp-json and qualified ecs for structured records, plus
text/html/svg for human reports. A signal selector distinguishes event, trace and metric exports;
unsupported format/signal combinations fail explicitly rather than stringify another representation.
Advanced incident/profile/instrumentor configuration remains inspectable through config/check.

Shared scope/filter options use supported scalar/enum/date/path/repeated-value grammar, not shell
strings reinterpreted as code. JSON pages retain metadata and opaque continuations. `follow --jsonl`
is an explicit stream, not an endlessly growing single JSON result; Ctrl-C preserves cancellation
and closes its query scope. Missing/expired/sampled material is visible in both renderings.
Prompts are optional conveniences with explicit equivalent flags; no prompt in noninteractive
operation. Do not substitute Rich prompts for Typer parameter resolution/provenance.

Extend CliState with invocation-owned consoles and the runtime handle, acquired only when needed.
Use public Context.with_resource/call_on_close for invocation teardown. Process-global SDK lifetime
remains LOG-02's responsibility. Parser/Settings errors can precede callbacks; preserve safe early
error reporting without opening files/network for help. Successful result_callback processing is
not exception cleanup. Completion remains disabled unless deliberately selected later; no DB or
telemetry acquisition may become necessary for discovery.

### Rich composition

Share a stderr Console among RichHandler, Progress and Live; set redirect_stdout=False where
stdout is reserved for JSON/binary output. No progress/rendering on MCP protocol stdout. Present
multiple native tasks with fields for stage/provider/attempt; unknown totals stay unknown. Do not
infer commit/success from the completion bar. Control refresh frequency (default4Hz maximum) and
avoid rebuilding large history trees on every event. Plain/no-progress modes support headless and
accessible use. Construct fresh consoles for each invocation so captured/test streams apply.

Use Table/Tree/Text/Syntax/Pretty/Panel/Markdown where their semantics help. Escape markup and
sanitize terminal control sequences independently; external messages are plain Text by default.
Do not display arbitrary object introspection/locals by default. A bounded pager is optional for
human history; typed output remains available without it. App themes do not configure Typer's
private help console: use public rich_help_panel/markup metadata and generated command docs,
not monkey-patching rich_utils. TYPER_USE_RICH is import-time behavior; an application --plain
option does not retroactively disable that hook.

Completion: launch the installed executable with JSON, Rich/plain, narrow terminals, invalid input,
missing DB and unexpected errors. Assert stdout/stderr separately. Use fixed Console capture for
renderers and CliRunner for parser/provenance controls; fresh processes cover exception hooks and
import-time presentation controls. Help continues without settings/DB/scientific kernel acquisition.

<a id="LOG-08"></a>
## LOG-08 — End-user support preview and portable export

`ci support preview --run RUN` resolves an authorized pinned scope and shows included artifact
kinds, size, coverage, sensitive exclusions and local destination. `ci support export --run RUN
--out PATH` writes a bundle with versioned structured events, trace/metric slices, masked effective
configuration, build/recipe/release references and optional human summary. Event support IDs from
normal errors lead directly to the same workflow. No automatic upload is included.

Default bundle excludes source text, prompts/completions, credentials, SQL values, reference-authoring
content and locals. Explicit include requests require source permission and preview; a privileged
principal cannot accidentally export evaluator material into an extraction session. Safe metadata
may preserve useful opaque references without granting content access. Export rechecks scope and
uses the same pinned selection; it cannot silently widen to all files during a backend outage.

Use native Typer file/stream lifecycle for single-result JSON/text exports, including '-' where
appropriate. Lazy/atomic writes apply only to their file contract, not a transaction over a bundle.
Bundles stage privately, close selected readers/writers, then publish a manifest and final path;
interruption leaves an explicit incomplete owned artifact, never a success-looking bundle. Refuse
overwrite by default. I04 supplies the pinning lifetime; large content is streamed, not rendered
into RAM. Rich record=True exports HTML/text/SVG presentations from bounded selected results,
not an indefinite Live recording; structured JSON/OTLP remains the semantic interchange.

Completion: offline preview/export from an ended operation produces independently checked safe
content with matching scope and omissions; interrupted export, denied source, retention races,
corrupt tail and existing destination have explicit outcomes. A rendered report is not replay or
proof of successful domain completion.

## Sources

[Typer](../../libraries/python_introspection/typer.md) §§2–8 and advanced addendum §§1–9;
[Rich](../../libraries/python_introspection/rich.md) §§2–10;
[Logfire](../../libraries/logging/pydantic-logfire.md) §15.2 for instrumentation-health capabilities.
Prefer supported Context, file parameters, RichHandler/renderables and native export over custom
command engines or terminal UI frameworks. Exact public request/result schemas are settled in
LOG-01 and LOG-03 before implementation consumers depend on them.

# Command knowledge, native authoring and context

**Proposed delivery design, 2026-11-10.** [Coordinator](../cli-and-logging_2026-11-10.md)
owns CLD-02/03/04 state and acceptance, O01/02/03/08 disposition and execution entry.

## CLD-02 — Focused native references

Extend the existing interface to `ci docs commands [COMMAND ...] [--stdout | --json]`.
No operands returns the whole reference; a group returns that subtree; a leaf returns its own
reference. For example, `ci docs commands schema inspect --stdout` supplies exact syntax and
examples without unrelated commands. Resolve exact external tokens; unknown tokens and continuation
past a leaf refuse with the longest resolved prefix. Reference requests never invoke commands.

One small version-coupled producer constructs the actual installed tree through
`typer.main.get_command(app)`, traverses native `TyperGroup.get_command` with parent-linked
`typer.Context` objects, and calls `typer.cli.get_docs_for_click` on the selected object with
the complete external name. Do not parse command operands, run callbacks or acquire settings.
Close constructed contexts. Preserve actual usage/help/epilog generation and one final newline.
This is selected Typer0.28 reuse, not external Click interoperability. Isolate its imports and
test its selected native behavior; no alternate command schema or handwritten renderer.
[Generator0.28](https://github.com/fastapi/typer/blob/0.28.0/typer/cli.py),
[construction](https://github.com/fastapi/typer/blob/0.28.0/typer/main.py),
[group](https://github.com/fastapi/typer/blob/0.28.0/typer/core.py).

Direct `--stdout` returns Markdown through existing delivery without managed acquisition.
Default/JSON delivery retains `commands.md`, selected tokens and existing Delivery identity/path.
Keep `--stdout --json` invalid. Make `just ci-reference` call the direct route; remove the reverse
recipe subprocess from command_reference, obsolete reference subprocess/cancellation branches and
their mechanism-only tests. Inspect documentation publisher consumers of that recipe and migrate
them together. Preserve actual broken-pipe and failed-publication behavior independently of the
removed child process. Native in-process generation avoids unnecessary subprocess preparation.

Complete task descriptions, external operand names, meaningful defaults/limits, examples and
domain-reader links across schema compile/check/derive/native-candidate/explain-operation/diff/
inspect/diagnostic; interpretations lookup/review/records/measurements/export-contract/author;
research compare-exclusions; db describe; model change inspection/preview/apply/candidate/
registration/deployment. Use public panels for inputs, correction, dependencies and delivery.
Focused Markdown must retain full dual-flag spellings even when terminal tables abbreviate them.
Describe read/write behavior accurately without deriving authorization from parser metadata.

Retain local native completion and the installed executable. Typed command inventory is deferred
until a structured consumer cannot use focused reference; no remote completion, new dispatcher,
generated signatures or automatic unnamed merging is selected. Native docs plus current domain
contract inspection is simpler than another catalog. The illustrative journey is selected
interpretation-author reference → retained input contract → supplied input authoring, preserving
structural versus accepted validation and private versus selected knowledge distinctions.

## CLD-03 — Reusable grammar with domain authority retained

Introduce one small declaration module for genuinely shared CLI meanings, using `Annotated` aliases,
finite Literal/Enum choices, pure parsers, explicit external names and numeric/path constraints.
Start with correction projection, retention, dependency selection and contract inspection in the
commands above. Existing `testing.ReportLimit` is a useful native example; do not combine unrelated
integer policies merely to reduce repetition.

| Shared family | Owning limits and consumer scope |
| --- | --- |
| Correction detail/raw choice | Explicit Boolean names/help across schema compile/check/inspection; raw remains opt-in |
| Correction count/depth/bytes | Mirror current correction owner: 1–1000 errors, 1–16 depth, 1024–1048576 bytes; validate final DMC contract in CLD-00 |
| Retention | compile/check explicit retention flag; direct reads remain acquisition-light |
| Dependency selectors | compile/check/explain-operation/diff; reuse the dependency owner’s actual ranges/choice meanings |
| Contract view/kind/purpose/page | schema inspection uses its finite existing domain choices and limits |
| Retained diagnostic bytes | Separate 1024–8388608 read limit; never conflate with correction projection or research query budgets |

Parser refusal of malformed scalars intentionally precedes acquisition. Cross-field validity,
resource lookup, release admission and purpose remain with existing request/operation owners shared
by MCP. Do not clamp invalid bounds. Keep logical paths, filesystem paths and opened resources distinct.

Extract ordinary shared preparation/report orchestration where schema check currently calls the
compile callback. Command functions retain their own invocation/custody responsibilities; internal
calls must not bypass or repeat settlement. Migrate all compatible declarations and remove obsolete
conversions/helpers in the same slice. Retain explicit registration and lazy heavy imports. Preserve
the raw `ci test --` split because parsed extras do not retain separator provenance.
[Native parameter grammar](../../libraries/python_introspection/typer.md#3-typed-parameters-conversion-and-validation),
[custom parsers](https://typer.tiangolo.com/tutorial/parameter-types/custom-types/),
[source correction limits](../../../python/corpus-structure/src/corpus_structure/semantic/correction_detail.py).

File-object/dash/lazy/atomic features are retained for a selected simple-stream consumer; they cannot
replace bounded authenticated reads or managed publication. Prompts, launchers, REPLs and shell
installation provide insufficient value for this unattended target. Custom classes/normalization
are not selected because native metadata and pure operations suffice.

## CLD-04 — Same-snapshot configured selection

Extend existing `ci context show --target development|deployment` with a typed `selection` product:
profile, target parameter source, `configured_unobserved` standing, canonical selected settings
section, relevant masked resource fields and their existing contribution origins. Retain
`observed_binding: null`; this read opens no database and grants no effect permission.

Read `state(ctx).settings()` once. Use existing deployment/profile selection and
`cli_settings_report(configured)` to select canonical database/deployment fields. Do not reconstruct
Settings, relabel source metadata on a copied model or calculate effect-eligibility fingerprints
merely to explain configuration. `ctx.get_parameter_source("target")` describes CLI explicitness,
not final settings-field provenance. Source defaults/derived/mixed/unknown states remain honest.

Actual acquired identity remains StorageTarget from the existing owner. Where model/deployment
results already expose it, present the configured selection beside that acquired binding without
another acquisition. Use that actual operation in acceptance. No new settings providers, autoenv,
default_map, reload, class caches or native settings CLI resolver is selected. DMC-15 already owns
faithful acquisition and masking. Invocation resource callbacks are available for a proven shared
presentation lifetime; current transaction/lease scopes stay explicit.
[Settings owner](../../../python/corpus-structure/src/corpus_structure/settings.py),
[profile selection](../../../python/corpus-structure/src/corpus_structure/schema/model_deployment.py),
[Context API](https://typer.tiangolo.com/reference/context/).

## Integrated O08 checks and completion

Use focused-reference and selected-context delivery as real authoring examples rather than a fake
demonstration command. Extend existing fixtures/documented patterns. CliRunner checks exact selected
usage/options/examples, exclusion of unrelated sections, invalid paths, direct/managed equality,
mutually exclusive delivery flags and zero settings/kernel acquisition during reference reads.
Independent scalar and domain cases cover omitted/malformed/boundary/repeated values and raw test
forwarding. Context tests cover omitted versus explicit development, deployment unavailable,
masked endpoints, one factory call and configured versus acquired standing. Sequential invocations
must not retain prior state. Fresh processes are for actual entrypoint/stream/signal contracts.

Preserve independent invalid-input expectations; no new test framework or complete decorative
snapshot requirement. Targeted checks finish packages, not whole-series qualification. CLD-10 owns
the final union and assembled review. These planned checks are **not_run** during authoring.

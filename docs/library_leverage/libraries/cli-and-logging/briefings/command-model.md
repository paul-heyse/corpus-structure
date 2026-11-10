# Command modeling, discovery and invocation scope

**Discovery, 2026-11-10; benefits Proposed.** [Baseline and authority](../briefing.md).
Source observations describe the current dirty tree, not runtime qualification.

## Current foundation

[app.py](../../../../../python/corpus-structure/src/corpus_structure/cli/app.py) constructs an
explicit Typer application and installs command families through
[REGISTRY](../../../../../python/corpus-structure/src/corpus_structure/cli/__init__.py).
Its callback creates lazy `CliState`; settings are evaluated only when an operation asks for them.
[output.py](../../../../../python/corpus-structure/src/corpus_structure/cli/output.py) already
shares `JsonOpt`, settings access and typed emission. Help/completion need not acquire a database.
The registry imports command modules, so keeping operation imports lazy still matters.

The command reference already derives from this application:
[justfile](../../../../../justfile) `ci-reference` calls Typer's `utils docs`, exposed directly
or as a managed artifact by
[operations.command_reference](../../../../../python/corpus-structure/src/corpus_structure/cli/operations.py).
There is no reason to propose another handwritten command catalog merely to add documentation.

<a id="cli-01"></a>
## CLI-01 — Native declarations as an authoring surface

**Mechanisms.** Reusable `Annotated` metadata, Literal/Enum choices, repeated options and fixed
tuples, explicit names, custom `parser`, and named/unnamed `add_typer` composition. Consider
declaration-level path/range checks before per-command string conversion. The current
[testing adapter](../../../../../python/corpus-structure/src/corpus_structure/cli/testing.py)
already shares a bounded `ReportLimit` alias and uses Literals and repeated result operands;
these are working source examples of the native approach.

**Potential value.** Adding a command could involve its actual operation and metadata rather
than repeated option parsing, help and conversion decisions. A domain identifier parser could
deliver a meaningful type to an adapter while the domain owner retains lookup, permission and
cross-field validation. Named groups separate public namespaces from module boundaries;
unnamed merging could help authoring where a new namespace has no consumer.

**Counterconditions.** Typer interprets a restricted annotation grammar, not arbitrary nested
models. A parser that opens a database would move effects into parameter processing. Unnamed
composition loses the child's callback boundary, and command-name collisions need attention.
Existing explicit composition may already be simpler. Do not introduce generated signatures or
a command registry layered above the current registry without a concrete repeated decision.

**Next question.** For one actual next DMC command, which authoring decisions repeat and which
belong to its distinct operation? Compare native declarations with the current adapter, including
what custom code could disappear and what domain validation must remain.

Primary routes: [custom parsers](https://typer.tiangolo.com/tutorial/parameter-types/custom-types/),
[one file per command](https://typer.tiangolo.com/tutorial/one-file-per-command/),
[0.28.0 construction](https://github.com/fastapi/typer/blob/0.28.0/typer/main.py).
Selected-source inspection confirms callable parser/composition construction; arbitrary nested
schema binding and external Click plugin interoperability are not established by those APIs.

<a id="cli-02"></a>
## CLI-02 — Discover tasks through the existing command model

**Mechanisms.** Public `rich_help_panel`, short help, meaningful metavars, epilogs/examples,
default descriptions, choices and command suggestions; generated Markdown; `ctx.get_help`,
`get_usage` and `command_path`; dynamic completion using parsed context.

**Potential value.** Codex can choose the right operation from compact task-oriented descriptions
and then obtain precise operands without repeatedly searching source. Current test failure/retry/
coverage and model inspection journeys already provide commands and next actions; discoverability
could connect those existing steps more clearly. Completion is secondary for a token-vector caller,
but its metadata and local suggestions may still reveal useful available values.

**Counterconditions.** Panels can increase captured text without adding meaning. Generated help is
presentation, not a machine command schema. Application Console themes do not configure Typer's
separate help/error consoles. No public general console-injection surface was found in the selected
adapter; do not assume private `rich_utils` patching is necessary. Installed0.28.0
`rich_utils.py` constructs its own Console; help uses stdout and errors stderr.

**Next question.** Can Codex complete a representative unfamiliar inspection using only root/group
help, generated reference and owner-provided next actions? Identify the missing semantic information
before proposing more output. Any value suggestions must retain the architecture's local/read-only
completion boundary. The overview's raw-token completion discrepancy warrants source qualification
if a proposed completion needs more than partially parsed `ctx.params`.

Sources: [help metadata](https://typer.tiangolo.com/tutorial/commands/help/),
[completion](https://typer.tiangolo.com/tutorial/options-autocompletion/),
[tagged Rich adapter](https://github.com/fastapi/typer/blob/0.28.0/typer/rich_utils.py).

<a id="cli-03"></a>
## CLI-03 — Provenance and resources without another settings authority

**Mechanisms.** `get_parameter_source`, nullable Boolean pairs, `default_factory`, `default_map`,
explicit envvars and autoenv opt-outs; `ctx.obj`, namespaced `meta`, `with_resource`,
`call_on_close` and `result_callback`.

**Potential value.** Explicitly supplied false/default-valued options can remain distinguishable
from omission. An invocation-scoped context manager could simplify a real presentation or lease
lifetime shared across commands. Inspect these alongside the active DMC
[configuration companion](../../../../plans/domain-data-model/independent-consumers-and-configuration.md),
not as a second configuration-merging policy alongside `Settings`.

**Source contracts.** Installed0.28.0 `TyperGroup.invoke` processes the successful child's result
while its context remains entered; `Context.with_resource` uses the exit stack. Result callbacks
are not a universal finally hook for failure or cancellation. Parameter callbacks can run before
other parameters are populated; whole-input validation needs a point after the needed values exist.
Typer's parser consumes `--`: parsed extras alone cannot prove a separator was supplied. The raw
split in current `app.main` preserves information the downstream parser discards.

**Counterconditions.** Current explicit scopes can already express the lifetime clearly. Moving
leases, transactions or settings into callbacks may obscure effects and complicate help or tests.
`default_map` and environment support do not establish the application's intended source precedence.
Typer file types manage ordinary streams but do not discharge size bounds, archive custody or
coherent multi-artifact publication; retain those substantive contracts.

**Next question.** Which actual duplicated acquisition or explicitness check exists in the next
consumer? Would context-native ownership remove it while retaining lazy startup, all exit paths
and the existing settings report? Keep the current scope if the answer is no.

Sources: [context API](https://typer.tiangolo.com/reference/context/),
[Boolean grammar](https://typer.tiangolo.com/tutorial/parameter-types/bool/),
[0.28.0 group invocation](https://github.com/fastapi/typer/blob/0.28.0/typer/core.py),
[context engine](https://github.com/fastapi/typer/blob/0.28.0/typer/_click/core.py),
[parser](https://github.com/fastapi/typer/blob/0.28.0/typer/_click/parser.py).

## Handoff

These are authoring and usability leads, not diagnosed defects or accepted API changes. A useful
follow-up names one command/extension and its repeated decisions, then qualifies the specific
native contract. Preserve independent grammar expectations and exact stdout/stderr assertions;
direct Python calls cannot establish CLI conversion or callback behavior.

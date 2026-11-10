# Authoring commands and discovering their contracts

**Functional recommendations Proposed, 2026-11-10.** [Review and baseline](../cli-and-logging_2026-11-10.md).

<a id="O01"></a>
## O01 — Focused, exact command knowledge

Codex should be able to inspect one operation's grammar, examples and related domain explanation
without consuming the full recursive command reference. Current `operations.command_reference`
delivers the whole Typer-generated document; schema inspection/explanation already supplies domain
meaning separately. The installed schema-check help observation demonstrates why concise exact
flag names and descriptions matter even when parsing works correctly.

Recommend command-path selection in the existing reference route, coupled with complete ordinary
help metadata for the affected DMC command families. Use native help/short-help/epilog, explicit
metavars, choices and `rich_help_panel`; keep a plain readable representation where panel layout
abbreviates syntax. Link to existing release contract exploration for semantic meaning. An
illustrative future journey is: request the interpretations-author reference, read its exact
inputs and example, inspect/export its released input contract, then author a private interpretation.
This is proposed behavior; no new command spelling is asserted as installed.

Improving help alone is the smallest alternative; choose it when it suffices. Focused generated
reference adds useful selective access using existing delivery. A typed command inventory could
later serve agents, but its traversal must be qualified against Typer0.28; rendered help is not a
machine schema. Parser facts cannot infer domain applicability, effect authority or authorization.
A handwritten catalog or command DSL would create a competing authority and is not recommended.
Completion remains supplemental: local suggestions can help, but token-vector agents benefit more
from exact scoped references than shell installation. No remote acquisition in completion.

**Delivery evidence:** discover and invoke a representative unfamiliar DMC read/authoring journey
from focused help/reference and existing semantic readers; exact names/choices remain visible;
help does not build settings or acquire application resources. Preserve native suggestions and
explicit external names when modules/functions change.

Sources: [current command reference](../../../python/corpus-structure/src/corpus_structure/cli/operations.py),
[native generation recipe](../../../justfile),
[help](https://typer.tiangolo.com/tutorial/commands/help/),
[context diagnostics](../../libraries/python_introspection/typer.md#7-context-level-diagnostics-and-controlled-termination),
[generator0.28](https://github.com/fastapi/typer/blob/0.28.0/typer/cli.py).

<a id="O02"></a>
## O02 — Local typed command authoring

Recommend native `Annotated` aliases for genuinely shared meanings such as diagnostic bounds and
report selection, precise Literal/Enum choices, repeated options and pure custom parsers. Current
schema compile/check repeat diagnostic selectors; testing already demonstrates `ReportLimit`.
Research/interpretation commands are realistic next consumers. A new diagnostic read should need
its operation and unique selectors, with shared grammar/help supplied once where semantics agree.

Retain explicit registered groups and ordinary callables. Shared primitive types alone do not
justify a common alias. Numeric refusal differs from clamping; path conversion differs from opening
a resource; a command parser differs from cross-field domain validation. Put the latter in the
existing request/operation owner shared with MCP. Move orchestration shared by compile/check into
an ordinary operation if callback-to-callback reuse obscures the contract, rather than treating
`Context.invoke` as a new parser.

Compare current explicit signatures with the alias approach at one complete command addition.
Generated signatures, custom dispatch classes, case normalization and a second command registry
add coupling without a matching benefit here. Named composition preserves callbacks; unnamed
merging is useful only when a child namespace has no consumer and its callback is unnecessary.
Preserve the raw `ci test --` split: parsed extras lose separator provenance.

Typer file objects, `-`, lazy opening and atomic writes remain useful for a future simple stream
operation, but cannot replace current byte limits, authenticated reads or managed publication.
No prompt, password/confirmation flow, launcher, REPL or module runner improves the selected
unattended-agent workflows enough to recommend it now. Revisit for a real interactive interface,
not to obtain feature coverage.

**Migration and delivery:** change compatible consumers together, remove superseded conversions,
preserve domain validators and independent invalid-input expectations. Verify representative
missing, malformed, repeated and boundary inputs through the actual parser; substantively invalid
combinations still reach their owned validator. No universal adapter framework is required.

Sources: [schema adapters](../../../python/corpus-structure/src/corpus_structure/cli/schema.py),
[testing declarations](../../../python/corpus-structure/src/corpus_structure/cli/testing.py),
[custom parsers](https://typer.tiangolo.com/tutorial/parameter-types/custom-types/),
[composition/annotation constraints](../../libraries/python_introspection/typer.md#typer-0273--advanced-capabilities-and-compatibility-addendum),
[selected construction](https://github.com/fastapi/typer/blob/0.28.0/typer/main.py).

<a id="O03"></a>
## O03 — Explain the selected invocation without changing acquisition

Recommend a selected operation/profile projection of the actual settings snapshot: relevant
redacted resource selection, CLI input explicitness where meaningful, and source contributions.
The dirty DMC settings source already observes actual native init/environment inputs once; do not
reimplement that capability. Current `context_show` reports the general snapshot and selected
target label; its `observed_binding` is not an acquired target identity.

A useful future interaction explains the configured deployment destination before candidate work,
then compares that selection with the actual bound target reported by the operation. The first
read must say configured/unobserved rather than imply a successful connection or permission to
apply effects. Use the existing target-selection owner and `StorageTarget` for acquired identity.
Do not duplicate entire settings into every event or result.

Retaining the general report is adequate where no selected projection helps. An operation-specific
projection or concise context reference is preferable to a parallel precedence resolver.
`get_parameter_source` and tri-state Boolean pairs can preserve omission versus explicit override
when the operation needs that distinction; they do not establish final settings-field provenance.
`default_map`, autoenv, files/cloud secrets, caches and reload would change acquisition and are not
recommended for this target. Revisit for a workflow unavailable through the selected snapshot policy.

`with_resource`/`call_on_close` can own a real invocation-wide presentation lifetime. Keep explicit
transaction/lease scopes when clearer; result callbacks process normal returned values and are not
failure finalizers. No eager settings/database initialization during discovery.

**Delivery evidence:** explanation and execution use the same selected snapshot/rules; defaults,
explicit false values, aliases and masked endpoints remain honest; configured and acquired facts
are distinguishable. Integrate with DMC-15 instead of creating another settings report.

Sources: [settings](../../../python/corpus-structure/src/corpus_structure/settings.py),
[current context](../../../python/corpus-structure/src/corpus_structure/cli/operations.py),
[active configuration target](../../plans/domain-data-model/independent-consumers-and-configuration.md),
[Typer Context](https://typer.tiangolo.com/reference/context/).

<a id="O08"></a>
## O08 — An example-led command development and verification path

Recommend extending existing command examples/fixtures to demonstrate the complete native path:
typed inputs, domain call, owned result/refusal and focused assertions. This is a developer
capability for Codex, not a new scaffold engine. Reuse CliRunner for grammar, exact separate
streams and sequential invocation isolation; Rich capture/StringIO and controlled clocks for
presentation; structlog event capture and backend capture for different processing boundaries.

Ordinary `capture_logs` bypasses processors; post-processing capture is needed to test selected
redaction/serialization. Cached loggers and handlers can retain obsolete configuration/streams.
Qualify these lifetimes only when adopting O05. Independent expected fields/bytes challenge meaning;
do not derive every expectation from the same registry/validator. Fresh-process checks serve
actual entrypoint hooks, cancellation and terminal routing, not every layout variation.

Compared with copying full process journeys for each command, native focused checks keep authoring
local. Compared with testing callbacks directly, runner checks exercise the actual grammar. Both
have a place; no new test framework, snapshot approval process or test-audit engagement follows.

**Delivery evidence:** add one representative command with focused rejection/result checks, then
exercise affected shared behavior; verify two sequential invocations do not leak diagnostic context.
Preserve malformed inputs and useful independent expectations while deleting obsolete helper tests.

Sources: [existing fixtures](../../../python/corpus-structure/tests/conftest.py),
[runner0.28](https://github.com/fastapi/typer/blob/0.28.0/typer/testing.py),
[structlog testing26.1](https://www.structlog.org/en/26.1.0/testing.html),
[test-assessment guidance](../../design_review/design_principles/core/test-assessment.md).

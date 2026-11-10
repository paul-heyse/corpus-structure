# Configuration explanation and operation scope

**Proposed functional judgment, 2026-11-10.** Shared [baseline and recommendations](../domain-data-model_2026-11-10.md).
Source: [DDM-10](../../library_leverage/libraries/domain-data-model/briefings/portable-contracts-and-settings.md#ddm-10).

<a id="O12"></a>

## O12 — Faithful configuration explanation as acquisition grows

**Judgment: retain current acquisition; conditional extension for richer explanation.**
The operator already has `ci context show`, including target, redacted effective settings,
origins and recognized environment names. [settings.py](../../../python/corpus-structure/src/corpus_structure/settings.py)
owns constructor/environment acquisition and masking; [cli/operations.py](../../../python/corpus-structure/src/corpus_structure/cli/operations.py)
passes the entry-point snapshot to its report. D2 explicitly keeps process settings separate
from semantic defaults and method policy. This is an existing useful capability, not an empty slot.

**Useful resulting workflow.** If a future recognizer/deployment configuration introduces deeper
nesting, aliases or an additional explicit source, the operator can ask why a value won and
which supplied name had no effect. An agent can distinguish invalid acquisition from a valid
resource selection that was not propagated to the actual operation. The report should describe
the effective instance, not a default class's imagined environment names.

**Realization and alternatives.** Extend the existing report/source boundary with a small
PydanticBaseSettingsSource wrapper that observes contributions under its actual instance policy,
then applies validation-aware attribution and current redaction. Source `current_state` and
`settings_sources_data` can inform the merge explanation; they do not by themselves prove final
field provenance. Recursive field/alias traversal is an alternative for known-name enumeration.
`CliSettingsSource.env_var_names` is useful if that CLI source is itself selected, but constructing
a parser merely to inspect names can introduce an unrelated environment source and extra policy.
Keep the current small enumeration while its one-level namespace remains sufficient.

Native `settings_cached`/cache clearing is a competing lifetime mechanism, not a missing feature:
entry-point construction and passing already establish the required snapshot. Adding reload,
cloud secrets or configuration files introduces effects and failure semantics; choose those for
an actual operator workflow, never to increase provider coverage. Source precedence does not
skip lower-priority execution. Retain direnv's environment custody until an explicit source-policy
change is selected.

**Prerequisite and revisit.** A planned nested/aliased/source-specific configuration must defeat
the current report or name audit before this extension becomes recommended. If a resource is not
propagated, fix its actual consuming operation rather than adding a global cache or provider layer.
There is no evidence here of a new need for hot reload or a second CLI framework.

**Delivery cases if selected.** Conflicting constructor/environment values; nested JSON plus
field override; alias and deeper unknown name; selected development/deployment context; invalid
field distinct from missing source; credentials never present in explanation; an operation
actually consumes its selected snapshot. Exercise effects with the selected provider only.

**Rule impact.** More accurate read-only explanation fits current owners. Additional acquisition,
reload or source-policy semantics require an explicit D8/D9/settings decision; they cannot become
an ambient alternative authority for released domain meaning. Current snapshot behavior is the
preferred baseline until those premises change. Benefits are qualitative; no runtime probe ran.

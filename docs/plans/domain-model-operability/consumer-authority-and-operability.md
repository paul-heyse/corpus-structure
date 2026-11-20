# Consumer authority, support acquisition and operational inspection

**Status:** Proposed · 2026-11-20. The [coordinator](../domain-model-operability_2026-11-20.md)
owns readiness and disposition. This companion realizes review [O03][o03], [O04][o04] and the
selected-support part of [O08][o08]. Its acceptance scenarios are planned.

<a id="dmo-03"></a>
## DMO-03 · Derive typed consumer requirements

N40 applied current presentation authority to historical fit support. N41 asked an ordinary
policy issuer to supply a rich producer family. The bounded N42 fixes passed the actual rich
journey and 18 native controls. The admitted facts already distinguished issuer, historical
receipt, release grant and current effect authority. [Rich admission evidence][cause]

Declare required output role, CPU/publication witness, effect, family claim and disclosure under
the consuming input role. Derive available producer facts from its admitted declarations and
support relation. Preserve explicit `none`, an undetermined declaration and a known family as
separate states. Compile available/required correspondence once per admitted definitions and check
it in preparation and the real consumer. At use, verify original history using its cut and
receipt and apply live authorization to present reads, disclosures and effects. Keep the current
scope and epoch checks at that boundary. The ordinary authorization input can satisfy its declared
role while protected fit material remains protected. Reuse existing relations as the authority.
Consider a separately versioned relation only for policy that requires its own authorized editing
and release lifecycle and serves actual consumers. The tested command-class row mutation shows how
an admitted fact can change behavior without editing the generated guard. [Rich admission source][rich] ·
[Native selected validity](../../adr/0122-set-wise-support-validity.md)

**Library realization.** Preserve the current LinkML and linkml-runtime 1.12.1 declaration route.
Use schema classes, slots and enums at the existing owner for structural facts. Where a requirement
uses a modeled slot, resolve its effective per-class contract through `SchemaView.induced_slot` or
`class_induced_slots` on the prepared view, preserving inheritance and class-specific overrides.
Compile consumer relationships using the existing Python lowerer and typed
PostgreSQL program authoring. Where a shared shape family actually replaces duplicate dispatch,
Pydantic 2.14.1 `Field(discriminator=...)` selects a variant on a shared tag, and callable
`Discriminator` with `Tag` supports legacy array-shaped discriminants if that family warrants it.
Start with the CPU basis when its owner is touched. Keep semantic cross-field checks and SQL mirror
correspondence with their existing owners. Avoid migrating an unrelated family for style alone.
[LinkML SchemaView](../../libraries/data_model/linkml.md#5-python-runtime-and-programmatic-schema-manipulation) ·
[Pydantic discriminated unions](https://pydantic.dev/docs/validation/latest/concepts/unions/#discriminated-unions)

Migrate affected rich, policy and event consumers with the shared projection. Retire duplicate
selectors, producer-family conditionals and hand-carried requirement bundles after migration.
Verify issue, fit and scoring consumers through a positive mixed-family case and independent
wrong issuer, substituted support, wrong disclosure purpose, changed epoch and revoked grant cases.
The refusal identifies the consuming role and failed requirement.

<a id="dmo-04"></a>
## DMO-04 · Acquire only the support a cut requires

The bounded event journey published frame, fit and authorization, then exhausted the watchdog
at scorer attachment. The retained cumulative phase timings do not attribute the remaining cost
to a particular statement. Source shows full-frontier acquisition and whole-cut closure work,
with repeated validity over shared producers across roots and pages. Two bounded fixes already
share identical-cut indexes and avoid redundant same-release correspondence. [Event evidence][cause] ·
[Current index][read] · [Support closure][support]

**Decision slice.** Use one bounded private replay of the real event journey. Record setup,
selected support acquisition, publication and scorer attachment. Use PostgreSQL 18
`pg_stat_activity` wait fields for the selected backend and sample `pg_blocking_pids(pid)` when
waiting on locks. If significant work remains unexplained, inspect the narrow generated query
plan and nested call counts for that phase on the private target. Treat a wait sample as a point
observation. Use `EXPLAIN (ANALYZE, BUFFERS)` only where executing the selected statement is safe
on that target, with real effects isolated. Correct fixture amplification when setup dominates.
Change demonstrated lock or transaction scope for waits, preserving authorization and publication
fences. Address repeated traversal with sufficient cut-scoped support and shared computation over
identical premises. Use the observed earliest cause to order these changes. Keep one genuine
fixture through all stages. [PostgreSQL wait events](https://www.postgresql.org/docs/18/monitoring-stats.html#MONITORING-PG-STAT-ACTIVITY-VIEW) ·
[Blocking process API](https://www.postgresql.org/docs/18/functions-info.html) ·
[EXPLAIN options](https://www.postgresql.org/docs/18/sql-explain.html)

**Realization.** Reuse the existing pinned selected-read acquisition and native set-wise validity
program. Scope the projection before materializing support. Share material checks only under the
same cut and validity scope, carry root/member attribution and negative dependencies, and preserve
stable keyset continuation and byte limits. Distinct roots can reuse computation and still have
distinct explanations. Reacquire the current epoch, principal and purpose at live disclosure or
effect. SQLAlchemy Core 2.1.6 `Connection` and scoped results retain the existing reader lifecycle.
Client result streaming can bound client transfer but leaves the server's examined work unchanged.
Choose the physical SQL shape from the diagnostic and generate it through the native owner.
Rely on local sharing before adding cross-request retention. [Core result handling](../../libraries/postgresql/sqlalchemy.md#85-result-processing-and-streaming) ·
[Continuation semantics](../../adr/0141-serving-continuation-and-reuse.md)

Parse a selected-source event once within its owned input/read lifetime. Reuse immutable validated
values established at ingress after [DMO-06](json-contracts-and-settings.md#dmo-06) when this
removes redundant structural checks. Retire unscoped readback/frontier walks for migrated callers
and repeated same-premise acquisition. Start target tests with operation-scoped M1 and event reads.
Independently check exact scorer result, valid authority leaf, substituted input, counterfeit authored
parameters, protected frame/label refusal, changed epoch, distinct cuts, and keyset continuity.

<a id="dmo-07"></a>
## DMO-07 · Explain operator decisions through existing commands

Consume typed preparation facts from DMO-01, material/recovery decisions from DMO-02 and role and
scope explanations from DMO-03/04. Start the preparation diagnostic as soon as its owning facts are
available. Extend `ci model change inspect` with the first changed determinant and bounded scope.
Extend `ci schema explain-operation` with admitted producer/consumer role, family, effect and scoped
native fate. Extend `ci results inspect` with the first failed preparation, executable acquisition,
provider publication or scoped-read boundary, expected/actual basis and a typed next action. Use
observed native authority and managed result bindings. Show unavailable facts or conditional
readiness explicitly. Resolve configured target separately from acquired target. Keep passive
preview free of registration, work claims and provider startup. [Result inspection model][inspect] ·
[Managed CLI custody](../../adr/0069-cli-operations-custody.md)

**Library realization.** Typer 0.28.0 `Typer` sub-apps and `Context` use the existing command and
resolved profile state. Keep typed `Argument`/`Option` scope and result selectors at the commands.
Rich 15.0.0 `Console`, `Group` and `Table` render bounded human reports and route diagnostics to
stderr through the existing output owner. Machine output serializes the typed report separately
with its owning JSON serializer. Report the actual delivered byte count where a limit applies.
For generated SQL explanations, retain the pglast 8.7 `parse_sql` and `Visitor` path used by
`prepare_sql` and `sql_source_fact`. It can attribute syntax and statement kinds to original
source spans. Native binding, grants and execution standing require their actual owners' evidence.
Retire newly redundant ad hoc diagnostic extraction. Avoid a separate status registry, repeated
bulk scans and a second source of managed truth. [Typer command composition](../../libraries/python_introspection/typer.md#2-command-model-and-application-composition) ·
[Rich rendering boundary](../../libraries/python_introspection/rich.md#21-console-as-the-rendering-and-output-boundary) ·
[pglast syntax limits](../../libraries/postgresql/pglast.md#22-raw-syntax-versus-analyzed-sql)

**Acceptance.** Compare a native parity pass with an actual pre-provider acquisition refusal and
an actual publication with scoped readback. Check matching terminal/JSON facts, explicit missing
observations, bounded output, stable selection, and redaction for credentials and protected support.
Verify retained invocation/target binding and executable next action through the managed route.

[o03]: ../../functional_reviews/udm-operability-and-json_2026-11-20.md#O03
[o04]: ../../functional_reviews/udm-operability-and-json_2026-11-20.md#O04
[o08]: ../../functional_reviews/udm-operability-and-json_2026-11-20.md#O08
[cause]: ../../design_review/evidence/2026-11-20_udm-operability-causality/README.md
[rich]: ../../../python/corpus-structure/src/corpus_structure/semantic/rich_admission_native.py
[read]: ../../../python/corpus-structure/src/corpus_structure/semantic/demand_results.py#L342
[support]: ../../../python/corpus-structure/src/corpus_structure/semantic/support_edges.py#L332
[inspect]: ../../../python/corpus-structure/src/corpus_structure/cli/result_inspection.py#L47

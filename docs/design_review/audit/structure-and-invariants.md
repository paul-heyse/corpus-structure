# Structure and invariants

**Freshness:** findings retain their stated older evidence except where explicitly refreshed.
The [November 1 engagement refresh](README.md#unified-model-refresh)
narrows current reliance; inherited prose is not a newly verified current defect.

These findings concern distinctions, state, lifecycle, outcomes and enforcement: FP-05, DP-02,
DP-03, DP-05, DP-09, DP-12 and DP-19–DP-21. Baseline, scope and scenarios are in the
[README](README.md).

Paths are relative to `python/corpus-structure/src/corpus_structure/` unless they start with `rev/`
(`python/corpus-structure/semantic_alembic/versions/`), `domains/` or `docs/`.

Native enforcement of immutability and privileges has its home on the
[native integrity page](native-integrity.md).

<a id="da-012"></a>

## DA-012 — Operational sets have no go-forward authority

**Principles:** DP-02, DP-03 (G3), DP-05, DP-24, FP-04. **Subject:** implemented.

*Continues the 2026-10-28 finding.* The legacy system closed these sets with generated CHECKs. In
the go-forward model they are governed by the legacy vocabulary or by nothing.

### Diagnosis

- **Built from the legacy vocabulary.** `semantic/operations.py` builds `TaskUnitType`,
  `ObservationKind`, `ObservationOutcome`, `RunKind` and `MeasurementScope` from legacy `core.vocab`
  (`:28`, `:131`, `:739-923`). That module is generated from the legacy `model/core.yaml` and
  `system.yaml`. `SourceMeasurementScope` in `observations.yaml` duplicates `MeasurementScope`, and
  code reads the legacy one.
- **Untyped source reports.** In `observations.yaml`, `SourceObservation.family`, `outcome` and
  `confidence_source`, and the batch `outcome`, are untyped strings. `family` is filled from the
  legacy `draft.kind.value` (`semantic/observations.py:183, 193`).
- **Unconstrained physical columns.** `ops.task.stage`, `ops.task.unit_type`, `ops.method.family`,
  `tier`, `unit_type` and `confidence_source` are plain `TEXT` with no CHECK
  (`rev/semantic_0006_operations.sql:141-142`; `rev/semantic_0025_*.sql:1`).
  `guard_task_lifecycle` checks only document, rendition and segment units, and silently accepts
  any other unit type (`rev/semantic_0012_observation_inputs.sql:97-102`). The execution catalog
  types `TaskUnit.kind` as `text`.
- **Run statuses invented in reports.** `orchestrate/commands.py:321-327` and
  `orchestrate/semantic.py:309` report run statuses that are not states of the semantic run
  lifecycle:
  - `awaiting_agent` comes from legacy `RunStatus` (`core/vocab.py:382`);
  - `source_ready` exists in no enum anywhere.

  Task filters use legacy `TaskStatus` (`orchestrate/commands.py:13`; `cli/orchestrate.py:24`).
- **The agent tier has no go-forward declaration.** `MethodTier` and `ConfidenceSource` exist only
  in legacy `core.vocab` (`core/vocab.py:345-353, 656-668`). The native `'agent'` literal matches
  them only by spelling ([DA-052](boundaries-and-composition.md#da-052)).

### Consequence

- The meaning of tasks and source reports sits outside any release or execution-model version.
- An edit to the legacy model changes go-forward behaviour silently.
- A misspelled stage or unit type persists.
- Retiring `core/` removes the only authority these sets have.

### Counterevidence

Python boundaries use the StrEnums (`orchestrate/semantic.py:245, 273, 432`), and the 0025 equality
guard catches task/method mismatches for `semantic-2` releases.

**Evidence:** diagnosed from source.

**Related:** [DA-045](boundaries-and-composition.md#da-045) (legacy edge),
[DA-002](semantic-model-and-authority.md#da-002) (closed sets in the semantic model).

<a id="da-013"></a>

## DA-013 — Outcomes and refusals are prose, and declared outcome domains are not emitted

**Principles:** DP-02, DP-19, DP-21, FP-02, FP-04; G2, G7. **Subject:** implemented, judged against
the accepted completeness target: "discriminated result types per operation".

*Continues the 2026-10-28 finding.* Legacy keying was corrected with coded drops; the go-forward
code repeats the pattern.

### Diagnosis

**Declared outcome domains are not emitted.**
- `execution-model.yaml` declares a transaction outcome domain: applied, replay, conflict,
  stale_binding, run_closed, recompute_required, infrastructure_failure. It is mirrored by
  `semantic/outcomes.py:24-32` and checked only for parity (`semantic/contracts.py:600`).
- Execution emits only `applied | replay` (`semantic/operation_results.py:48-50`).
- `scientific_policy` declares `unsupported` (`execution-model.yaml:5505`), but unsupported operand
  shapes become `undecided` (`semantic/domain_operations.py:2825-2834`).
- One flat `ScientificOutcome` (`semantic/outcomes.py:11-22`) covers status, equivalence and rule
  findings. When several causes apply, the last cause overwrites `unknown`
  (`semantic/domain_operations.py:3271-3276`).
- Invariant `failure_code`s in the catalog are never emitted; native code raises 321 distinct prose
  messages under five SQLSTATEs ([DA-027](semantic-model-and-authority.md#da-027)).

**Exception classes merge causes.**
- `semantic/operations.py` maps the native SQLSTATEs P0004 and 55000 to one `OperationConflict`
  (`:89-92`, `:436-439`, `:946-951`, `:988-1028`).
- The same class carries provider absence, timeout, non-zero exit and `is_error`
  (`intervene/automated.py:64-210`), and unit failures (`orchestrate/semantic.py:298-299`).
- There are 55 prose `DomainOperationRefused` raises in `semantic/domain_operations.py` and one in
  `orchestrate/commands.py`. Only `IdentityResolutionConflict` carries a code.
- The same type serves four roles: whole-operation refusal, an undecided pair (caught and recorded
  as `reason=str(exc)`), an uncheckable condition, and admission failure.
- Coverage reasons are prose throughout `semantic/domain_operations.py:1126-1714`.

**Adapters flatten what remains.**
- `ci regenerate` catches `ValueError | KeyError | SQLAlchemyError` and prints
  `refused: <first line>` (`cli/regenerate.py:185-188`). That bucket also holds programming errors,
  lost connections, serialization failures (40001) from `select_project_result`, and the
  provider's stderr tail.
- `cli/orchestrate._refusals` follows the same pattern.
- The legacy `classify_error` (`core/db/store.py:108-121`) has no go-forward user.
- Across adapters:
  - `ci query` emits a JSON envelope whose code is an exception class name;
  - `ci golden` and `ci eval` print to stderr only, even with `--json` (`cli/golden.py:50-52`);
  - MCP tools raise `ToolError`, map to `SubmissionResult`, or let a raw `ToolFailure` through
    (`record_direction`, `intervene/semantic_server.py:464-479`);
  - MCP maps every `OperationConflict` to `not_open` with `task_open=False`, even when the cause is
    not a lost fence (`intervene/semantic_server.py:424-431`).

**The concrete failure.** The `claims` query's `object=` filter reads `typed_value.c.lexical`, a
column that does not exist (`serve/queries.py:88`). `AttributeError` is not among the handled
refusals (`cli/query.py:24-31`), so the user gets a traceback. The structural cause is that
consumer SQL names physical columns without checking them against the physical model, and that
failures have no shared taxonomy. No test passes `object`.

### Consequence

- No tool can choose among retry, fix and abandon without parsing prose. Run 3's guard refusal and
  a dropped socket produce the same CLI result: exit 1, "refused".
- The distinction between unsupported and inconclusive is lost.
- `explain` and coverage counts must parse prose to classify anything.

### Counterevidence

Native code raises stable SQLSTATEs and messages, so the information exists one layer down.
`IdentityResolutionConflict` is a structured, coded refusal, and source-to-semantic coverage
translation is declared (`semantic/outcomes.py:66-104`).

**Evidence:** diagnosed from source. The `object=` failure was confirmed by metadata introspection
(2026-10-29).

<a id="da-014"></a>

## DA-014 — Source coordinates have two grammar implementations that diverge, two locator encodings, and positional item keys consumed outside their owner

**Principles:** DP-01, DP-02, DP-03, DP-04; CI-03; G1, G2. **Subject:** implemented.

*Continues, with the subject reframed.* The 2026-10-28 finding concerned locator identity limits
stated more narrowly than a plan assumed. Statement identity is now scoped to release, realization
and rendition (`semantic/source_projection.py:19-29`), and D1 states the ordinal, so that premise
narrowed. What remains is source coordinates without a single representation.

### Diagnosis

- **Two grammar implementations that diverge.**
  - The locator grammar `page@kind[n]:prefix` is implemented natively in
    `ops.source_locator_segment` (`rev/semantic_0030_source_frames.sql:51-80`).
  - Go-forward Python resolves the same grammar through legacy `core.locators`
    (`semantic/source_frames.py:10`; `semantic/proposals.py:21`; `semantic/source_projection.py:11`).
  - Their whitespace normalization differs. **Probe P5** (2026-10-29): native
    `regexp_replace(…,'[[:space:]]+',' ')` under the database's `C.UTF-8` libc locale does not
    collapse NBSP, NEL or U+001C, while Python's `str.split()` does.
  - NBSP is common in HTML sources (`&nbsp;`). Python resolves agent anchors with `LocatorIndex`
    (`semantic/domain_operations.py:1243-1254`), and native code re-resolves them during publication
    (`ops.source_locator_segment`). The divergence therefore sits on the path from admission to
    publication, where the two can disagree on otherwise valid locators.
- **Two encodings in one column.**
  - Author markup writes `"rendition:<key>:span:<s>:<e>"` (`semantic/domain_operations.py:1199-1215`).
  - Agent claims and exclusions write canonical JSON (`:1396-1398`, `:1510-1517`, `:1770-1777`).
  - The structured coordinates live separately in `evidence_source`.
  - `serve/queries.py:118-131` filters with `e.c.locator == p.locator`, which matches neither
    encoding for a plain locator (suspected; not executed).
  - The source `find` query returns `LocatorIndex.generate` strings (`serve/queries.py:292`), which
    can never be fed back as a locator filter.
- **Positional item keys consumed outside their owner.** Occurrence item keys are positional
  (`"claims/" + index`). The evaluator re-derives that encoding to find admitted claims
  (`evaluate/semantic.py:706`; compare `semantic/domain_operations.py:1343, 1472`). Native guards
  match the item grammar by regex (`^claims/[0-9]+$`, `entities/%/attributes/%`;
  `rev/semantic_0030_source_frames.sql:184-262`).

### Consequence

- A change to how locators are normalized, encoded or itemized has to be made in Python, native SQL
  and the evaluator together, and nothing checks that they agree.
- A mismatch shows up as a refused valid locator, a filter that matches nothing, or an emptied
  prediction that looks like a zero grade.

**Evidence:** diagnosed from source; whitespace divergence measured by probe P5.

<a id="da-015"></a>

## DA-015 — Readers of M19 verdicts have no rule for selecting the current pass (inherited, not re-examined)

*Inherited from the audit at `024bb33` (2026-10-28). Applicability limit: M19 exists only in legacy
`consolidate/finalize.py`, off the go-forward production path. Semantic finalize seals one `final`
cut (`orchestrate/commands.py:270-281`). The subject lies outside this baseline's scope and was not
re-examined.*

**Principles:** DP-19, DP-05.

**Original diagnosis.** Each finalize pass would write one M19 task's refuted-only `verification`
rows, and no reader rule selected the current pass. With iterated passes, `explain` could have
shown a stale refutation.

<a id="da-016"></a>

## DA-016 — Escalation and confidence policy declarations compile without consumers

**Principles:** FP-05, DP-03, DP-08, DP-21; ADR-0018 (§B6). **Subject:** implemented.

*Continues the 2026-10-28 finding,* whose subject was confidence policy split between the policy
file and prose. The premise has changed: the go-forward path parses policy declarations but does
not consume most of them.

DESIGN §B6 and the pack `policies.yaml` comments declare escalation routing a phase-1 deferral. The
missing consumers are therefore not the defect in themselves. The defects are two:
- the policy compiler accepts chains and blocks that the runtime silently ignores;
- the propose context fabricates `None` and `False` for symbols the language declares.

### Diagnosis

- **Only one chain runs.** Only `PolicyChain.PROPOSE` is evaluated (`orchestrate/semantic.py:582`).
- **The rule context is mostly constant.** `target.*` and `budget.*` are always None, `judged_by`
  always returns False, `decision` and `confidence` return None, and `iteration` is 0 (`:635-648`).
  No metrics are passed (`:556`), although `orchestrate/policy.unit_language` exposes them.
- **Nothing is refused at compile time.** `compile_policy` compiles every chain
  (`orchestrate/policy.py:232-264`). `budgets`, `thresholds` and `confidence` parse but have no
  consumer.
- **Confidence has no producer.** The domain path produces no confidence, and
  `assessment.confidence` has no producer in `semantic/`, `orchestrate/semantic*` or
  `intervene/semantic*`.

### Consequence

- A policy that conditions on `target.max_confidence`, or uses the `escalate` chain, compiles and
  never fires.
- A "cheap model first, escalate on low confidence" policy is accepted and silently does nothing.
  Propose runs once at seal time (`orchestrate/semantic.py:300-306`), so agent outcomes can never
  condition a later tier.
- §B6's "routed by versioned policies over measurements" is realized only for propose, and not
  over measurements.

### Counterevidence

The recorded trigger (rule key, condition, classification, values; `orchestrate/semantic.py:662-674`)
realizes §B6's "records the rule and trigger values" clause.

**Evidence:** diagnosed from source.

<a id="da-017"></a>

## DA-017 — Retired at this baseline

*Was: "The `agent_reuse: by_unit` option overrides the reuse key without defining it" (suspected,
2026-10-28).*

Semantic runs refuse any reuse mode other than `full` (`orchestrate/semantic.py:74-77`). The CLI
still advertises `by_unit`; that remnant is recorded in
[DA-047](boundaries-and-composition.md#da-047). Verified 2026-10-29 at `ad4593f`. The earlier text
is in Git.

<a id="da-040"></a>

## DA-040 — Value admissibility is enforced late and partially at boundaries

**Principles:** DP-03 (G3), DP-02, DP-19, DP-20, DP-21; CI-02, CI-08. **Subject:** implemented.

### Diagnosis

The types that admit values at a boundary do not carry the contract a later stage enforces.
Admissible input therefore fails late, and with a coarse effect.

- **Establishment.**
  - `AgentClaim.establishment` ranges over `Establishment = {stated, derived, agent_asserted}`
    (`model/semantic/agent.yaml:70`; `core.yaml:595-599`). A probe on 2026-10-29 confirmed that the
    toy agent schema admits `derived`.
  - Nothing checks it at submission. `_project_cut` passes it through
    (`semantic/domain_operations.py:1473`), and `consolidation.assemble` raises a bare
    `ValueError` for anything other than stated or agent_asserted (`semantic/consolidation.py:231-234`).
  - The result is a failure of the whole `consolidate_cut`, not an item refusal or a coverage row.
  - The failure is deterministic, so the sealed run cannot finalize. End to end, this is suspected:
    not executed.
- **Finite numbers at the read boundary.**
  - `PreparedRelease.property_adapter` builds `TypeAdapter(field.rebuild_annotation())`, which drops
    the model's `allow_inf_nan=False` (`semantic/types.py:295-312`; `semantic/prepare.py:815`).
  - Probe: the field adapter accepts NaN, which the model rejects, and `QueryRow` serializes it as
    `"object": null`.
  - The writers validate through models and refuse non-finite values (`semantic/identity.py:57-59`),
    so the gap is latent. Its docstring promises a "strict output boundary … including its
    constraints".
- **Untrusted decimal lexicals expand without bound.**
  - Native `decimal_canonical` expands with `repeat` after an integer cast
    (`rev/semantic_0006_publication.sql:21-22`).
  - **Probe P6** (2026-10-29): `'1e400000000'` raises SQLSTATE XX000 "invalid memory alloc request
    size 3200000008", and `'1e2147483648'` raises 22003. Neither is the refusal class 23514.
  - Python's `_meaning`/`format(Decimal, "f")` would expand agent-proposed values first.
- **Same class at the source-projection boundary.**
  - `semantic/source_projection.py:86` refuses author-markup synthesis unless the statement
    relation's range is literally `SourceStatement`.
  - A cut-wide refusal fires when observations carry differing constant profiles
    (`semantic/domain_operations.py:1097-1098`).

### Consequence

- One admissible but unsupported value from an agent can block a whole run.
- A hostile or malformed numeric lexical becomes a memory-allocation failure instead of a refusal.
- The read boundary's promise of strict validation overstates what it enforces.

**Evidence:** diagnosed from source; boundary admission, NaN serialization and decimal expansion
observed by probe.

**Related:** [DA-026](semantic-model-and-authority.md#da-026) (the literal `SourceStatement` binding
behind the STATUS blocker is the native member of this class).

<a id="da-041"></a>

## DA-041 — Earlier missing lifecycle manifestation corrected

**Implemented, source-inspected 2026-11-01 at `1cb8e620`.**
`semantic/sql/execution_guards.sql:1–96` consumes release-projected task/run transitions,
checks attempts/holders and terminal receipts, requires structured failure diagnostics and guards
run sealing/terminalization. The earlier missing-outcome/lifecycle diagnosis no longer describes
these inspected paths. Package completion and actual qualification remain plan-owned. Unexamined
failure/recovery paths receive no new acceptance credit from this source inspection.

<a id="da-044"></a>

## DA-044 — Representatives and attributions are chosen by incidental ordering

**Principles:** DP-04, DP-05, DP-21, FP-04; A2. **Subject:** implemented.

### Diagnosis

Several choices that consumers see as meaning are made by whatever ordering the code happens to
use:
- **Entity attribute facts.**
  - Identity keys and labels take the evidence and establishment of the first claim that mentions
    the entity (`setdefault`, `semantic/domain_operations.py:1480-1485`, `:1532-1546`).
  - They get a fabricated asserted/positive qualification (`:1575-1587`). `AgentEntity` has no
    evidence of its own.
  - Attributes of declared but unreferenced entities are omitted, with no coverage row
    (`:1550-1551`).
- **Stored values.** A fact's stored value is the hash-minimum report representation
  (`semantic/consolidation.py:181-188`). Value ids hash the report representation, while fact ids
  hash meaning.
- **Display label.** The lexicographic minimum (`semantic/domain_operations.py:3366-3373`).
- **Equivalence representative.** The minimum by canonical bytes (`:3375-3378`;
  [DA-034](semantic-model-and-authority.md#da-034)).

### Consequence

- `explain` shows identity attributes supported by an unrelated quote.
- A fact's displayed value (`1.0` against `1.00`) can flip when a new report arrives.
- None of these choices is a declared policy that a consumer could understand or a reviewer could
  change.

**Evidence:** diagnosed from source.

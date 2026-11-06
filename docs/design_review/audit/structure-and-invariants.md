# Structure and invariants

**Implemented source inspected, 2026-11-03.** [Baseline](README.md#baseline).
Paths omit `python/corpus-structure/src/corpus_structure/`. Test/native qualification was not run.

<a id="da-012"></a>

## DA-012 — Operational declaration correspondence remains a bounded question

**Source-inspected 2026-11-05.** **FP-04/05, DP-01/02/03; unresolved, no new demonstrated mismatch.** Generated core vocabulary
and released observation/physical schemas remain distinct declaration contexts. Native completion
now checks actual result outcome/family/confidence domains against the released method definition
(`semantic/sql/native_task_completion.sql:21–51`). The previous implication that arbitrary
operational dimensions cross completion is removed. This refresh did not establish a concrete
conflicting accepted value or universally trace every generated-core enum into its native domain;
several contexts alone do not prove independent authority.

<a id="da-013"></a>

## DA-013 — Semantic inability now has a structured reason owner

**Source-inspected 2026-11-05.** `semantic/refusals.py:26–83` owns reason codes, operation/release/reference context and transport
fields. Actual comparison branches populate codes (`semantic/domain_operations.py:3007–3024,
3091–3093`). The earlier prose-only semantic-inability manifestation is removed. Some ordinary
validation errors remain prose; no consumer requiring an additional discriminator was demonstrated.

<a id="da-014"></a>

## DA-014 — Historical dual-HTML grammar diagnosis removed from current supported path

`semantic/source_frames.py:12–32` accepts NativeProposalFrame/PDF only;
`semantic/proposals.py:329–353` owns native typed addresses separately from HTML locators.
Positional claims/N interpretation remains in producer/native/evaluator paths. This coupling
alone is not an incompatible contract. DA-005 now records the shared evaluator address owner;
no fresh HTML whitespace defect or all-coordinate incompatibility is asserted.

<a id="da-015"></a>

## DA-015 — Historical M19 pass-selection observation not refreshed

Current finalization seals one final cut and refuses unfinished tasks
(`orchestrate/commands.py:369–382`). Legacy M19 internals were not re-audited and do not establish
a defect in current source execution. Historical evidence remains in Git.

<a id="da-016"></a>

## DA-016 — Policy applicability now rejects unrealized context

**Source-inspected 2026-11-04, M1-20261104-r4.** `orchestrate/policy.py` now declares executable
applicability and refuses unsupported chain/context inputs before production dispatch. The
previous syntactic-acceptance diagnosis is corrected at that boundary. M1 must consume the same
applicability owner; broader escalation remains an accepted target rather than fabricated context.

<a id="da-017"></a>

## DA-017 — Earlier by_unit refusal correction retained

Current semantic runs explicitly refuse by_unit (`orchestrate/semantic.py:91–95`).
DA-047 records the subsequent correction of its CLI advertisement.

<a id="da-040"></a>

## DA-040 — Source-establishment ingress now shares the released domain

**Source-inspected 2026-11-04, M1-20261104-r4.** Proposal/source assembly consume released
`source_establishments()` rather than accepting the full global vocabulary and failing only
inside aggregate assembly. Attribute-specific custody in `semantic/sql/closure.sql` checks the
actual owned source attribute and its evidence; shared display evidence cannot establish another
attribute. The inspected late-boundary cause is corrected. This dated correction alone did not establish M1 record support; current progressive native
publication custody is examined in native-integrity.md.

<a id="da-041"></a>

## DA-041 — Missing run/task lifecycle diagnosis remains corrected

Native guards enforce released transitions, attempt/holder identity, terminal digests, structured
failed-task errors and coherent sealing (`semantic/sql/execution_guards.sql:23–95`).
Source execution closes method owners and records terminal failure/cancellation
(`orchestrate/semantic.py:725–762,1164–1185`). DA-053 records the subsequent claim-lifetime correction.

<a id="da-044"></a>

## DA-044 — Attribute attribution and scientific representative policies corrected

**Source-inspected 2026-11-05.** Source attributes retain their own evidence and qualification
(`semantic/domain_operations.py:1734–1810`). Scientific representatives carry named
`min-fact-id-1` policy and component identity (`:3696–3718`). Lexical display choice
(`:3687–3694`) and minimum stored typed representation (`semantic/consolidation.py:173–179`)
remain deterministic choices, but do not by themselves establish semantic misattribution.
Original occurrence forms remain retained. The earlier first-claim attribution cause is removed.

<a id="da-053"></a>

## DA-053 — Outstanding claims now remain within renewal ownership

**Source-inspected 2026-11-05.** Orchestration claims only the first ready method (`orchestrate/semantic.py:585–598`), then
maintains that batch across custody preparation, execution and per-task durable settlement
(`:608–772`). `semantic/claim_lifetime.py:55–106` serializes renewal/completion and retires only
after commit or exact committed replay. Native completion fences competing attempts and recognizes
exact terminal replay (`semantic/sql/native_task_completion.sql:11–16`). This corrects the cited
cross-method waiting window; no new fault execution was performed.

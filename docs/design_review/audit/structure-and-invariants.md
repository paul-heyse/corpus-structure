# Structure and invariants

**Implemented source inspected, 2026-11-03.** [Baseline](README.md#baseline).
Paths omit `python/corpus-structure/src/corpus_structure/`. Test/native qualification was not run.

<a id="da-012"></a>

## DA-012 — Operational vocabulary crosses independent declaration contexts

**FP-04/05, DP-01/02/03; implemented, narrowed.** Semantic operations import generated core.vocab
(`semantic/operations.py:19–26`), generated from the older model/core.yaml and system.yaml
(`core/vocab.py:1–10`). Released observation family/outcome/confidence_source remain strings
(`model/semantic/observations.yaml:60–72,135–146`), as do physical method/task dimensions
(physical.yaml:1096–1110,1241–1246). Their linkage is not a single released closed-set contract.
This is not a claim that every operational set lacks authority: ReadinessOutcome now declares its
statuses, actual results validate dimensions (`orchestrate/semantic.py:736–739`), and native
execution guards enforce task/method equality and released lifecycle transitions.

<a id="da-013"></a>

## DA-013 — Operation-specific semantic reasons remain prose

**FP-05/06, DP-02/21; implemented, narrowed.** The old blanket failure-flattening diagnosis is
removed. `cli/failures.py:25–84`, semantic/refusals.py:84–156 and invariant_failures.py:108–137
preserve database cause/phase/effects, semantic/programming distinctions and release-bound invariant
identity. `operation_results.py:25–87` validates outcome dimensions.
Operation-specific refusals still often carry only messages (`semantic/domain_operations.py:2075–2077,2426–2547`);
scientific operand/precondition failures yield undecided with a prose reason (`:2801–2822`).
A tool needing those distinctions must interpret messages. Whether every consumer needs a distinct
unsupported versus undecided outcome remains unresolved; the entire taxonomy is not absent.

<a id="da-014"></a>

## DA-014 — Historical dual-HTML grammar diagnosis removed from current supported path

`semantic/source_frames.py:12–32` accepts NativeProposalFrame/PDF only;
`semantic/proposals.py:329–353` owns native typed addresses separately from HTML locators.
Positional claims/N interpretation remains in producer/native/evaluator paths. This coupling
alone is not an incompatible contract. DA-005 records the separately authored evaluator translation;
no fresh HTML whitespace defect or all-coordinate incompatibility is asserted.

<a id="da-015"></a>

## DA-015 — Historical M19 pass-selection observation not refreshed

Current finalization seals one final cut and refuses unfinished tasks
(`orchestrate/commands.py:369–382`). Legacy M19 internals were not re-audited and do not establish
a defect in current source execution. Historical evidence remains in Git.

<a id="da-016"></a>

## DA-016 — Accepted policy expressions can reference unrealized context

**FP-04/05, DP-03/08/15; implemented, scoped.** compile_policy accepts supplied chains
(`orchestrate/policy.py:236–268`), while production dispatch consumes PROPOSE
(`orchestrate/semantic.py:1022`). Its context supplies iteration=0, empty target/budget,
judged_by=False and decision/confidence=None (`:1065–1075`). Syntactically accepted policies
can therefore name meaningful inputs that have no producer on this path.
Routing trigger/classification/selection and scope-limit decisions are retained (`:1090–1107`);
unavailable classification is explicitly unknown (`:1050–1051`). D6 marks broader escalation as
proposed/deferred. Missing later-phase implementation is not itself the defect; accepting policies
without a declared applicability/refusal boundary is the concern.

<a id="da-017"></a>

## DA-017 — Earlier by_unit refusal correction retained

Current semantic runs explicitly refuse by_unit (`orchestrate/semantic.py:91–95`).
Its continued advertisement is a narrower surface issue under DA-047.

<a id="da-040"></a>

## DA-040 — Source establishment is admitted before an incompatible assembly boundary

**FP-05, DP-02/03/15; implemented.** AgentClaim uses global Establishment
(model/semantic/agent.yaml:93; core.yaml:595–599). Proposal reference checks do not narrow source
establishment (`semantic/proposals.py:573–688`); projection passes it into SourceItem
(`domain_operations.py:1490–1506`), then assembly rejects derived for the whole assembly
(`consolidation.py:242–246`). Upstream acceptance can thus cause late aggregate refusal.
The duplicate accepted-set authority is DA-002; this finding owns boundary placement/consequence.
Decimal normalization remains expansion-based (`value_codec.py:15–21`; sql/identity.sql:12–22),
but no new exploit was run. The prior NaN observation remains historical, not refreshed.
Effective statement relation binding now corrects the former literal-SourceStatement manifestation
(`source_projection.py:80–90`).

<a id="da-041"></a>

## DA-041 — Missing run/task lifecycle diagnosis remains corrected

Native guards enforce released transitions, attempt/holder identity, terminal digests, structured
failed-task errors and coherent sealing (`semantic/sql/execution_guards.sql:23–95`).
Source execution closes method owners and records terminal failure/cancellation
(`orchestrate/semantic.py:725–762,1164–1185`). DA-053 is a different claim-lifetime problem.

<a id="da-044"></a>

## DA-044 — Representative and attribution choices retain incidental ordering

**FP-04/A2, DP-04/08/11, CI-01/02; implemented.** The first eligible claim supplies entity
attribute evidence (`semantic/domain_operations.py:1507–1512,1580–1589`); synthesized attributes
receive asserted/positive qualification (`:1618–1620`). Entities without eligible evidence are
omitted. Stored fact representation uses the minimum value ID (`consolidation.py:192–201`),
display uses a lexical minimum (`domain_operations.py:3393–3402`), and scientific-equivalence
components retain their first accepted fact (`:3404–3407`). These choices affect representative
meaning/attribution without a declared consumer-facing policy for the choice.
Occurrence report representations are now separately retained (`consolidation.py:258–260`;
serve/read.py:82–92), so this does not claim that original source forms disappear globally.

<a id="da-053"></a>

## DA-053 — Source execution leaves outstanding claims outside renewal ownership

**Implemented source inspected, 2026-11-03. Principles:** FP-03/05/07, DP-19/20, G5.

`orchestrate/semantic.py:491–503` claims a batch for each scheduled method before executing
any. `:564–708` executes those batches serially, with maintained_claims scoped only to the
currently executing method (`:602`). Completion is deferred until every method has returned
(`:708–722`). A later method's claims wait without renewal, and an earlier method's claims stop
renewing before their completion is persisted. The lifecycle owner therefore covers inference,
not the full lifetime of outstanding claimed work.

Singleton groups also prepare custody/units before renewal (`:510–551,564–602`) and stop
renewal before per-task completion. The concrete cross-method grouping is adjacent compatible extract.math/normalize.formula
(`_source_step_groups`, `:1137–1161`), not arbitrary producer combinations. A large or skewed
math workload can keep outstanding work beyond the lease. Dependency admission
(`orchestrate/semantic.py:410–490`) normally delays normalization until extraction completes;
the first small batch does not claim both together. With more than one four-view batch, a fresh
extraction batch and now-ready normalization of earlier views can overlap in the outstanding
work list (math methods declare batch_size=4). This is the concrete cross-method scenario. `semantic/sql/execution_projection.sql:80–87`
permits another claimant to reclaim expired running tasks and increments their attempt.

Counterevidence bounds the consequence: maintained_claims renews its supplied claims and propagates
loss/cancellation; native complete_task checks holder/attempt (`semantic/sql/native_task_completion.sql:11–16`).
Expiry alone is not a completion refusal. A competing reclaim can cause duplicate computation
and fenced rejection of the first attempt; this is not evidence that expired work always fails,
or that stale attempts can publish corrupt results. No runtime failure or elapsed-time result
was observed. Static lifetime mismatch establishes the diagnosis; frequency and operational impact
remain unmeasured. This is independent of DA-041's earlier missing lifecycle-record diagnosis.

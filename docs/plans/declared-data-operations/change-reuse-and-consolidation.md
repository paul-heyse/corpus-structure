# Reuse, change determination and consolidation

**Proposed ·2026-11-12.** Develops DDO-09 under the
[coordinator](../declared-data-operations_2026-11-12.md). Consumes DDO-01–04 semantic identity,
binding/support and native admission; integrates with DDO-05–08 demands and producers.

## One mechanism for currentness and substitutability

Compile the typed producer/consumer dependency graph from declarations. Reuse existing normalized
member diffs as change facts; `semantic/operation_reporting.py:791–888` does not already provide
complete transitive data-operation impact. Use existing graph primitives for compile-time closure
and cycle diagnostics; do not persist a second workflow scheduler.

The recipe changes only for declared result-affecting meaning. Bindings include exact semantic
products, role/order/multiplicity, support requirements, analyzed context and closed population
witnesses. A refactor or execution placement change records new provenance without invalidating
unaffected results. Whole NativeProfile hashing must be replaced with the compiled semantic recipe
projection; execution admission still checks the complete requested/observed profile.

Plan binding resolution first; then find an admissible settled request/output under the same recipe,
semantic value binding and required support. Where the contract permits value substitution, attach
an explicit equivalent trusted support binding and avoid inference. Preserve the authentic original
derivation and any consumer requiring that episode/provider/independent evidence. Never interpret
multiple copies of one product as multiple evidence votes. Do not compare runtime/code bytes as a
reuse equality fence. Unknown semantic determinants refuse binding rather than silently use a broad
runtime fallback.

## Change and revocation algorithm

1. Pin old/new definition revisions, requested subject/discovery universe, selected result bindings
   and trust snapshot. Compare effective semantic contract/recipe/eligibility projections.
2. Find directly affected definitions and newly applicable or never-derived subjects using both
   old/new declared relations. Include population additions/removals, reordered input and optional
   presence/absence changes, not only rows with existing derivations.
3. Follow indexed reverse input/support lineage within relevant demand scope. Classify potential
   impact, awaiting upstream determination, incompatible/stale selected binding, revoked support,
   currently substitutable, inapplicable or unknown. Record reasons and exact reference witnesses.
4. Execute changed requested producers only through demand execution. When new value/support is
   substitutable, stop propagation. A transitive consumer is not proven stale merely because an
   upstream declaration changed.

Eligibility-only widening preserves prior recipes only when result scope, coverage, inputs, effects
and validity cannot change. Output schema equality alone does not prove compatibility. Cross-release
admission also checks original source/context/custody, outcome strength, selected alternatives,
purpose permissions and trust. Meaning-changing translation is a named admitted operation.

Revocation appends a scoped reason/selector under DDO-04's trust epoch protocol. It invalidates
required support paths, not raw shared content. Historical selections stay immutable. Another
support path is usable only when explicitly admitted by the consumer contract; recomputation after
revocation appends a new derivation generation. Retry, revocation and requested replicate remain
different operations. Serving an old snapshot is distinct from assessing its current trust.

## Consolidation is inside the total model

Declare consolidation/materialization as an operation over a cut selection: exact semantic products,
roles, support and coverage, selected alternatives, consolidation/admission policy and subject
universe. Retain per-run published knowledge, observations-versus-admitted-knowledge separation and
coherent visibility. Physical recomputation of a cut does not excuse undeclared inputs.

Store consumed binding identities in the cut result. A staleness request names its comparison target
release/demand/policy/trust snapshot; there is no implicit current/latest derivation. Reuse the same
change classification and reverse lineage, not a second consolidation-specific invalidation engine.
Future consumers can explain why one selected reading remains valid while another needs replacement.

## APIs, retirement and checks

Expose bounded typed change/currentness and revocation explanations through the same production owner
used by native reads, ci and MCP. Include IDs, reasons, examined scope, unknowns and continuations;
inspection does not schedule missing work or relabel historical facts. Model-backed projections can
use indexed PostgreSQL joins; hydrate bodies only for requested details.

Remove task_dependency_scope, valid_reuse runtime equality, copied reused status, freshness salts,
hand-maintained determinant lists and stale-cut classifiers only after their replacements and
consumers work. Preserve independent controls for legitimate nonreuse, source custody and incomplete
coverage. Test same declaration/new executable, one semantic parameter change, equal producer output,
support-only changes, newly optional input, deletion/absence witness, eligibility widening and rival
trusted/revoked support. Expected affected subjects and stop points must be independently specified.


Support substitution must independently establish that the authentic producing execution remains
trusted for its own recipe/runtime/behavior. Alternative upstream evidence cannot rehabilitate an
execution directly revoked for its own defect. Such a product needs a separate trusted producing
derivation (or recomputation), even when its bytes match. Preserve this refusal as an independent
native/admission test, alongside allowed substitution of equal-value upstream support.

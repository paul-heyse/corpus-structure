# Typed relations, revision comparison and supported dossiers

> Current authority,2026-11-06: ADR-0068 selects shared-development qualification; ADR-0067 selects current-only execution.
> Use the SAME120 Grinstead–Snell physical pages191–310 for development, regression, fitting and
> assessment. No new sources, separate calibration population or independent-origin readiness gate
> is required. In-sample fitting is diagnostic; preserve numerical validity, exact source evidence
> and source-only reference judgments. Current test-resolution is complete. Remove replaced
> production contracts and historical decoder paths across ALL remaining WCE, retaining controls
> only on current contracts. The coordinator owns execution status and final-source qualification.


**Implemented selected target; execution reconciliation,2026-11-06.** This companion develops WCE06–WCE07.
The [WCE coordinator](../witnessed-corpus-enrichment_2026-11-05.md) solely owns package state,
finding disposition, evidence, rule changes and completion. This page develops behavior and
implementation dependencies; planned verification does not represent passing evidence.

Consume the integrated [production-enrichment review](../../design_review/reviews/design_review_production-enrichment-improvements_2026-11-05.md)
at `6487c486` (542 lines), especially §§3–4.4, 7–12 and F04/F05, with F01–F03 inputs. The
[recommendation audit](../../design_review/reviews/audits/design_review_production-enrichment-improvements_2026-11-05_audit.md)
supplies rationale for the integrated revision. All RC01–RC06 were operator-accepted for planning
on 2026-11-05; WCE00 routes the changed authorities before dependent implementation. RC03 adds
typed/revision comparison alongside the lexical baseline; RC04 selects supported-facet display
as a bounded projection, without strengthening dossier membership admission. The separate
test-audit resolution plan is an assumed-ready target foundation, not a repair package here or
a claim about actual completed checks.

## Intended result and foundation assessment

The operation should answer a concrete source question by composing qualified pieces: which unit
and note govern this table value; what a formula symbol denotes in this local scope; which rule's
triggering interval changed; or which supported dossier facets are represented within a display
budget. A syntactic parse, graph path, lexical difference or representative set does not answer
all of those questions on its own.

| Current owner at `6487c486` | Implemented baseline observed 2026-11-05 | Required change |
|---|---|---|
| [Contribution adapter](../../../python/corpus-structure/src/corpus_structure/methods/contribution_adapter.py) and [M1 source](../../../python/corpus-structure/src/corpus_structure/methods/m1_source.py) | Retain native table/formula groups and bounded formula syntax with explicit input policy. | Consume located syntax/geometry in scoped relation operations; retain their meaning and source mapping. |
| [Structural semantics](../../../python/corpus-structure/src/corpus_structure/semantic/structural_products.py) | `ClauseField` retains lexical value/evidence; comparison has finite lexical outcomes. Dossier members carry relation references and producer qualification metadata. | Add versioned typed premises, independent applicability axis and qualified automatic membership/facet projection. |
| [Structural methods](../../../python/corpus-structure/src/corpus_structure/methods/structural_products.py) | `compare_clauses` returns incompatible-applicability for scope/version mismatch; `assemble_dossier` selects source-order representatives per group and always retains mandatory roles. | Preserve that control meaning. Add typed comparison and greedy marginal supported-facet selection through separate versioned operations. |
| [Scientific evidence](../../../python/corpus-structure/src/corpus_structure/semantic/scientific_evidence.py) | `canonical_operand` uses Decimal and retains unit/basis; interval closure and `canonical_restriction` comparator direction have production ownership. | Reuse/extract pure production semantics for typed comparison; do not copy protected evaluator models. |
| [Structural admission](../../../python/corpus-structure/src/corpus_structure/semantic/structural_admission.py), native [products](../../../python/corpus-structure/src/corpus_structure/semantic/sql/structural_products.sql) and [publication](../../../python/corpus-structure/src/corpus_structure/semantic/sql/structural_publication.sql) | Common source-resolved statement/publication custody; dossier statement excludes representative display and says `membership_assembly_not_member_truth`. | Keep that admission boundary. Typed comparison needs its exact independently judged statement/policy; display cannot change admitted membership. |
| [Serving](../../../python/corpus-structure/src/corpus_structure/serve/structural_products.py) | Completed-cut bounded reports and optional independent publication support use a common read route. | Extend new variants, typed premises and representation/omission facets while retaining exact original source/runtime pin closure under current readers. |

The review's `scientific_evidence.py:845–931` reference resolves to `semantic/scientific_evidence.py`,
not `methods/`. Implementation should follow that actual production owner. Architectural authority
is [D1](../../design/D1-knowledge-representation.md),
[D5](../../design/D5-consolidation-identity-confidence.md) and
[D8](../../design/D8-agent-and-query-interfaces.md), including
[ADR-0065](../../adr/0065-cross-source-structural-products.md). WCE00/WCE01 schedule changed
decisions prospectively; frozen source references and old report semantics remain intact.

**Proposed foundation assessment.** Existing finite reports, source-contribution custody, scientific
kernels, native eligibility and bounded reads provide the needed homes. FP-04/05 and CI-02/04
require making scope, unsupported conversion and inspection coverage explicit rather than allowing
proximity or missing results to imply truth. FP-03 favors typed joins and shared pure transformations
over another inference service. FP-02 requires versioned lexical/typed/applicability meanings and
current-only readers. FP-07/A4 favors source-local indexed joins, prepared grammars, bounded
formula products and normalized-premise reuse; semantic substructure does not need a lifecycle per
node. This is a focused assessment, not a new formal review or measured capacity claim.

Keeping supplied lexical fields and source-order display remains an inexpensive, honest control.
It cannot supply typed threshold consequences or supported-facet coverage. A universal parser,
graph engine or exact optimizer would add machinery before the missing semantic premise exists.
Those alternatives are unselected. Conditional algorithms below have specific reopening triggers.

## Contracts consumed and produced

The [semantic/native companion](semantic-contracts-publication-and-consumers.md) owns WCE00/WCE01/WCE11;
the [source/assessment companion](assessment-source-expansion-and-qualification.md) owns WCE02/WCE12.
Early source/question/rubric readiness precedes producers; later output-first freezing follows
their actual products and is not an input-label prerequisite for production.

WCE01 supplies executable released types, operation versions, scientific/native-policy boundaries
and source/result compatibility. WCE02 supplies independently frozen source opportunities,
operation questions and appropriate reference groups. [WCE03–WCE05](witness-and-parser-composition.md)
supply named located candidates, witnessed definitions, actual mentions and question-relative
compatible relationships. Readiness requires a working producer/consumer slice, not only accepted
interface prose. WCE06 can start source parsing against WCE01 while awaiting WCE05's complete
relationship consumer, but cannot declare joined/native behavior complete before that integration.

| Product | Minimum interpretation contract |
|---|---|
| Typed premise | Exact lexical input and original source pieces; typed value and unit/basis; operation/grammar/release revision; assumptions and unresolved interpretation. |
| Scoped attachment | Participant identities and roles, direction, kind, source/region/scope/version, basis and exact dependencies; selected versus unresolved alternatives and coverage. |
| Formula substructure | Consumed syntax node/use and declaration candidates; parsed-input coordinates plus original-source mapping; syntax and denotation are separate judgments. |
| Comparison | Left/right premise identities, independent lexical delta, typed delta and applicability; transformation identity, assumptions, precision and explicit unsupported outcomes. |
| Dossier membership | Root/sense/question, qualified relation dependencies, all selected members, mandatory flags/roles and completeness relative to frozen selection. |
| Dossier representation | Membership revision, supported facet evidence, mandatory selection, display budget, deterministic algorithm/version, selected subset and omitted/continued population. |

Preserve each original source project/run/cut/release/result revision, native product/content,
projection/recipe digests and coordinate version. A cross-source analysis project does not become
the source owner. Reader continuations and detached export must retain producing semantic/runtime
identity and the evidence closure behind these products. Components use typed versioned variants
in existing SourceContribution/Structural products and can be batched under the existing
task/publication lifecycle; the table does not prescribe new physical stores. Private production,
protected assessment and public admission remain separate immutable relations.

## WCE06 — Table, symbol and typed revision composition

**Contribution:** F04 and typed F03 composition; supplies real ambiguity to F06/WCE08.
**Delivers:** source-local typed attachments and comparisons, their qualified derivations and
native/read integration. RC05 now requires statistics qualification and domain-neutral extension scenarios;
it does not establish a second fully released corpus.

### Table relationships and coverage

Compose actual cell occurrences with their row labels, nested header band/property, applicable
unit, note/exception and value role. Restrict candidate joins by source/table/region, parent paths,
marker evidence and released role/scope constraints before hydrating content. A nested unit governs
its band, not every visually adjacent cell. A note may validly govern several rows; no one-to-one
assignment is imposed on notes or units. Geometry can exclude a source-established impossibility;
uncertain geometry proposes a candidate rather than proving applicability.

Retain direct participant evidence and the joined chain, including which observations are shared.
An inferred unit agreeing with another interpretation of the same header is not independent
confirmation. WCE08 owns any declared probabilistic policy for that ambiguity; deterministic
composition must not secretly choose the preferred interpretation as a hard premise. Distinguish
forced under exhaustive premises, preferred among the retained candidates and unresolved. Declare
the inspected support before a negative or exhaustive conclusion.

The source-opportunity account retains unstated/not-applicable facets, uninspected regions,
inspection failures, missed positive attachments and wrong emitted edges separately. More private
proposals or graph density do not establish added correct structure. Only admitted premises and
rules may feed the existing finite inference owner. Successful source-bound attachments can
remain useful private or narrowly admitted products without complete record success.

### Formula syntax and contextual symbol meaning

Lower consumed Lark syntax into existing immutable located products, so a formula use can link to
a local declaration and then to a scoped parameter/concept. The same glyph in adjacent examples
remains a distinct occurrence and may have another meaning. Preserve bound/free or other
domain-relevant role distinctions only where the selected operation declares them; glyph equality
does not establish denotation. Keep alternatives when a declaration or parent convention is unclear.

Maintain parsed-input to original-source mappings. A normalized/reconstructed formula may have
faithful syntax while lacking an exact original subspan; retain formula-level evidence and explicit
mapping limits rather than assigning normalized offsets to the source. The selected `recognized_only`
versus `captured_native_text` input policy and recognition availability stay visible. A successful
tree is syntax evidence, not a semantic assessment of the historical four unassessed contextual
symbol roles. WCE02 supplies a frozen meaning rubric and independent expected bindings for those
roles, plus authentic normal-density/standard-normal/parameterization distinctions absent from the
prior selected passages.

Consume only syntax nodes useful for symbol/declaration/condition products; no task, receipt,
table or publication lifecycle per AST node. Repeated visits to a shared subtree cannot become
independent evidence. Bounded declaration lookups honor source section/example scope; no full-book
graph walk is required for a local formula question.

### Procedure relationships

As a domain-neutral extension scenario, compose step → controlled artifact → prerequisite/order
using witnessed actor/action/object/modality and condition/exception roles. Preserve prescribed,
described and example behavior. A passive surface order must not reverse actor and object.
An artifact identifier denotes a scoped artifact/version; a dependency edge is not identity.
An inferred prerequisite needs its admitted rule and direct premises; mere textual order remains
a proposal. These cases exercise the same typed relationship contract rather than introduce a
general workflow engine or simultaneous multi-pack runtime. Use one producing domain per operation
and explicit cross-source comparison projections where needed.

### Source-bound parsing and numerical semantics

Select Lark `==1.3.1` small routed grammars for comparator/interval/unit/identifier questions.
Prepare `Lark(..., parser="lalr", lexer="contextual", propagate_positions=True)` for grammatical
consumers, with a declared start rule and grammar revision. Where the required evidence is merely
lexical, use `Lark(..., parser=None, lexer="basic")` and `lex(..., dont_ignore=True)` instead.
Do not require a parse tree to retain a comparator lexeme or a unit token. Grammar route selection
comes from the operation/field contract, not from whichever grammar happens to accept first.

Use `TextSlice(buffer, start, end)` only with supported basic/contextual lexers and an authenticated
captured-text buffer. Its indices belong to that buffer; normalization or reconstructed formula
input still requires an explicit mapping. TextSlice avoids substring allocation but lexical-state
initialization may scan the prefix. Choose bounded scopes and prepare parsers once per grammar/
recipe lifetime; no constant-time incremental claim or custom line-counter cache is selected.

Keep original lexeme and typed value together. `Token.update` and `Token.new_borrow_pos` can preserve
positions during local normalization, but lower consumed token/node positions to owned immutable
products before copies, transforms or persistence. Ordinary token pickle/deepcopy can lose ending
positions; `Tree.copy` is shallow and does not establish independent preserved metadata. Grammar
priority or forest ranking must not resolve domain ambiguity silently. General Earley forest
processing remains conditional on a real ambiguous grammar consumer; `Lark.scan` is not available
in pinned 1.3.1 and is not a selected mechanism.

Primary versioned sources: [classes/TextSlice/lex](https://github.com/lark-parser/lark/blob/1.3.1/docs/classes.rst),
[lexer/token behavior](https://github.com/lark-parser/lark/blob/1.3.1/lark/lexer.py),
[tree copy behavior](https://github.com/lark-parser/lark/blob/1.3.1/lark/tree.py), and
[parser configuration](https://github.com/lark-parser/lark/blob/1.3.1/lark/lark.py).
The [Lark guide addendum §§2–5](../../libraries/parsing/lark.md) is read-only capability guidance.
Context7 `/lark-parser/lark/1.3.1` was consulted on 2026-11-05. These are Interface-checked
mechanisms; no new parsing/provider efficacy has been Tested by plan authoring.

Use production `semantic/scientific_evidence.py` and its underlying evidence kernel for unit/basis,
interval closure, comparator direction and qualified mathematical comparisons. If comparator/
condition semantics currently usable only through an evaluator need a pure reusable function,
move that function to its production owner and make both consumers call it. Protected labels,
reference models and expected outcomes stay evaluator-side. Shared pure semantics do not justify
expected answers generated by the same transformation under test.

### Typed comparison behavior

Introduce a new operation/schema version alongside existing `qualified_comparison` lexical
reports. Do not change the meaning of `compare_clauses` v1 or make historical rows decode as new
typed conclusions. For each pair retain three independent outputs:

| Axis | Required result | Refusal/uncertainty boundary |
|---|---|---|
| Lexical delta | Original field values and literal same/different/unknown result. | Missing fields stay unknown; a typed equivalence does not erase lexical change. |
| Typed semantic delta | Typed premises, explicit transformation and exact difference/equivalence or unsupported/ambiguous result. | Unknown unit/basis, non-finite values, unsupported conversion or parse ambiguity withhold the stronger result. |
| Applicability | Co-applicable, successive revisions, differently scoped or unestablished, with source premises. | Different version alone does not prevent comparison; a comparison alone does not select the governing rule. |

For the accepted example, source-supported `x > 25000` and `x > 50000` with compatible actor,
currency, object/action, conditions and exception premises yield the change in this rule's triggering
region `(25000, 50000]`. Preserve old/new ordering, strict versus inclusive endpoints, units and
transformation. This says neither that every approval requirement disappears in the band nor that
an operator should adopt the later rule. An unknown or changed exception can permit a threshold
delta while withholding a governed-treatment conclusion. An unknown shared actor/currency similarly
limits applicability rather than disappearing behind a numeric result.

Use exact Decimal/rational arithmetic for supported finite threshold/interval transformations and
declare precision/conversion behavior. Do not cast source thresholds to binary float just because
an optimizer accepts arrays. Unit conversion requires an owned compatible conversion, retained
input units/basis and exact or declared precision; unsupported units stay unsupported. Keep negative
and infinite endpoint cases honest under the actual supported grammar/type contract. Scientific
kernel equivalence under stated assumptions does not establish source truth or policy authority.

Where cross-revision clause alignment needs a declared one-to-one counterpart population, SciPy
`==1.18.1` `scipy.optimize.linear_sum_assignment` is a conditional mechanism, with explicit unmatched
choices. [Primary API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html).
Independent split/merged clauses remain representable outside that assumption. It is not selected
for table notes or many-target definitions. Freeze population and cost meaning before comparing
against the simple nominated-pair route; dependency/API availability does not establish semantic fit.

### Integration, recovery and verification

Implement released meanings → domain parsing/join/comparison → contribution/structural lowering →
native source/derivation validation → exact admission → ordinary read/export as one package.
Likely edit surfaces are the source/contribution and structural methods, structural semantic/released
definitions, scientific production owner, prospective migrations and structural SQL, preparation,
`serve/structural_products.py`, named queries, `cli/structure.py`, MCP and review bundle. WCE01
coordinates shared release/native edits; WCE06 owns adoption of its new semantics in those consumers.

Validate each distinct source closure once per coherent batch, share located/normalized premises,
and hydrate bounded join candidates after source/role filtering. Keep CPU parsing and mathematical
work outside long database transactions; recheck current source/selection/dependency premises
before atomic publication. Preserve cancellation and failed attempts. Do not partially publish a
derived consequence whose required premise failed. Existing source/native publication guard
identities remain in force; this plan establishes no safely removable assurance check.

Independent known answers cover nested header scope, one note governing several rows, unstated
versus missed units, repeated symbol glyphs with different local declarations, condition attachment,
passive role reversal, `>`/`>=` boundary differences, unit/basis mismatch, reversed revision order,
unknown/changed exceptions and explicit unsupported parses. Check exact original substrings and
node-to-source mappings after lowering/serialization. Test lexical/typed/applicability outputs
separately. Derive the threshold example's expected interval independently, not by calling the
same comparator twice.

Evaluate A alone, B alone and A+B on identical fixed endpoints before automatic discovery, using
independent source-opportunity truth. Record corrected, preserved, lost, spurious and unresolved
cases; do not count overlapping predictions as distinct facts. Trace at least one new synthesis
through every direct premise and its transformation. Native negatives include foreign/missing
premises, substituted source version, invalid derivation, unsupported component admission used as
whole-statement support and changed current selection. Exact replay and Reader/CLI/MCP/detached
export preserve both old lexical reports and the new qualified typed outputs. Full qualification
remains WCE12, not a per-slice campaign.

## WCE07 — Qualified membership and supported-facet dossier display

**Contribution:** F05, consuming qualified F01–F04 products. **Consumes:** WCE01 dossier/publication
contracts, WCE02 dossier questions, WCE04/WCE05 supported relationships and applicable WCE06 typed
products. **Delivers:** automatic qualified membership plus a bounded, explainable supported-facet
projection through native and ordinary consumers.

### Membership before representation

Given a root concept or provisional sense and frozen source selection, assemble members only through
qualified upstream relationships carrying actual passage/source evidence. Preserve member role,
sense, scope/version and predecessor product/assessment standing. An upstream product sharing the
input inventory is insufficient: the dependency must actually support that physical citation in
the required role. Do not accept producer-supplied `independently_supported` metadata as native
authority. Preserve proposed, ambiguous, rejected and unsupported material in its proper private
inspection context rather than allowing it to contribute to supported coverage.

Completeness remains relative to the frozen selected population. A selection missing normal-density
material cannot become complete by optimizing a dossier of available passages. Display filtering
does not shrink the membership universe or erase a conflict. Preserve exceptions, conflicts and
revisions as mandatory members; retain unresolved sense/open questions with explicit standing.
If a membership relation changes, invalidate its dependent assembly; an unrelated inventory vector
change alone should not renew a semantically unchanged claim without its declared dependency.

Keep the existing common admission route and exact membership statement. RC04 selects display
projection only: coverage scores, representative identities and algorithm budgets do not become
member truth or strengthen `membership_assembly_not_member_truth`. A future public claim of
supported-facet completeness would need its own independently assessed question/policy and is
unselected here. No automatic activation or identity merge follows from a dossier root.

### Greedy supported-facet selection

Define supported facets from qualified member products and the dossier question: term/definition,
scope/parameterization, applicable usage, relationship, variant, condition, exception, revision and
conflict as relevant. Facet identity binds its meaning/scope, not just section label or lexical
string. Evidence establishes each member-to-facet association before the display algorithm sees it.
An embedding similarity can reduce redundancy or break a tie; it cannot establish membership,
semantic support or an absent facet.

Select mandatory members first. For remaining display capacity use deterministic greedy marginal
supported-facet coverage, with a declared stable tie-break such as original source order and member
identity. If the declared budget is bytes or a weighted display cost, compute marginal gain against
that same cost; do not compare a member-count greedy result to a byte-budget baseline. State the
chosen budget dimension and algorithm version in the representation contract. Return selected
members, represented supported facets, unresolved/missing facets, budget usage and omitted members/
continuation. Preserve a complete membership handle even when the first display page is small.

When mandatory content exceeds the display budget, return explicit overflow with bounded pages
and continuation/omissions, retaining all mandatory membership and the exact reason for display
incompleteness. Do not drop the conflict, silently exceed response limits or claim complete display.
The continuation pins membership, selection policy, facet evidence revision and producing source/
runtime context, so later pages cannot select against another dossier revision.

Retain `assemble_dossier` source-order representatives as the equal-budget control. Compare identical
membership, supported facets, mandatory policy and budget; a larger dossier or changed membership
is not evidence for the selection algorithm. The greedy procedure is a simple reproducible heuristic;
no optimality claim follows. Do not introduce a second generic optimizer abstraction for one display
operation.

### Conditional exact optimization

SciPy `==1.18.1` `scipy.optimize.milp` with `Bounds`/`LinearConstraint` remains conditional on actual
interacting constraints that make greedy selection materially inadequate, such as joint category/
source coverage and mutually restricted representative choices. [Primary MILP API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html).
If triggered, formulate binary member/facet coverage, force mandatory selection, and compare to
greedy at the same budget. Declare objective/constraint meanings and solver limits. A limited
feasible incumbent can be reported as such; timeout or a nonzero gap does not establish optimality.
An infeasible mandatory budget remains explicit overflow, not permission to remove mandatory facts.

This uses the already pinned numerical dependency; exact version availability and an optimizer call
do not establish a useful product improvement. Greedy is the selected initial route, and no MILP
experiment or benchmark is required merely to demonstrate diligence. Trigger execution only when
an independently judged dossier question exposes the interacting-constraint need.

### Native/read migration and verification

Extend structural dossier producer/types and the released projection definition, preserving old
`DossierProduct` semantics through explicit reader versions. Native membership/eligibility must
bind the exact upstream selected products, original source citations and current selection.
Representation uses the same membership snapshot but cannot alter its public statement or admit
unsupported member roles. Keep short atomic publication after private assembly/selection; a
cancelled display computation must not mutate membership or leave half a new assertion visible.

Migrate `serve/structural_products.py`, `structural_dossiers`, `ci structure list`, MCP and review/
detached export to distinguish complete selected membership, selected representation, omitted/
continued members, mandatory overflow and separate publication support. Budget checks account
for hydrated evidence and envelope bytes. Avoid constructing every full source payload before
selection; fetch compact qualified member/facet metadata and hydrate selected pages with pinned
support. Do not create a durable cache/service per dossier merely to retain an inexpensive greedy
choice. WCE11 assembles larger journeys after these consumers work.

Independent examples must show duplicate redundant definitions losing a slot to a supported
exception/parameterization facet, an unsupported proposed member contributing no supported facet,
a conflicting revision retained despite redundancy, deterministic ties, empty/unresolved membership
and mandatory overflow with a valid continuation. Verify every represented facet has its declared
qualified member evidence and every selected member belongs to the full membership. Assess
automatic membership errors separately from representative-selection errors. Compare the
source-order control and greedy on the same frozen input; retain any lost supported facet alongside
gains. A complete source-order baseline may legitimately tie the greedy result.

Native negatives include spoofed member qualifications, a predecessor with shared inventory but
no required citation/role, changed source/current selection, stale facet dependencies and display
metadata supplied as membership evidence. Reader/CLI/MCP/export journeys must preserve scope,
all membership references and explicit omitted/continued display. Exact output/source integrity
and supported coverage are distinct checks. The coordinator owns F05 disposition and WCE12
owns final assembled qualification.

## Execution dependencies and completion contribution

The executable order follows contracts rather than whole-document barriers. WCE06 parser and
typed-value work can proceed when WCE01 and a WCE02 case slice exist; joined products need
WCE03–WCE05 actual source roles and compatible relationship semantics. WCE07 can implement
membership and simple facet display against the first qualified upstream slice, then adopt later
typed comparison facets without redefining membership. WCE08 needs WCE06's retained real
ambiguity, not a fabricated factor example. Coordinated editing of shared semantic/release/native
files remains the root's responsibility.

Packages include their producer, stored representation, native enforcement, affected reads and
focused verification. WCE11 assembles ordinary entrypoints and WCE12 owns final qualification/
retirement; neither absorbs unfinished package consumers. Preserve original PCE scope and controls,
authentic raw reports, source versions/digests, current supported readers, plans, evidence and raw
outputs. Retire replaced production selector/comparison/representative branches only after their
replacements and consumers are qualified, keeping useful named controls.

Plan-authoring execution, 2026-11-05: read-only code/documentation inspection and Context7 Lark
lookup performed. Product tests, probes, provider/database execution, training, benchmarks and
integrated qualification: **not_run**. Relevant targeted functional/native/provider checks are
planned above; final-source union accounting, publication checks and `just turn-end` belong to
the coordinator/root. No quality gain, optimum, normal-workload capacity or fully released
enterprise-corpus claim is established by these Proposed designs.

## Current selected realization — 2026-11-06

The [completion audit](../witnessed-corpus-enrichment_2026-11-05.md#completion-audit) bounds the comparison below to its observed premises.
The ordinary threshold producer leaves the basis unset and both Python and native comparison
treat two missing bases as equal. The same-unit revenue fixture therefore emits an interval even
though the accepted contract withholds it. Neither path consumes witnessed succession. The note
producer expands a table reference to per-cell proposals without a row or band premise.

The dossier journey assembles the caller-declared predecessor aggregate. The Python and native
paths copy the root identifier into that aggregate, and portable verification replays the same
selection. Root-specific qualification and the associated consumer journey remain open. The
recorded display comparison and exact aggregate custody are preserved.

**Implemented; actual scoped comparison and source products Tested.** Source-local table, note,
unit, formula/symbol and procedure contributions retain original physical anchors and outcomes.
All three GS120 policy arms retain the same8210 source contributions. Source-role mistakes remain
in the independent account; geometry and typed syntax alone establish neither semantic role nor
scientific interpretation. Actual comparison163/cut212 parses literal `T > 3` and `T > 6` in one
exercise while preserving unknown units and withholding stronger interval/applicability claims.
Ordinary native completion, Reader/file export, portable closure and fresh CLI/MCP parity pass.

The dossier producer derives members from exact retained source contributions plus structural
predecessors, with protected publication support only on exact independently assessed facets.
Original local interpretations, solver outcomes and unknowns enter member/facet/public identities.
Greedy supported-facet display and source-order control use identical full membership and a
12-member budget, preserve mandatory overflow and show omitted/missing facets explicitly.
`source-order-control-1` sorts immutable source IDs, citation offsets and member ID; it is a
deterministic source-ID control, not physical book-page reading order. Coverage differences
measure display of already-supported facets, not newly established corpus meaning.
The complete source membership remains proposed even when the representation selects it.
Native163 validates shared custody once per backing task binding before projecting every member;
its single-reference Reader delegates to the same validation owner. Full-workload timing and
representation results are retained in
[the actual structural journey](../../design_review/evidence/2026-11-06_wce-gs120/current-structural-journey/).
No unsupported member truncation, timeout widening or public-standing upgrade is permitted.

### Completion repair evidence

**Tested, 2026-11-07.** Native comparison run197 retained both event thresholds and
withheld interval and applicability claims. Literal revision controls exercise exact older
declarations, shared located clause lineage and forward or reversed comparison. The
selected root for dossiers196/202 is the exact normal-density definition component.
Both display policies retained the same two qualified members and facets, excluded the
independently supported marginal-totals component and passed Reader, CLI, fresh MCP and
portable verification. The budget could display both members, so this comparison
establishes no display advantage. [Repair evidence](../../design_review/evidence/2026-11-06_wce-completion-repair/README.md)

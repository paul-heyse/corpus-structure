# Design review for the M2 private parser stage

**Accept scoped · Proposed · 2026-11-08.** Proceed with private, released
HanLP frames and host candidates, Maverick mentions and memberships, and
Dipo ordered trees and context references. Preserve provider coordinates and
meaning through the shared task and Reader owners. Acceptance here concerns
the proposed architecture at the bounded development scope. Parser accuracy,
wider profiles, assembled PM2-08 delivery and release selection have their
own evidence boundaries.

## Scope and ownership

The subject is PM2-03–05 against committed `fb3709f4d43b697f6acc08d1fa6b783688343b83`,
excluding concurrent edits. The operator selected a combined review of HanLP,
Maverick and Dipo with source fidelity, private semantic authority and
execution fit. The diagnostic input is the parser refresh at that audited
source. The standard is core 3.3, heuristics 1.0, code-intelligence 1.4, the
repository binding and test-assessment 1.2. The reviewer inspected source and
pinned library interfaces independently. Foundation receipts retain their
original scope. [Parser audit refresh](../audit/README.md#pm2-parser-refresh) ·
[Package contracts](../../plans/production-milestone-two/linguistic-referential-discourse.md) ·
[Functional target](../../design/DESIGN.md#section-1)

| Boundary | Owner and contract |
| --- | --- |
| Source | Existing native product and retained view owners supply immutable source, recipe and coordinate identity. Cut 514 supplies source-first reference preparation. A successor release selects source through the authenticated finished origin at cut 517, or reprojects the retained integrated product through the current source owner and checks correspondence. |
| Execution | Released operation declarations govern applicability and shape. Existing task admission and attempt settlement own scheduling identity and effects. Provider preparation and inference run outside publication transactions. |
| Observation | Provider owns its native response. Source adapter owns coordinate mapping. Released private product validators own typed composition and local evidence references. Existing M1 producer and replay owners continue to govern the strong definition witness. |
| Consumption | Reader exposes committed operations and bounded products by explicit selection. PM2-08 owns composed delivery. PM2-11 owns independent assessment, and PM2-12 owns release adoption. |

| CI fact or relationship | Fidelity, universe and identity |
| --- | --- |
| HanLP dependency, argument, constituent | Typed inferred observations for supplied canonical sentences. Preserve one-based heads and root sentinel, PTB tags, SRL native roles and half-open spans, plus ordered constituency yield. A host candidate records its source-supported cue and frame without conferring strong definition-witness status. |
| Maverick mention and cluster membership | Inferred detections and memberships for the admitted coherent scope. Preserve raw inclusive endpoints, canonical mentions and mapping refusals. Membership supports proposing participants. Its coverage claim extends to the admitted scope and reported inventory. |
| Dipo EDU and binary tree | Inferred boundaries and tree over the exact raw or reconstructed input arm. Preserve ordered child ranges, native nuclearity and relation, and leading or unmapped gaps. A bounded sibling context is a view of the retained tree under its selected range and limits. |
| Retained private evidence | Stable operation, source and producer binding. Exact selected projection and canonical physical occurrence are separate promises. A refused mapping can leave a native item inspectable with its reason. |

## Contracts, execution and alternatives

**Proposed.** Use one released task for each provider and logical scope.
Bind method version, exact ordered provider input, source map, profile,
mode and supplied inputs before launch. Preserve stable source identity
through re-selection and keep the original execution origin for a reuse hit.
Publish private typed products with existing contribution custody. Use the
existing validators for anchor and endpoint closure. Preserve per-scope
success, empty, limited, unavailable and failed states separately from the
examined source population. Reader selection uses the completed cut and
explicit operation or task identity. Its one-result convenience method
has different cardinality. [Claim adapter](../../../python/corpus-structure/src/corpus_structure/orchestrate/pm2.py#L26) ·
[Contribution validation](../../../python/corpus-structure/src/corpus_structure/semantic/contributions.py#L69) ·
[Source result cardinality](../../../python/corpus-structure/src/corpus_structure/semantic/operations.py#L1302)

| Native capability | Application and material limit |
| --- | --- |
| HanLP multitask call | Submit complete canonical sentences with the five qualified heads and skip native tokenization. Keep the qualified EOS repair, PTB and UD distinctions, and return native SRL roles. An omitted predicate marker leaves SRL support unavailable. The Large/Base comparison holds source and heads fixed with separate profile pins. |
| Maverick `predict` and MES inventory | Use the ordinary detection seam and the native inclusive coordinates. Separately invoke `predefined_mentions` on the same tokens and scope. Preserve unassigned and unmapped items. Membership retains an ordered population without materializing every possible pair. |
| Dipo `predict_from_text` and `predict_both` | Raw layout-forced and learned modes compare identical text. Paired parsing shares one encoding over an EDU-reconstructed string. Capture that arm's actual source offsets and both token maps. Bound both mappings before their decoder work. Preserve the native tree as ordered ranges and read the smallest eligible sibling subtree by reference. |

The proposed route extends the foundation once and preserves native
decoders. Keeping smoke-report-only storage is physically simple, but
every consumer of a frame, cluster or subtree would have to parse the raw
response and reestablish evidence. Flattening all three results into a
generic graph would blur role, membership and ordered-tree meaning and
introduce unnecessary pair and edge expansion. The named private products
give consumers bounded selection over distinct semantics. A resident worker
amortizes model startup across scoped claims, and serial device ownership
trades parallel GPU execution for the existing capacity and recovery contract.
The design assumes the qualified bounds and uses independent diagnostics for
Base, forced layout and extended window behavior. [Pinned provider sources and operating profiles](../../plans/production-milestone-two/linguistic-referential-discourse.md#shared-integration-boundary)

## Change scenarios and findings

Adding a business vocabulary changes released definitions and fixtures while
the same preparation, native adapters and Reader apply. Replacing a
checkpoint changes the pinned producer and request identity. Existing
retained results stay readable through their origin. A cohesive section beyond
the qualified input bound exposes examined subscopes and unexamined
cross-boundary pairs. A sibling provider failure leaves committed products
and an explicit gap. A supplied diagnostic arm draws from a frozen reference
selection and carries a distinct mode and provenance. The ordinary arm receives only the frozen production inputs. These are Proposed scenarios, grounded in the
Interface-checked routes and the original foundation evidence.

| ID | Finding, consequence and correction | Closure evidence |
| --- | --- | --- |
| <a id="F01"></a>F01 | Provider-specific semantics currently live in the raw reply, with mapped smoke occurrences. Exposing a typed product by independently decoding the reply in each consumer would distribute authority. The parser adapters and released contribution owners should bind frame roles and candidate hosts, cluster members, and ordered tree ranges with explicit evidence and refusal states. Keep the strong definition path under its original producer. FP-02/04, DP-02/03/07, CI-G1/G2. | Read one retained product per provider and its exact origin. Reject a wrong span, endpoint or yield. Preserve ambiguous or unavailable evidence and demonstrate the same path with a second vocabulary. |
| <a id="F02"></a>F02 | A method/view selector admits multiple parser scopes while `BoundReader.source_result` assumes one result. Collapsing to a first match could silently substitute scope. Use explicit completed-cut operation or selected task identity. A cross-release selection must satisfy original finished-run custody. Compare separately from same-release computation reuse. FP-05/06, DP-04/09, CI-G2. | Read two different scopes of one method on one view by exact identity. Reject wrong cut or source pins. Verify a changed effective input schedules work and a matching same-release task preserves its origin. |
| <a id="F03"></a>F03 | Dipo raw recovery does not execute inside `predict_both`. Reusing its offset map or trusting the existing recovered-EDU limit alone would misattribute a paired result or allow excess decoder work. Bind the actual reconstructed text and offsets and enforce the reviewed and predicted EDU bounds before decoding each arm. FP-05/07, DP-08/15/20, CI-G1. | Retain both arm maps for a reviewed span with altered whitespace or a repeated string. Refuse a forged projection and over-limit EDU inventory. Keep raw layout forcing a separate mode and control. |

The [M2 coordinator](../../plans/production-milestone-two_2026-11-08.md#review-disposition)
owns all three dispositions. The companion plan retains package closure and
provides the integration evidence to PM2-08 and PM2-11.

## Judgments, gates and decision

The following judgments are for the proposed bounded route. Implementation
and operation qualification remain separate.

| Judgment | Verdict and evidence basis |
| --- | --- |
| A1 · Localize change | Satisfied. Vocabulary changes reach released definitions and adapter-local native mechanics stay behind owned provider boundaries. |
| A2 · Encode meaning explicitly | Satisfied for the proposed private scope with F01 constraints. Native interpretations, source identity, scoped candidates and admission have separate types and authorities. |
| A3 · Extend through composition | Satisfied. Existing task, evidence and contribution primitives combine with provider-local adapters and bounded read projections. |
| A4 · Fit execution | Satisfied for the bounded workload with F02–F03 constraints. Native bounds, local range views and a resident worker constrain repeated model and Reader work while preserving independent committed scopes. Larger context and throughput claims remain unresolved. |

| Gate | Proposed verdict and premise |
| --- | --- |
| G1 Authority | Pass. Source, inference, typed composition and public eligibility each use their owning boundary. |
| G2 Fidelity | Pass with F01 and F03. Distinct roles, absence states, memberships and ordered ranges survive mapping. |
| G3 Validity | Pass with F01 and F03. Source, endpoint, tree and arm limits have rejection points before consumers rely on them. |
| G4 Hidden behavior | Pass. Effects follow explicit private requests and the task owner. Inspection uses retained reads. |
| G5 Recovery | Pass. Bounded claims preserve committed scopes and expose interrupted or unexamined work. |
| G6 Transformation and reuse | Pass with F02 and F03. Inputs, mapping and origin bind reuse, and diagnostic arms carry distinct coordinate custody. |
| G7 Capability claims | Pass for the stated design. Foundation evidence supports the selected mechanisms and initial bounds. Package inference fidelity and native integration still require fresh evidence. |
| G8 Library leverage | Pass. The route reuses native decoding, shared task lifecycle and existing contribution and source readers. |
| CI-G1 · Fidelity | Pass with F01 and F03. Native inference and scoped semantic interpretation remain separately attributed. |
| CI-G2 · Closure | Pass with F01 and F02. The Reader binds products to a completed selection and immutable evidence. |
| CI-G3 · Assessment | Pass. The ordinary request is fixed before predictions and cannot consume independent references. Reviewed inputs belong to named diagnostic arms. |

**Accept scoped.** Confirm implementation through focused mapping and retained
Reader controls, actual pinned native runs, paired comparison cases and the
assembled review. Fresh product, provider and fault checks were `not_run`
in this design review. The current binding decisions govern this route. Evaluate wider
modes when PM2-06 has matching operating evidence. Assembled publication and
release selection remain unresolved at this review boundary.

## Assembled implementation assessment

**Interface-checked · 2026-11-08.** This assessment inspected the assembled
working tree over `fb3709f4d43b697f6acc08d1fa6b783688343b83` during integration.
The private path reuses authenticated source selection, exact-input task
admission, lease ownership and transactional contribution settlement. The
task owner limits reuse to completed or empty work with matching project,
release, realization revision, runtime, method configuration, unit and
input. The contribution Reader accepts explicit selected task identity.
These are source findings. Fresh native inference, retained-result and reuse
checks were `not_run` in this assessment. [Runner](../../../python/corpus-structure/src/corpus_structure/orchestrate/pm2_stage.py) ·
[Task admission](../../../python/corpus-structure/src/corpus_structure/semantic/operations.py#L267) ·
[Contribution Reader](../../../python/corpus-structure/src/corpus_structure/serve/contributions.py#L122)

| Review question | Observed implementation and remaining obligation |
| --- | --- |
| F01 · Authority and fidelity | HanLP validates UD trees, SRL role spans and ordered constituency yields before locating frames and cues. Maverick distinguishes detection and membership and preserves native coordinates in the report. Dipo validates an ordered binary tree and anchors each EDU independently. Products carry generic retained contribution values, with provider shape checks at the adapter. Released operation declarations cover family, tier and outcome. Release-owned payload shape and provider-specific consumer checks remain open. The existing strong definition witness stays under its original operation. [HanLP](../../../python/corpus-structure/src/corpus_structure/methods/pm2_hanlp_products.py) · [Maverick](../../../python/corpus-structure/src/corpus_structure/methods/pm2_maverick_products.py) · [Dipo](../../../python/corpus-structure/src/corpus_structure/methods/pm2_dipo_products.py) · [Retained representation](../../../python/corpus-structure/src/corpus_structure/methods/pm2_result.py#L283) |
| F02 · Scope and reuse | A selected extent was checked at canonical token boundaries and then sentence-split independently. A token-aligned truncation can therefore appear as a complete canonical sentence or coherent pack. Authenticate against the complete view's prepared sentence boundaries. Verify separate task selections on one view, exact same-release reuse, changed inputs and forged source pins through the retained Reader. [Scope preparation](../../../python/corpus-structure/src/corpus_structure/orchestrate/pm2_stage.py#L122) |
| F03 · Dipo paired custody | The paired path captures the actual reconstruction and bounds EDU mappings before building representations. It accepts reconstruction only when it is an exact selected substring and limits the diagnostic to that correspondence. Overlapping reconstructed token offsets are refused as location evidence while native tree structure remains inspectable. Verify reviewed and predicted arms independently, including a case with a projection change, and demonstrate the bounded sibling result from a committed tree. [Paired inference](../../../python/corpus-structure/src/corpus_structure/methods/pm2_dispatched.py#L303) · [Range view](../../../python/corpus-structure/src/corpus_structure/methods/pm2_dipo_products.py#L244) |
| Recovery | Startup mismatch is scoped to the affected profile. A provider error frame terminates the resident worker, leaving later scopes of that profile unattempted. Malformed result shape can also escape conversion and interrupt later profiles. Keep provider result failures local to the affected task and preserve run recovery for infrastructure failure. Exercise a successful sibling after both startup and inference failure. [Worker error handling](../../../python/corpus-structure/src/corpus_structure/methods/pm2_worker.py#L198) · [Claim settlement](../../../python/corpus-structure/src/corpus_structure/orchestrate/pm2.py#L26) |
| Work and coverage | Guards bound the admitted text and native token or EDU work, and reuse of one resident worker amortizes setup. A HanLP batch that crosses a sentence or padded-token bound loses otherwise eligible sentences. Maverick and Dipo bounds refuse the full submitted scope. These refusals retain a reason. The planned fallback still needs complete supported subscopes and explicit unexamined cross-boundary coverage. [HanLP bounds](../../../python/corpus-structure/src/corpus_structure/methods/pm2_hanlp.py#L151) · [Maverick and Dipo bounds](../../../python/corpus-structure/src/corpus_structure/methods/pm2_dispatched.py#L15) |

The scoped design remains applicable. Keep recovery, canonical sentence
fidelity and fallback coverage in package disposition until corrected or
explicitly bounded by the owning plan. The frozen comparison panels supply
source-only expectations for later native and retained observations.
[Comparison panel](../evidence/2026-11-08_pm2-parsers/README.md) ·
[Package closure](../../plans/production-milestone-two/linguistic-referential-discourse.md)

**Integration follow-up · Interface-checked · 2026-11-08.** The revised runner
uses the complete view's prepared layout to derive sentence boundaries once per
selected view, then refuses token-aligned truncation of a HanLP or Maverick
sentence. It opens another worker for remaining claims when inference closes
the current worker. Parser payload validation errors from a successful reply
have a failed-result path with the rejected reply preserved. Native receipts
still determine recovery and prepared-scope behavior. [Revised runner](../../../python/corpus-structure/src/corpus_structure/orchestrate/pm2_stage.py) ·
[Conversion settlement](../../../python/corpus-structure/src/corpus_structure/orchestrate/pm2.py)

**Tested integration · 2026-11-08.** The installed book runner completed cut
520. Two exact selections over one HanLP method and view returned different
scope results. A ten-sentence parent recorded a native limit and two child
results preserved their distinct five-sentence coverage. The exact replay in
cut 521 retained the two original task identities. The Dipo Reader retained
the separate source pieces around the roulette separator and supplied the
bounded temporal context selector with exact leaves. Parser claims remain
private. The owning plan records additional assessment and consumer work.
[Native execution receipt](../evidence/2026-11-08_pm2-parsers/records/pm2.private-parser-stage.json) ·
[Dipo readback](../evidence/2026-11-08_pm2-parsers/records/pm2.dipo-panel.json) ·
[Execution disposition](../../plans/production-milestone-two/linguistic-referential-discourse.md#parser-execution)

# Domain model operability

**Status:** Proposed implementation. Owns the successor design and full-system qualification.
**Created:** 2026-11-20. The operator directed this series to supersede the entire
[Unified domain model and execution series][predecessor]. Its files and receipts are historical
baseline evidence. This series derives its design work from the [integrated functional review][review]
and its acceptance from the resulting supported product. Production changes require execution
authorization. This plan publication does not change an accepted ADR or current runtime state.

## Outcome and current baseline

The operator can tell which work a change affects, see the first failed prerequisite before
starting costly work, and retain eligible results when a later step changes or a run stops. Model
relationships drive preparation, consumer requirements, change propagation, and validation. Each
data boundary has an identifiable owner. PostgreSQL-native numeric behavior governs supported
interchange, with a deliberate, versioned identity contract where a digest has semantic meaning.
The finished capability includes the real providers, managed operation controls and one complete
book run on the adopted final release.

**Source reviewed.** Integration review publication `d4d606247`, the [causal evidence][causal],
and the [JSON boundary evidence][json-evidence]. Current source and dependency pins were inspected
at `d4d606247`. The repository's [design standard][standard] supplies the criteria. Explicit domain
authority and identity layers matter to the adoption and access boundaries. Execution fit is judged
by selected work, repeated verification, boundary crossings, and recovery scope on the supported
workload. A narrower response does not by itself bound server work. The only planned performance
diagnostic is for the material event uncertainty and any resulting correction. No speed target is
claimed.

| Current fact | Consequence for this plan |
| --- | --- |
| N42 stage admitted both releases and main reproduced all 624 native objects. Cold Integrated demand refused in executable acquisition before inference. | Installed program parity and acquiring the selected executable need separate evidence. |
| The bounded rich case passed. The M1 attempt published but exceeded its broad readback bound. The event attempt published before timeout at scorer attachment, with two authority cases unrun. | Preserve rich authority, exercise selected M1 readback, and qualify the full event journey. |
| N36 actual stop/resume and unchanged repeat passed in their scope. N29 remains the recorded canonical head and the book's selected generation is 5. | Recheck actual targets. Keep exact recovery and qualify material adoption on the new basis. |
| Native request validation and client result validation already exist. The retained Python/PostgreSQL schema comparison shows disagreements, and JSON paths differ in numeric and decoder behavior. | Establish shared meaning before removing residual checks. Migrate consumers with the codec and contract. |

The precedents above are retained, dated evidence. [Current evidence][causal] ·
[Historical qualification][old-qualification] · [Implementation architecture](../design/DESIGN.md)

## Shared contracts and rule decisions

- The operation declaration supplies selected executable surfaces. Preparation verifies actual
  archive, loaded callable and resource correspondence. Material identity states what can change
  an output. Native reuse independently checks sufficiency, original custody and current authority.
- The consuming role supplies requirements. Historical support is checked against its own custody.
  Current disclosure and effects use live authority. Share established validity only under the same
  cut and premises. A narrower projection keeps root attribution, missing-member meaning and fences.
- PostgreSQL integer domains govern whole numbers, `double precision` governs approximate typed
  calculations and finite JSON numbers are the interchange. PostgreSQL JSONB uses its native numeric
  representation. Identity and historical byte custody keep their own named contracts. The operator
  confirmed consistency and PostgreSQL-native handling on 2026-11-20.
- Existing CLI routes render typed decisions and observed progress. A preview may report available
  facts and conditional readiness. Executable preparation, native effects and provider publication
  keep their owners. Readback reports its scope.

<a id="dmo-00"></a>
### DMO-00 · Establish the current contract and resolve rule impacts

Confirm current source, observed stage/canonical selections and supported entry points when
execution starts. Read the applicable existing decisions and capture their exact change or
preservation in the owning package. Schedule only the affected successor ADRs and owning design
edits before dependent production work. The earlier plan's status change by itself does not change
accepted architecture. The operator's numeric direction governs the transport design. Where it
would change an identity equivalence class, public field contract, or guarantee below, make the
specific consequence explicit and obtain the rule decision before the dependent cutover. Until
then preserve the existing rule at that boundary. Use the repository's applicable review cadence
for changed ownership or binding boundaries. The plan's focused foundation assessment is recorded
here and in the companions. [Decision and review binding][binding]

| Contract to resolve | Proposed domain or preserved basis | Owner and dependency |
| --- | --- | --- |
| D1 keys and analyzed-scope identity | Preserve current D1 keys and authenticated archive bytes. Decide a versioned transition if native numeric scope would merge formerly distinct values. Verify independent Python and SQL vectors. | DMO-02 with DMO-05 domain definition. [ADR-0100](../adr/0100-ddo-contextual-identities.md) |
| Native wire and agent-facing output | Keep explicit Draft 7 and request-in-SQL/result-in-client placement. State the narrower numeric domain and the D8 implications of changing `exact_json` delivery. Version and migrate affected consumers together if the contract moves. | DMO-05/06, then DMO-07 delivery. [ADR-0128](../adr/0128-wire-contract-boundary-validation.md) · [D8](../design/D8-agent-and-query-interfaces.md) |
| Runtime custody, recovery and continuation | Preserve exact executable and original producer custody and keep live authority. Narrow enforced correspondence only over proven selected boundaries. Continue to distinguish continuation compatibility from stronger reuse. | DMO-01/02 and DMO-04. [ADR-0137](../adr/0137-serving-code-and-model-custody.md) · [ADR-0139](../adr/0139-compatible-pdf-checkpoint-custody.md) · [ADR-0141](../adr/0141-serving-continuation-and-reuse.md) |

## Execution queue

| Package | Delivered change | Entry and completion boundary |
| --- | --- | --- |
| DMO-00 | Current baseline, scoped contracts and rule decisions | Reconcile current environment and owners. Resolve binding changes by the point they are needed. |
| [DMO-01][p01] | Selected PDF/M1 executable acquisition and early preparation refusal | Current archive and runtime owners. Verify alternate roots, relocation and real binding/resource refusals. |
| [DMO-02][p02] | Versioned material identity, explanations and compatible recovery | Selected executable contract and DMO-05 numeric semantics. Consume DMO-06 native wire projection where changed. Verify digest vectors and independent regional uptake. |
| [DMO-03][p03] | Typed consumer requirements and current/historical authority | Existing admitted role, support and effect owners. Integrate with DMO-01 preparation and confirm the real mixed-family path and refusals. |
| [DMO-04][p04] | Bounded event diagnosis and scoped support acquisition | Diagnostic can start from the existing fixture. Working integration consumes DMO-03 requirements and the DMO-06 owned snapshot where relevant. Verify scoring, paging and both authority negatives. |
| [DMO-05][p05] | Numeric roles, interchange and independently deliverable settings | Establish value semantics first. Coordinate codec activation with DMO-06 where the wire moves. Verify real boundary behavior and private environment isolation. |
| [DMO-06][p06] | Explicit, equivalent schema contracts and residual validation retirement | DMO-05 value contract. Prove agreement on the supported profile before the combined wire cutover and removal of repeated checks. Verify native rollback on off-contract results. |
| [DMO-07][p07] | Attributed operator diagnostics | Preparation slice can start with DMO-01. Finish with actual recovery, consumer and scope facts from DMO-02–04 and the applicable typed output contract. |
| [DMO-08][p08] | Final-source stage and functional qualification | Functional and retirement scope complete. Reconcile the managed evidence union against final source and acquired context. |
| [DMO-09][p09] | Guarded canonical adoption and whole-book qualification | DMO-08 on the selected final release. Verify original custody, complete the book, and independently verify interruption/reuse and zero new work on repeat. |

Dependencies refer to the supplied contract or integrated consumer, not to every activity in the
cited package. The settings slice, schema inventory, executable acquisition, first diagnostic work
and event investigation may proceed in parallel. The author of a contract also schedules removal of
its superseded paths with its consumer migration. A scoped pass closes only the property it tests.

## Review disposition and investigation

Original IDs retain their source meaning, with all integrated recommendations accounted for here.

| Integrated review | Source correspondence | Package and closure |
| --- | --- | --- |
| [O01][o01] | N42 refusal and missing M1 capture | DMO-01 selected binding controls and DMO-08 real M1 scoped publication. |
| [O02][o02] | Book attachment and checkpoint uptake | DMO-02 field comparisons and authenticated recovery. DMO-09 adopted whole book. |
| [O03][o03] | Rich admission and JSON O09 | DMO-03 typed input requirements, mixed-family and live/history refusals. |
| [O04][o04] | First failing prerequisite, including M1 and event read scope | DMO-07 typed previews and observed failure/readback. |
| [O05][o05] | JSON O01/O02/O08, D4/D7/D8/D11 | DMO-05 consistent native numbers, codec consolidation, workers, delivery bytes and public numeric consumers. |
| [O06][o06] | JSON O01/O03, identity and tag collision | DMO-02 named profiles and authenticated old bytes. DMO-05 value-domain inventory. |
| [O07][o07] | JSON O04/O05/O06, D2/D3/D5/D6 and conditional O11 | DMO-06 one authority and a portable profile. Dialect move conditional on scoped benefit and rollout. |
| [O08][o08] | Event support and JSON O07, parse-once and residual validation | DMO-04 sufficient cut, DMO-06 reuse of owned validation and detached checks. |
| [O09][o09] | JSON O10, D1/D9/D10 | DMO-05 settings slice with private-cohort and provider propagation controls. |

The decisive open questions have bounded outcomes. DMO-01 uses selected-operation checks on each
historical edit and leaves required correspondence conservative when unresolved. DMO-02 inventories
old digest roles and the tag collision. DMO-05 identifies fraction-sensitive readers and stored
bodies, including dynamic prepared packs. It compares RapidJSON bytes/options and callable custody
only if a consumer still requires RapidJSON. DMO-06 inventories actual kind dialects, generated and
installed validation call sites, verifies pattern parity including variable-width patterns, and
maps native digest fanout before a wire move. DMO-04 uses one bounded event diagnostic to choose
fixture, lock/transaction or repeated-traversal correction. [Review open checks][review-open]

Conditions govern alternatives. Keep Draft 7 unless a warranted coordinated wire migration can
absorb Draft 2020-12. Consider an alternate regex or schema engine if the portable profile cannot
express required constraints and the candidate demonstrates agreement. Consider `msgspec` only for
a demonstrated typed protocol fit or material bottleneck. Decline `orjson` for the selected role.
Native continuation and current process caches are part of product behavior. Former persistent
cache tiers and predecessor-only design work have no successor work package.

## Completion and handoff

The series owns any product changes needed for supported functionality to qualify. DMO-08 accounts
for the integrated ordinary, native, fault, real-provider and repository evidence. DMO-09 owns
verified preservation and guarded activation, then the original 518-page and 29-region workload,
controlled interruption, completed composition and an unchanged repeat. Incompatible generated
work may be regenerated through the current path. Choose the book's effective resource policy from
the adopted workload and record it with the run. Chandra OCR stays excluded. The predecessor's
package statuses, resource limits and proof questions are historical. Report outcomes at their
actual scope, retain failed receipts, and leave unavailable required cases open with the missing
prerequisite. [Qualification and adoption][p08]

**Current state.** Plan authored. Product implementation, guarded adoption and successor
qualification are `not_run`. First execution is DMO-00 and the ready bounded investigation slices.

[predecessor]: unified-domain-model-and-execution_2026-11-19.md
[old-qualification]: unified-domain-model-and-execution/qualification.md#retained-fit-custody-and-rich-producer-authority
[review]: ../functional_reviews/udm-operability-and-json_2026-11-20.md
[review-open]: ../functional_reviews/json-boundaries_2026-11-20.md#open-checks
[causal]: ../design_review/evidence/2026-11-20_udm-operability-causality/README.md
[json-evidence]: ../design_review/evidence/2026-11-20_json-boundary-contracts/README.md
[standard]: ../design_review/design_principles/standard.toml
[binding]: ../design_review/design_principles/binding/corpus-structure.md
[p01]: domain-model-operability/execution-identity-and-recovery.md#dmo-01
[p02]: domain-model-operability/execution-identity-and-recovery.md#dmo-02
[p03]: domain-model-operability/consumer-authority-and-operability.md#dmo-03
[p04]: domain-model-operability/consumer-authority-and-operability.md#dmo-04
[p05]: domain-model-operability/json-contracts-and-settings.md#dmo-05
[p06]: domain-model-operability/json-contracts-and-settings.md#dmo-06
[p07]: domain-model-operability/consumer-authority-and-operability.md#dmo-07
[p08]: domain-model-operability/qualification-and-adoption.md#dmo-08
[p09]: domain-model-operability/qualification-and-adoption.md#dmo-09
[o01]: ../functional_reviews/udm-operability-and-json_2026-11-20.md#O01
[o02]: ../functional_reviews/udm-operability-and-json_2026-11-20.md#O02
[o03]: ../functional_reviews/udm-operability-and-json_2026-11-20.md#O03
[o04]: ../functional_reviews/udm-operability-and-json_2026-11-20.md#O04
[o05]: ../functional_reviews/udm-operability-and-json_2026-11-20.md#O05
[o06]: ../functional_reviews/udm-operability-and-json_2026-11-20.md#O06
[o07]: ../functional_reviews/udm-operability-and-json_2026-11-20.md#O07
[o08]: ../functional_reviews/udm-operability-and-json_2026-11-20.md#O08
[o09]: ../functional_reviews/udm-operability-and-json_2026-11-20.md#O09

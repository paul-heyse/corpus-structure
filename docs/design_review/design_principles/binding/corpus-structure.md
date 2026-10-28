# corpus-structure binding

Apply the [design principles](../core/design-principles.md) and [efficient-architecture heuristics](../core/efficient-architecture-heuristics.md) together
for consequential architectural choices. Use qualitative judgment before physical organization,
interfaces, preparation, assurance and lifecycle choices become entrenched. During execution,
apply relevant guidance to material open choices or revealed mismatches; reuse settled reviews
unless concrete new evidence warrants reopening them. No standing checklist, cost model or
additional proof machinery follows.

The repository layer of the design standard. It defines no principles; it maps the
[core design principles](../core/design-principles.md) and the
[code-intelligence profile](../profiles/code-intelligence/principles.md) onto this repository's
binding decisions, review cadence, vocabularies and code. `docs/design/DESIGN.md` plus
`docs/design/sections/` is the architectural collection; DESIGN §2 delegates review mechanics to
this page under ADR-0002. Other design contracts and accepted decisions govern plan execution and
implementation review in their domains; a design review treats them as current design and reports
its rule impacts instead (design-review, Grounding).

## Standard applied

| Layer | Document | Version |
|---|---|---|
| Core | [design principles](../core/design-principles.md), [efficient-architecture heuristics](../core/efficient-architecture-heuristics.md), [review template](../core/design-review-template.md) | 3.3 (repository-owned edition, ADR-0002/0006) |
| Profile | [code-intelligence principles](../profiles/code-intelligence/principles.md), [review additions](../profiles/code-intelligence/review.md) | 1.4 |
| Binding | this page | — |

The version/path declaration in [`standard.toml`](../standard.toml) is authoritative for loading.
Preserve DP/CI IDs and historical version semantics; FP-01–FP-07 and A1–A4 supply the
architecture structure. FP-04/A2 require an adequate, explicit domain model that governs
behavior. ADR-0002/0006 adopts core/template 3.3 and code-intelligence guidance 1.4 when selected. Apply domain-model
assessment within requested or scheduled reviews; ordinary implementation does not initiate it.
Follow flows only where they resolve a concrete uncertainty within that scope. FP-07/A4 qualitatively assess
execution fit for the functional-intent workload: access paths, necessary work, library composition,
locality, working sets, reuse, assurance and lifecycle/recovery scope. Semantic declarations do not
prescribe physical granularity. Static evidence can establish amplification; quantitative performance
claims need measurements. Explain material tradeoffs in plain language; no numerical estimates,
cost models, estimators, runtime cost accounting, execution-planning machinery, instrumentation,
formal cost proofs or additional proof artifacts are required by this consideration. Such mechanisms
need a separate concrete functional or operational requirement; semantic correctness obligations
remain. No new standing review, checklist or benchmark obligation is introduced.

## Design principle audit

The [audit skill](../../../../.claude/skills/design-principle-audit/SKILL.md) maintains
[one living Markdown collection](../../audit/README.md) at `docs/design_review/audit/`.
It diagnoses current code broadly against the functional target and the same core, heuristic and
profile principles, without an incoming library preference or principle subset. It need not choose
remedies or render an overall acceptance verdict.

Refresh the broad account before a new diagnostic design-review engagement about production
or broad system scope, including direct invocation. Test-only engagements use the separate
test account below. Mixed engagements identify the accounts covering their consequential
questions and refresh the applicable scope; one baseline does not refresh the other.
Use the preceding audited source state and intervening changes to focus current inspection;
reconsider unchanged dependencies and earlier findings when their premises change. Record source
commit, included dirty changes, date, standard versions and meaningful coverage limits honestly.
The publishing commit is distinct from the source baseline. An empty scaffold is not an audit.

One refreshed account can serve preparation and review in the same engagement while its baseline
remains applicable; reconcile intervening source or standard changes before relying on it. Reviews
cite its publication revision and stable finding anchors. An inherited observation keeps the date
and applicability limits of its evidence rather than becoming freshly verified by republication.

The audit owns baseline diagnosis and groups structural causes in flexible documents, initially
around semantic authority, structure/invariants, boundaries/composition, local reasoning/assurance
and execution fit. Give each finding one primary home, relevant principle IDs and its inspected
footprint; distinguish suspected reach. Keep identity across moves and material lineage across
splits/merges. Resolve and remove findings on evidence; Git and the removal commit preserve history.
Do not copy plan progress or run a new whole-codebase audit to close every implementation slice.

Ordinary implementation, focused plan-foundation assessment and loading review criteria do not
initiate a broad principle audit or formal review. Principle audits do not automatically start solution reviews or authorize
remediation. Process discussion and edits to this workflow do not require an audit/review artifact.
The initial audit and detailed library overviews remain separately scoped work.

## Test code design principle audit

The [test audit skill](../../../../.claude/skills/design-principle-audit-tests/SKILL.md) maintains
[a separate living collection](../../test-audit/README.md) at docs/design_review/test-audit/.
Use it for an explicitly requested test-scope audit and before a new diagnostic solution review
whose subject is test architecture or test evidence. This is a sibling diagnostic route, not a
whole-production audit prerequisite. Ordinary test edits, implementation reviews, qualification
runs and installation of this process do not initiate it.

Load the [test-assessment companion](../core/test-assessment.md) through `[core].test_assessment`
alongside the selected core, heuristics and applicable domain profiles. It supplies test-specific
judgment, not new principles, gates or a mandatory test campaign. Tests include relevant inline
code, fixtures, helpers, generators, doubles, oracles, reference data and execution configuration;
production paths are inspected as needed to understand contracts and assurance dependencies.

The test account records its own audited source state, included dirty changes, date, standard
and companion versions, inspected scope and limits. Its publishing revision is distinct. Use
intervening production-contract and support changes as well as test edits when refreshing it;
an unchanged test can have changed evidential meaning. Neither an empty scaffold nor another
account's source baseline establishes test-audit coverage. Reviews cite the applicable publication
revisions and finding anchors and reconcile intervening changes before relying on them.

New test findings have stable DTA-nnn identities, beginning with DTA-001. Each structural cause
has one primary finding home across both audit collections. Existing DA-nnn findings retain
their identity and home and are linked rather than copied; reexamination here states its scope
without silently refreshing that other account. Preserve lineage on moves, splits and merges,
never reuse retired IDs, and remove resolved material only on evidence with recoverable history.
Reviews own alternatives and judgments; plans own scheduled disposition and closure evidence.
This collection diagnoses and does not select remedies, authorize repairs or certify suite quality.

## Functional capability exploration

Use [functional-extension-review](../../../../.claude/skills/functional-extension-review/SKILL.md)
and its preparation companion for deliberate functional enhancement within the operator's chosen
outcome, workflow, subsystem or ecosystem. The [functional collection](../../../functional_reviews/README.md)
owns output and recommendation-audit conventions. These reviews assess useful capabilities and
their realization without a diagnostic audit prerequisite or required principle violation.
The diagnostic design-review cadence below remains distinct. Selected opportunities enter the
existing planning and decision routes; a review does not itself approve scope or implementation.

## Library leverage

The [library-leverage framework](../../../library_leverage/README.md) owns three distinct
skills and their output contracts (ADR-0008): codebase opportunities, focused library capability
applicability, and comparative judgments of complete options. All stages use relevant base
patterns and additional patterns collected in assessment outputs. Useful library types and
additional patterns remain after current matches retire; promotion into base guidance is manual.

Use the selected standard for consequential comparisons. Opportunity recognition, principle
diagnosis, applicability and comparative preference remain distinct. Plans own execution
disposition and closure evidence. The workflow neither initiates a broad audit nor replaces
formal review due under the existing cadence or authorizes product changes. Installation
establishes no assessment baseline or qualified library fit.

## Plan improvement

Use [plan-improvement-review](../../../../.claude/skills/plan-improvement-review/SKILL.md) at
requested or explicitly planned boundaries to assess the remaining change footprint of a plan
or coordinated series. Include design-principle alignment and general enhancements to components
substantially modified to accommodate the plan, even when their value extends beyond its
functional target. Judge recommendations for coherent integration and total burden. Publish a
standalone [plan-improvement review](../../../plan_improvement_reviews/README.md) with proposals
distinct from accepted scope and scheduled work. Plan revision from that document is separately
instructed; no separate update skill is required.
This workflow has no broad diagnostic-audit prerequisite, does not refresh an audit account and
does not replace a formal design review due at the cadence below. Existing scope and decision
routes govern adoption.

## Reviews in this repository

- **Location:** `docs/design_review/reviews/design_review_{slug}_{YYYY-MM-DD}.md`.
- **Evidence method:** static source, contract and documentation inspection can suffice. Probes
  are optional when material uncertainty warrants them; no review kind requires a probe or evidence
  folder merely because it is a review. Tested and Measured claims still need their stated evidence.
- **Who:** the `design-review` skill with `design-review-code-intelligence`, usually through a
  fresh `design-reviewer` subagent, so the author of a change is not its reviewer.
- **Review focus:** the operator chooses holistic/unconstrained, library-targeted, principle-focused
  or combined. Clarify an unspecified choice. Libraries are hypotheses, not required adoption;
  principle focus directs solution depth while other relevant guarantees still constrain remedies.
- **Grounding:** the standard and the functional target in `docs/design/DESIGN.md` §1.1; any
  mechanism §1.1 names is a rule, like ADRs and the policies on this page. A review lists the
  rules its recommendations would change (`review#RCnn`); they change only after the operator
  confirms them in plan creation.
- **Cadence and purpose** (ADR-0002; every review has the `target` purpose):
  - Before a substantial stage, changed ownership/dependency boundary or §B decision: a
    **design/target** review, including adjacent consumers and realistic change scenarios.
  - For a bounded slice inside accepted boundaries: **change/target**, with the affected
    contract, one relevant extension scenario and its enclosing architectural limit. Pure
    mechanical changes may give an explicit reason the scenario is unchanged.
  - At an integrated stage or increment boundary: **design/target** review of the assembled
    scope and accumulated findings; compare the original scenarios with the resulting code.
    A coincident stage/increment end needs one review. Depth follows impact and uncertainty.
  - Reopen architectural analysis sooner when repeated classifiers, private dependencies,
    inseparable test setup or repeated structural deferrals affect planned work. These are
    reasoning triggers, not new blocking hooks.
  - A local pass never certifies the enclosing architecture.
- **Authority:** for plan execution and implementation review, the architectural collection is
  authoritative, so a divergence from an implemented claim is a code defect or a stale DESIGN
  section; distinguish both from an accepted target still awaiting implementation. A design
  review judges the collection against the standard and the functional target instead.
- **Outcomes and labels:** check outcomes are `passed`/`failed`/`blocked`/`not_run` with the
  command (AGENTS.md *Reporting*); historical test receipts keep their original date and scope
  and are not fresh runs; a mocked provider is never a pass; outcomes are never turned into a
  percentage.
- **Reviews are evidence, never authority.** A governed architectural section changes through
  the ADR that responds to a finding, once the operator has confirmed any rule change it carries.

**Documentation boundary (ADR-0003).** Read the architecture map, relevant section owner and
adjacent consumers. Stable section IDs survive relocation; one resolver supplies ADR lint and the
site directory. Derived navigation/search and link checks serve readers; they do not certify
implementation or historical claims. Documentation tooling uses focused `just docs-test` /
`just docs-check`, independently of integrated product qualification.

## Design-review recommendation audit

Use [design-review-audit](../../../../.claude/skills/design-review-audit/SKILL.md) for a deliberate
requested or explicitly planned reassessment, usually between a completed review and plan
creation (ADR-0007). Inherit its operator-selected focus and applicable standard. Reconsider
each recommendation and their interactions, and seek omitted improvements within that focus.
Judge diagnoses separately from remedies; retaining a recommendation is a valid result.

Publish a net-change companion at
`docs/design_review/reviews/audits/<principal-review-stem>_audit.md` and an integrated revised
review at the original principal path. The [folder guide](../../reviews/audits/README.md)
owns naming and repeat-audit conventions. The companion accounts for every input recommendation
with Retain, Improve, Correct or adjust, Omit, or Unresolved, plus additional recommendations and
their basis. Preserve the exact input in Git before replacement and cite its revision. Record
the current audit date, source/standard baselines and evidence limits, distinguishing changes
since the first assessment from corrections to it.

The revised principal explains the resulting design, with consistent judgments, recommendations,
dependencies and rule impacts. Briefly attribute the new judgment and link the companion; it
does not imply the original reviewer agreed. Keep critique of the first round in the companion.
Preserve finding/rule-impact identities and the difference between recommendation correspondence
and finding identity. Omitting a remedy can leave a valid diagnosis open. Existing test receipts
remain historical evidence at their original strength, date and applicability.

This normally continues the same engagement and does not itself require another broad audit;
reconcile changed premises and use the freshness rule if it becomes a new engagement. A fresh
`design-reviewer` can provide independent judgment, returning both texts for coordinator
publication. Recommendation dispositions are editorial, not execution status. Flag implications
for plans already consuming the review without silently changing accepted scope. Rule changes
still go to the operator in plan creation; the audit does not authorize remediation.

## Plan-completion audit

Use [plan-completion-audit](../../../../.claude/skills/plan-completion-audit/SKILL.md) at a
deliberate requested or explicitly planned claimed-completion boundary (ADR-0007), for the whole
plan or explicitly bounded scope. Reconstruct the accepted obligations from the intended behavior,
target design, authorized scope changes and acceptance conditions, including applicable consumer,
migration, preservation and retirement work. Inspect actual implementation beyond completed rows
or the reported diff. New design opportunities are distinct from unfinished accepted scope.

Update the same owning plan in place: a current Completion audit section records date, inspected
source state, claimed scope, bounded conclusion and evidence limits. Reconcile affected package
state, findings, completion claims and next work rather than appending a contradictory report.
The coordinator owns a series' combined conclusion; supporting plans retain affected local
details and source finding identities. Git holds prior accounts and receipts keep their original
dates and scope. No separate completion report, folder or progress register is introduced.

Distinguish functional implementation, required qualification and benefit measurements. Use
existing applicable evidence and targeted investigation as warranted; no automatic full test
campaign follows. Missing required evidence remains outstanding under the existing qualification
policy. A fresh `implementation-reviewer` can return the judgment and proposed plan corrections
read-only for coordinator publication. The audit identifies actionable repair scope without
authorizing production repairs, broad principle diagnosis or a new solution review. Neither new
audit is a recurring per-slice gate or an automatic part of every handoff.

## 1. Binding decisions and what they bear on

IDs are never reused or renumbered. Changing a §B decision needs an ADR and a design/target review.

| ID | Binding decision (DESIGN.md §2 is authoritative) | Bears on |
|---|---|---|
| — | None yet: add a row per §B decision, naming the DP/CI rules and gates it bears on | — |

## 2. Recurring review questions, routed onto the gates

Add domain questions here as reviews repeat them, each routed to the gate that settles it. Use
them after reconstructing responsibilities and expected changes.

## 3. Vocabulary and scenario authorities

| Meaning | Authority |
|---|---|
| Design claim strength | Core principles §D; label and date the claim actually established |
| Architectural judgments | Core §E, A1–A4; report separately from gate verdicts |
| Correctness/fidelity gate verdicts | Core §A and profile gates |
| Check execution outcomes | AGENTS.md Reporting; each outcome names its command |
| Domain vocabulary | Executable declarations and DESIGN; never infer it from review labels |

Select scenarios from the active plan. Record the recurring architectural scenarios here with
their expected boundary as they emerge (for example: add a variant using existing categories;
upgrade a dependency; change an invariant; test a transformation in isolation). They are scenario
seeds, not promises about current implementation.

## 4. Where findings land

Diagnostic findings retain `DA-nnn` identities in the [living audit](../../audit/README.md);
reviews cite the consumed audit revision and preserve those IDs. Additional review findings keep
source-review identities. Recommendation-audit editorial dispositions do not own execution
progress. Completion-audit corrections belong in the same owning plan.

The source review owns the dated finding and its evidence, identified by `review#Fnn`. Current
execution disposition has **one owner**: the active plan's findings table when scheduled, otherwise
an explicit Deferred row in the source review. On transfer to a plan, link the review to that owner;
preserve the original assessment recoverably in Git and attribute revised judgment. Subsequent reviews and STATUS link to the owner instead of copying
mutable status. Related findings with one structural cause share a remediation row and keep every
source reference. No separate register is introduced.

The plan row records source findings, disposition, responsible component, decision/implementation
links, and closure evidence or revisit trigger. Dispositions are open, in progress, deferred,
closed or superseded. An accepted ADR is a decision, not implementation or closure. Close a finding
only when the named evidence establishes its correction. A closed or superseded row can leave the
plan once the commit that removes the row cites its closure evidence; Git retains it (ADR-0001).

A review's rule impacts (`review#RCnn`) go to plan creation for operator confirmation first;
an accepted change then uses the route below, and a rejected one stays as the plan records it.
An action uses the existing route appropriate to it:

- **ADR + DESIGN** for changed architecture, semantics or a meaningful alternative; accepted
  records are immutable except lifecycle metadata. A proposed ADR can carry an open decision.
- **Implementation/refactor** inside an accepted contract, with the affected owner and deletion
  obligations; no ADR is needed solely to report code movement.
- **Test or `rules/` entry** when a meaningful regression is plausible and a cheap check catches
  it. Keep independent semantic controls independent.
- **Deferred disposition** with scope consequence and the event that reopens it.

| Existing check | Use |
|---|---|
| Compile checks, focused tests/probes | During implementation: validate the scope just implemented |
| `just turn-end` | At the end of a turn that changed files, by the root agent |
| `just hygiene` | Once at scope end, beside `just test-all`; the agent fixes what fails |
| `just rules-scan`, `just rules-test` | A justified code-shape invariant; run within `hygiene` |
| `just adr-lint`, `just lint-agents` | Decision metadata and agent-facing links/commands; run within `hygiene` |
| `just test-all` | Integrated functional acceptance at scope end, not every slice or process edit; qualification also cites `just hygiene` passing for the same tree |

Review quality is established by scenario reasoning and calibration, not by a new checker.

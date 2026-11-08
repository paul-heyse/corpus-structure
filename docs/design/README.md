# Architecture map

Use the [design principles](../design_review/design_principles/core/design-principles.md) and [efficient-architecture heuristics](../design_review/design_principles/core/efficient-architecture-heuristics.md) together
when assessing consequential choices; consider physical realization early alongside ownership
and contracts.

**Mixed implementation maturity (2026-10-29).** The design set below contains accepted targets,
implemented semantic routes and earlier proposed detail. [DESIGN](DESIGN.md) holds scope and
binding decisions; each owner labels its supported boundary. [STATUS](../../STATUS.md) and the
active plan in [plans](../plans/README.md) own current completion claims, evidence and open findings.

## The design set

Read D0 first, then D1 → D2 → D3, which carry most of the risk. The [worked trace](trace.md) is
the spine of the set: four Siegrist units carried through every document as exact data. Spikes
that test the design are in
[design_review/evidence/2026-10-28_design-spikes](../design_review/evidence/2026-10-28_design-spikes/README.md).

| Doc | Question it answers | Detail level |
|---|---|---|
| [D0 Target overview](D0-target-overview.md) | What we build, why the previous architecture failed, the decisions taken | Summary |
| [D1 Knowledge representation](D1-knowledge-representation.md) | What the pipeline produces: evidence, entities, claims, qualifiers, values, conditions, statuses, identity | Full |
| [D2 Schema conventions and statistics pack](D2-schema-and-guidelines.md) | How a domain is declared in LinkML, how one schema compiles into extraction, validation and LLM output, the statistics schema v0 and guideline v0 | Full |
| [D3 Database](D3-database.md) | The PostgreSQL layout of all three levels, JSONB contracts, indexes, run semantics | Full |
| [D4 Method catalog](D4-method-catalog.md) | Every analysis method: inputs, observations, library calls, configuration, outcomes | Cards; library detail to deepen |
| [D5 Consolidation, identity and confidence](D5-consolidation-identity-confidence.md) | How observations become entities and claims, how conflicts and confidence work, validation | Algorithms |
| [D6 Orchestration, metrics and policies](D6-orchestration-metrics-policies.md) | Stage graph, task lifecycle, caching, GPU use, metric definitions, policy rules | Algorithms |
| [D7 Evaluation, goldens and the outer loop](D7-evaluation-goldens-outer-loop.md) | Guidelines, blind golden authoring, alignment and scoring, experiments, the operator's review loop | Protocols |
| [D8 Agent and query interfaces](D8-agent-and-query-interfaces.md) | MCP tools for Opus, work packets, CLI, typed queries | Contracts |
| [D9 Repository and phase 0 plan](D9-repository-and-phase0.md) | Code layout, dependencies, lanes, phase 0 tasks and acceptance | Plan |
| [Worked trace](trace.md) | Four Siegrist units: source, segments, target entities and claims, expected observations | Data |
| [Design rationale](rationale.md) | Why: the operator's intent and constraints, the diagnosis of the old repository, the principles, the alternatives weighed for each area, judgment calls and open concerns | Reasoning (not an authority; D-documents and ADRs win) |

The library-leverage lane deepens D4's **Library realization** subsections; contract changes
arrive as `> Library proposal (L-nn):` blocks, disposed in the [active plan](../plans/design-phase_2026-10-28.md).

## Responsibility map

| Responsibility | Owner document | Code package (D9) |
|---|---|---|
| Scope, binding decisions, deferrals | [DESIGN §1, §2, §13](DESIGN.md) | — |
| Knowledge model types and invariants | D1 | `core` |
| Domain schema language and compilers | D2 | `schema` |
| Storage layout and migrations | D3 | `core.db` |
| Document ingest and segmentation | D4 (M01–M03) | `ingest` |
| Extraction, normalization, resolution methods | D4 | `methods` |
| Observations to claims; confidence | D5 | `consolidate` |
| Constraint and condition checking, domain verifiers | D5 | `validate`, `domains/<name>` |
| Stage graph, tasks, policies, metrics | D6 | `orchestrate` |
| Goldens, alignment, scoring, experiments | D7 | `evaluate` |
| Agent and human intervention tools | D8 | `intervene` |
| Query surface and exports | D8 | `serve` |
| The `ci` command line | D8 §4 | `cli` |

**Dependency direction** (D9 §1). `core` ← `schema` ← `validate`; (`ingest`, `methods`) ←
`consolidate` ← `orchestrate` ← (`evaluate`, `serve`) ← `intervene` ← `cli`, with `consolidate`
using `validate`. A package imports only packages to its left. `domains/<name>` holds data (schema,
guideline, policies, rules with `views:`) plus plug-ins: verifiers implementing a `validate`
interface and domain queries implementing a `serve` interface. Source profiles live in
`sources/<profile>.yaml`, apart from any domain.

This table describes intended ownership; it is not a certificate of current architectural
conformance.

## Trace a result through the code

- [Source capture](../../python/corpus-structure/src/corpus_structure/ingest/pdf_section_views.py) · [Source-view SQL](../../python/corpus-structure/src/corpus_structure/semantic/sql/source_views.sql)
- [GLiNER observations](../../python/corpus-structure/src/corpus_structure/methods/gliner.py) · [Typed contextual links](../../python/corpus-structure/src/corpus_structure/semantic/contextual_links.py)
- [Reader queries](D8-agent-and-query-interfaces.md) · [MCP](../../python/corpus-structure/src/corpus_structure/cli/mcp.py) · [Operation assessment](../../python/corpus-structure/src/corpus_structure/evaluate/operation_assessment.py)

Docling and the managed Nemotron Parse 3.5 path support the demonstrated PDF intake.
GLiNER supplies retained extraction observations. Finite interpretation and fitting
have their own implemented scope. Graphical-model and probabilistic-programming
extensions using pgmpy and Pyro remain research questions. Chandra has verified
explicit inspection, with governed promotion a separate proposed step.
[Scope and model roles](../functional_reviews/github-visitor-experience_2026-11-08.md#O03)

## Reading and extending

For a change, identify the semantic owner, its consumer contract and the expected extension axis.
Read that owner plus affected consumers, then the ADR that governs the section
([index](../adr/README.md)); reuse or compose existing capabilities where their semantics fit.
Detailed fields and invariants belong in executable declarations once code exists; until then the
D-documents carry them. Update the owner when meaning or boundaries change. Section IDs never
renumber; a moved live section keeps a relocation pointer, and retired material is recovered from
Git ([historical recovery](../README.md#historical-recovery)).

## Conventions used in the D-documents

- **Labels.** Each document's label applies to all its content unless a line says otherwise. A
  section may carry its own maturity and evidence label. Use the dated checkpoint for
  current qualification and the owning section for the architectural contract.
- **Open questions** are marked `OPEN-Dn-k` inline and collected in the active plan's findings
  table, which owns their disposition.
- **Library proposals** from the library-leverage lane are marked `> Library proposal (L-nn):`
  inline until the design owner accepts or rejects them (see the active plan).
- **Names.** Code identifiers are `snake_case`; schema classes are `PascalCase`; predicates are
  `snake_case` and namespaced by domain prefix in storage (`stat:has_distribution`).

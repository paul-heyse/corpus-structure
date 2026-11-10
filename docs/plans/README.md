# Plans

Plans live here, named `<topic>_<YYYY-MM-DD>.md`. The plans below own distinct scopes. The
original three ownership boundaries follow the operator decision of 2026-10-28; the dedicated
semantic pivot series was added on 2026-10-29:

| Plan | Owns |
|---|---|
| [Agent CLI and diagnostics](cli-and-logging_2026-11-10.md) | Planned CLD-00–10: O01–O08, all ten discovery leads and conditional decisions; focused native references, invocation explanation, correction/replay, scoped structured observations, correlation and progress. Execution follows DMC-17 and precedes PM2. |
| [Integrated domain-data-model capabilities](domain-data-model_2026-11-10.md) | Proposed DMC-00–17 and DMC-I01–09: full November10 functional-review scope, bounded branch decisions and selected delivery across authoring, archives, terminology, measurements, diagnostics and independent consumers. Execution follows completed PTD-11 and precedes PM2. |
| [design-phase](design-phase_2026-10-28.md) | Design findings and the disposition of OPEN items; the design queue |
| [design-spikes series](design-spikes-s0-s1_2026-10-28.md) | Spike execution, spike evidence and its findings |
| [phase 0 series](phase-0_2026-10-28.md) | The production build of phase 0 and its findings |
| [semantic-model pivot](semantic-model-pivot_2026-10-29.md) | Semantic pivot packages, completeness and improvement extensions (SP-I01–SP-I09), and their dependencies; existing phase-0 finding ownership is preserved |
| [production efficiency](production-efficiency_2026-10-30.md) | Model-governed production analysis, data/runtime efficiency and review F01–F11; planned PE-00–PE-12, with existing pivot completion preserved |
| [parsing pipeline](parsing-pipeline_2026-10-30.md) | Planned PP-00–PP-10: complete original/canonical decomposition, connected parsing contracts, native adapters, interpretation, views and adoption; parsing-review O01–O07 disposition |
| [PDF/Docling pipeline](pdf-docling-pipeline_2026-10-31.md) | PDF-00–PDF-28 (PDF-26 conditional): native/triple-pass baseline, relational streaming, shared PostgreSQL/Arrow payload/validation amendments and RC12 current-product adoption; source-qualified review dispositions and I01–I25 |
| [PostgreSQL capability leverage](postgresql-capability-leverage_2026-11-01.md) | Completed PG-00–PG-12 series (targeted319-case qualification): execution outcomes, typed preparation/transfer, native Alembic extensions, analytical/operator/selected-source consumers; review O01–O15 and PG-I01–03 |
| [PostgreSQL typed-domain series](postgresql-typed-domain_2026-11-09.md) | Planned PTD-00–11 and PTD-I01–06: released types, SQL explanations, exact retrieval, faithful exchange, native inspection/evolution and bounded branch decisions. Owns the November9 functional review O01–O13; separate from PM2, awaiting current-tranche handoff. |
| [Test architecture and evidence](test-architecture-and-evidence_2026-11-02.md) | Proposed TA-00–TA-12: all20 test-audit dispositions, native system/library comparison, lifecycle and qualification, scenario preparation, independent semantic/reference and real interface evidence; existing UM/PDF acceptance ownership preserved |
| [Test audit resolution](test-audit-resolution_2026-11-05.md) | Original TR-00–10 evidence and incomplete qualification; Proposed TR-11–15 tooling amendments, distributed harness, independent WCE case support and conditional native comparisons |
| [Audit closure](audit-closure_2026-11-03.md) | Completed selected AC00–AC14 scope2026-11-04; final105 acceptance and M1 handoff at §15; existing DA dispositions retain their plans |
| [First production milestone](first-production-milestone_2026-11-03.md) | Superseded for remaining scope by progressive enrichment; historical M1 package state, five-family targets and receipts retained without claiming completion |
| [Progressive corpus enrichment](progressive-corpus-enrichment_2026-11-04.md) | Planned PCE-00–PCE-11: independent structural contributions, operation assessment, local qualification, parsing/mathematics, contextual embeddings/linking, cross-document products and review export; progressive-review O01–O10/RC01–08 and transferred M1 obligations; execution stopped |
| [CLI operations and managed results](cli-operations_2026-11-07.md) | Proposed CLI-00–CLI-08: installed command surface, recipe integration, managed results, tests, controlled model changes, corpus journeys and operational adoption. Owns O01–O07 and improvement review I01–I10, including Typer 0.28.0 and bounded diagnostics. |
| [CLI reporting](cli-reporting_2026-11-07.md) | Audit repairs verified on main with targeted functional and native checks. CLIR-01–08 cover bounded reports, test evidence, managed model and corpus reads, recipe diagnostics, stream behavior and file-free workflows. Owns reporting review O01–O07. |
| [Next corpus enrichment](next-corpus-enrichment_2026-11-07.md) | Proposed NCE-01–12: caption and role recovery, witnessed links, artifact scoring, rooted navigation, finite interpretation, operation reliability and review O01–O12 dispositions. |
| [Chandra 2 after Nemotron](chandra-2-post-nemotron_2026-11-08.md) | Proposed CH-01–07: Docling upgrade, opt-in visual evidence, and gated recovery, specialist consumer and runtime investigations. Owns the Chandra review O01–O09 dispositions. |
| [Domain-model alignment](domain-model-alignment_2026-11-08.md) | Proposed DMA-00–13 for the November 8 review. Covers release and target authority, semantic admission, source projection, operational custody, visual evidence and integrated qualification. |
| [Production milestone two](production-milestone-two_2026-11-08.md) | PM2-00–12: private development and proposed domain-agnostic extraction, contextual retrieval, composition and release qualification on Grinstead–Snell. Owns O01–O09 and the [GLiNER2/spaCy dispositions I01–I10](production-milestone-two_2026-11-08.md#extraction-improvement-disposition), and the [structuring and DMA-13 dispositions](production-milestone-two_2026-11-08.md#structuring-improvement-disposition), including [conditional learned investigations](production-milestone-two/learned-extraction-investigations.md). |
| [GitHub visitor experience and Pages](github-visitor-experience_2026-11-08.md) | Complete and live. [GHV-07–11](github-visitor-experience_2026-11-08.md#ghv-follow-on-acceptance) add verified exhibits, publication corrections, visitor navigation and presentation. Owns all GHV findings. |


[Witnessed corpus enrichment](witnessed-corpus-enrichment_2026-11-05.md) is the new Proposed series
for the audited enrichment target: WCE00–12, F01–F07/RC01–RC06, concrete library realization,
source/reference expansion and conditional interpretation/identity challengers. It preserves the
selected PCE completion and the separate test-resolution execution owner.

The [phases 1–5 roadmap](roadmap-phases-1-5_2026-10-28.md) is not an execution plan: it says what
each later phase adds and what decides it, until its detailed plan is written. Cross-references
between plans cite package ids and evidence record ids, never copied status. An active plan owns
execution and the current disposition of its scheduled findings. When it is finished or superseded, its remaining obligations
move to the next owner and its status line says so; **the file is never deleted** (operator
direction, 2026-10-28; see `AGENTS.md`).

A plan usually has:

- **Status and authority:** `**Status:** Active; owns <scope>. **Revised:** <date>`.
- **Current state and qualification boundary:** what is implemented, what is verified, what is not.
- **Execution queue:** ordered slices, each with its responsible component and verification.
- **Findings disposition:** the single current owner for scheduled findings, one row each, with
  `| Item | Component | Consequence and intended correction | Disposition · dependency | Closure check |`.
  Rows keep their source-review IDs (`review#F01`); dispositions are open, in progress, deferred,
  closed or superseded. A row leaves once the commit that removes it cites its closure evidence.
- **Deferred, each with a trigger:** `| Item | Trigger |`.
- **Risks** and **standing conventions** that the plan relies on.

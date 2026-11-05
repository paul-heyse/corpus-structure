# Plans

Plans live here, named `<topic>_<YYYY-MM-DD>.md`. The plans below own distinct scopes. The
original three ownership boundaries follow the operator decision of 2026-10-28; the dedicated
semantic pivot series was added on 2026-10-29:

| Plan | Owns |
|---|---|
| [design-phase](design-phase_2026-10-28.md) | Design findings and the disposition of OPEN items; the design queue |
| [design-spikes series](design-spikes-s0-s1_2026-10-28.md) | Spike execution, spike evidence and its findings |
| [phase 0 series](phase-0_2026-10-28.md) | The production build of phase 0 and its findings |
| [semantic-model pivot](semantic-model-pivot_2026-10-29.md) | Semantic pivot packages, completeness and improvement extensions (SP-I01–SP-I09), and their dependencies; existing phase-0 finding ownership is preserved |
| [production efficiency](production-efficiency_2026-10-30.md) | Model-governed production analysis, data/runtime efficiency and review F01–F11; planned PE-00–PE-12, with existing pivot completion preserved |
| [parsing pipeline](parsing-pipeline_2026-10-30.md) | Planned PP-00–PP-10: complete original/canonical decomposition, connected parsing contracts, native adapters, interpretation, views and adoption; parsing-review O01–O07 disposition |
| [PDF/Docling pipeline](pdf-docling-pipeline_2026-10-31.md) | PDF-00–PDF-28 (PDF-26 conditional): native/triple-pass baseline, relational streaming, shared PostgreSQL/Arrow payload/validation amendments and RC12 current-product adoption; source-qualified review dispositions and I01–I25 |
| [PostgreSQL capability leverage](postgresql-capability-leverage_2026-11-01.md) | Completed PG-00–PG-12 series (targeted319-case qualification): execution outcomes, typed preparation/transfer, native Alembic extensions, analytical/operator/selected-source consumers; review O01–O15 and PG-I01–03 |
| [Test architecture and evidence](test-architecture-and-evidence_2026-11-02.md) | Proposed TA-00–TA-12: all20 test-audit dispositions, native system/library comparison, lifecycle and qualification, scenario preparation, independent semantic/reference and real interface evidence; existing UM/PDF acceptance ownership preserved |
| [Audit closure](audit-closure_2026-11-03.md) | Completed selected AC00–AC14 scope2026-11-04; final105 acceptance and M1 handoff at §15; existing DA dispositions retain their plans |
| [First production milestone](first-production-milestone_2026-11-03.md) | Superseded for remaining scope by progressive enrichment; historical M1 package state, five-family targets and receipts retained without claiming completion |
| [Progressive corpus enrichment](progressive-corpus-enrichment_2026-11-04.md) | Planned PCE-00–PCE-11: independent structural contributions, operation assessment, local qualification, parsing/mathematics, contextual embeddings/linking, cross-document products and review export; progressive-review O01–O10/RC01–08 and transferred M1 obligations; execution stopped |

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

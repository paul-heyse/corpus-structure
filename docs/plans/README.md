# Plans

Plans live here, named `<topic>_<YYYY-MM-DD>.md`. The plans below own distinct scopes. The
original three ownership boundaries follow the operator decision of 2026-10-28; the dedicated
semantic pivot series was added on 2026-10-29:

| Plan | Owns |
|---|---|
| [design-phase](design-phase_2026-10-28.md) | Design findings and the disposition of OPEN items; the design queue |
| [design-spikes series](design-spikes-s0-s1_2026-10-28.md) | Spike execution, spike evidence and its findings |
| [phase 0 series](phase-0_2026-10-28.md) | The production build of phase 0 and its findings |
| [semantic-model pivot](semantic-model-pivot_2026-10-29.md) | Semantic pivot packages, completeness extensions and their dependencies; existing phase-0 finding ownership is preserved |

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

# Plans

At most one **active plan** lives here, named `<topic>_<YYYY-MM-DD>.md`. It owns execution and the
current disposition of scheduled findings; when it is finished or superseded, its remaining
obligations move to the next owner and the file is deleted (Git holds it).

A plan usually has:

- **Status and authority:** `**Status:** Active; the sole execution plan. **Revised:** <date>`.
- **Current state and qualification boundary:** what is implemented, what is verified, what is not.
- **Execution queue:** ordered slices, each with its responsible component and verification.
- **Findings disposition:** the single current owner for scheduled findings, one row each, with
  `| Item | Component | Consequence and intended correction | Disposition · dependency | Closure check |`.
  Rows keep their source-review IDs (`review#F01`); dispositions are open, in progress, deferred,
  closed or superseded. A row leaves once the commit that removes it cites its closure evidence.
- **Deferred, each with a trigger:** `| Item | Trigger |`.
- **Risks** and **standing conventions** that the plan relies on.

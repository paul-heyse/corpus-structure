# Final-source actual automated source journey

**Passed, 2026-11-04 UTC (2026-11-03 local).** The existing authenticated automation probe ran
against the current main checkout after root maintenance and queue-mode repair. Root granted the
sole shared native database slot. No historical receipt was overwritten.

Command:

```sh
uv run python docs/design_review/evidence/2026-11-03_automated-source/automation_journey.py --checkout /home/paul/corpus-structure --receipts docs/design_review/evidence/2026-11-03_ac14-acceptance/automated-source
```

`command.json` retains argv, HEAD and SHA256 witnesses for the queue server, producer binding and
probe. All witnesses matched after execution. `journey.log` retains complete output, including
nonfatal schema-authoring diagnostics. The process exited0.

`attempt-20261104T013903Z-9a1b069a/result.json` records actual authenticated Claude CLI → run-bound
MCP → current protected native completion. The owned scenario produced run1/task2, terminal `done`
and one retained proposal report. The probe independently checks equal nonempty lease/completion
producer bindings and exact native task/attempt receipts. Configured versus provider-reported
identity retains the existing distinction; this is provider-reported execution, not artifact
verification. The scenario's PgAdmin contexts disposed their owned databases before successful
return. No application/default selection or shared server configuration changed.

This is one actual automated producer journey. It does not establish the full AC14 union,
managed-recognition generation custody, M1 accuracy, CPU resources or a released corpus.

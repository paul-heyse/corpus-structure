# Actual automated source extraction

2026-11-03, AC08/AC14. `automation_journey.py` uses the existing authenticated Claude CLI,
a fresh owned native test deployment, controlled published PDF SourceView, the actual
`extract_run` process/MCP route and the native attempt/terminal effect owner. Authentication
readiness is retained without account identifiers or credentials. The configured model alias,
provider-reported identity, invocation/session and exact native task/attempt/holder remain
separate in receipts. Raw refused, failed or interrupted attempts remain evidence; a script
exit or textual model answer alone does not establish native completion.

Run with the checkout's local environment: `uv run python automation_journey.py` (absolute
script path), from the repository root. The root coordinator owns final source/context and
assembled qualification; this retained probe establishes only the actual journey it records.

**Tested · 2026-11-03:** the initial actual authenticated journey reached native task completion,
then inspection exposed that its completion event omitted the producer binding despite retaining
it in the lease event and committed report diagnostics. Its raw `runtime/result.json` describes
that narrower native success; it does not close the attribution obligation. The completion event
now carries the binding returned from the exact committed proposal. Both declared producer routes
and receipt controls passed7 cases in `raw/provider-binding-native-7.log`.

`runtime/attempt-20261103T234813Z-50cf0327/result.json` records the corrected actual journey:
configured alias `opus`, provider-reported model usage `claude-opus-5-5`, session
`eafcb003-b397-4c61-9b7e-432dc99f2a6d`, task2/attempt1 and native protocol `done` with one retained
claim-proposal report. The probe independently requires equal nonempty lease/completion producer
bindings and matching receipt task/attempt. The configured and reported identities remain distinct;
this establishes `provider_reported` execution, not managed local artifact custody. The fresh owned
database was disposed after receipt capture. The retained branch release uses semantic-6; the
root's final integrated release/model/native context still requires its declared qualification.

Actual mutating MCP image delivery is separately exercised by `raw/inline-image-native.log`:
the tool creates/retains a native render artifact, returns an image within the admitted encoded
response budget, and returns an explicit error disposition plus committed artifact/fence references
when inline delivery would exceed it. Scalar retained byte length and exact base64/result-envelope
size are admitted before selecting artifact content; the actual final CallToolResult is checked
again. The minimum inline budget1024 permits a reference-only refusal, default1MiB/max8MiB. A replay
control confirms oversized delivery performs no artifact-content SELECT. The original source-schema
fixture failure and typing failures remain in `raw/`; scoped production Ruff and Pyrefly0errors
passed after correction. Source creation and passive read budgets remain separate owners.

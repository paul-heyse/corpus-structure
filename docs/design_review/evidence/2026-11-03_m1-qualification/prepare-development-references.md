# Development reference session helper

**Prepared, 2026-11-03. Database execution not run; root GO is required while native101
qualification has the sole database slot.**

Local readiness check (reads only the retained manifest, paragraph and root guideline):

```sh
uv run python docs/design_review/evidence/2026-11-03_m1-qualification/prepare_development_references.py --check-inputs
```

After root GO, run in a persistent stdin/PTY session with a new evidence output directory:

```sh
uv run python docs/design_review/evidence/2026-11-03_m1-qualification/prepare_development_references.py --execute --output docs/design_review/evidence/2026-11-03_m1-qualification/development-reference-session-001
```

The helper takes a read-only PostgreSQL18 custom dump of `corpus_pdf_20261102` through the existing
`sudo -n -u postgres` identity, then restores into one freshly stamped `PgAdmin` database created
from `template0`. Restore retains object owners/ACLs and targets only that owned name; it uses no
create, clean or ownership-stripping option. Existing database policy is replayed through the
shared lifecycle. Only the owned copy is upgraded to `semantic_m1_records_20261103`. Existing
archives are compared byte-for-byte by hashes and opened through the current archive reader.

The helper prepares and admits the exact current statistics pack, initializes a fresh source
realization, authenticates retained `task6/integrated/1882a372…`, and runs the M1 graph's existing
ingest-only form on `#/groups/4265`. It selects the one paragraph `[29,468)` from retained view5,
using actual projection/native citation addresses. The original PDF exists under
`docs/statistics_corpus/corpus/siegrist_random/Full_PDF/Full.pdf`; this route reuses its copied
registered document and retained source-artifact custody rather than registering it again.

The protected source-only packet, released response schema, frozen frame, target paragraph and
root-authored guideline are emitted before the helper prints `status=ready`. It authors no
expected records. Siegrist is assigned only to the development partition; the selection is
purposive. All five families must be inspected, and any family may have no eligible reading.

Send one JSON command per stdin line after writing fresh Sol author files:

```json
{"action":"submit","pass":"A","actor":"gpt-6.1-sol-high-A","path":"/absolute/path/A.json"}
{"action":"submit","pass":"B","actor":"gpt-6.1-sol-high-B","path":"/absolute/path/B.json"}
{"action":"agreement"}
{"action":"packet-c"}
{"action":"submit","pass":"C","actor":"gpt-6.1-sol-high-C","path":"/absolute/path/C.json"}
{"action":"close"}
```

`packet-c` emits the existing adjudication packet, retaining exact A/B JSON strings, their pass
identities/digests and deterministic disagreement. Pass submissions call the existing protected
`record_pass`; authored bytes and receipts remain in the output directory. A failed command
closes the session with failure evidence. EOF or close disposes the owned database and removes
only the helper-created ignored `build/m1-dev-reference-*` dump directory. The receipt retains
the dump digest/size; no database archive is written to evidence or Git.

This session establishes development reference authoring only. Its paragraph-scoped frame sits
over a complete section view. The current grader loads predictions for the whole view and can
reject out-of-frame predictions, so this helper does not grade a whole-view candidate run or
claim model quality, release qualification, recall or capture. Final-cut grading needs its own
supported source-unit/region scope. Live native99, run6/tasks27–31 and defaults are untouched.

Execution prerequisites remain: settled native101 and matching current code/pack, the dedicated
18/corpus cluster on socket5434, existing peer purpose roles, operator-owned source database
policy replayable through `PgAdmin`, noninteractive sudo for the two PostgreSQL commands,
PostgreSQL18 clients/extensions, enough copy space, and source archives accepted by the current
read boundary. The helper fails through existing owners if those premises do not hold.

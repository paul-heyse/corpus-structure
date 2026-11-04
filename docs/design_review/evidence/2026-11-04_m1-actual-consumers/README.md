# Actual M1 consumers over frozen native124

**Tested, 2026-11-04; bounded live candidate and retained-source journeys.** This evidence folder belongs to
M1-12 in `docs/plans/first-production-milestone/publication-and-consumer-adoption.md` and
ADR-0059. It compares the same actual persisted result across existing query, CLI, registered
MCP, support export, and detached JSONL/Parquet consumers. It supplies no independent expected
scientific semantics and establishes neither reading quality nor milestone completion.

The selected release is
`release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd`, frozen
native124. Reads use the actual `corpus_sem_reader` principal on `corpus_structure_dev` through
the existing purpose credential route and dedicated PostgreSQL cluster. No project/global
selection, source product, database bootstrap, dependency, model, PDF or OCR change is made.
Independent-reference author output, passes, goldens and grades are not inputs and were not read.

## Method and commands

`run_consumers.py` opens the actual read runtime and native snapshot, requests the common
`RecordPage`/`RecordSupportPage`, invokes actual `uv run ci records list`, `support` and `export`
subprocesses, and calls the registered `records`, `record_support` and `inspect_source` MCP tools
using `Client(server)`. The MCP server uses a real reader engine; no tool implementation or
database response is mocked. This is in-process MCP transport, not HTTP, a host attachment,
an external agent session, or a registered MCP resource journey. `call_tool_mcp` retains the
complete SDK result including text, structured content and server metadata. The registered
tool names above are the current source API names.

Commands run from the repository root:

```bash
uv run python docs/design_review/evidence/2026-11-04_m1-actual-consumers/run_consumers.py --run 11 --output source-only-11-001 --completed-receipt docs/design_review/evidence/2026-11-04_m1-cpu-readings/source-only-001/grinstead-snell/completed-result.json
uv run python docs/design_review/evidence/2026-11-04_m1-actual-consumers/run_consumers.py --run 12 --output source-only-12-001 --completed-receipt docs/design_review/evidence/2026-11-04_m1-cpu-readings/source-only-001/forbes-statistical-distributions/completed-result.json
uv run python docs/design_review/evidence/2026-11-04_m1-actual-consumers/run_consumers.py --run 13 --output source-only-13-001 --completed-receipt docs/design_review/evidence/2026-11-04_m1-cpu-readings/source-only-001/nist-ehandbook/completed-result.json
uv run python docs/design_review/evidence/2026-11-04_m1-actual-consumers/inspect_custody.py --completed-receipt docs/design_review/evidence/2026-11-04_m1-cpu-readings/source-only-001/grinstead-snell/completed-result.json --output native-custody-gs-001
uv run python docs/design_review/evidence/2026-11-04_m1-actual-consumers/inspect_custody.py --completed-receipt docs/design_review/evidence/2026-11-04_m1-cpu-readings/source-only-001/grinstead-snell/completed-result.json --output native-custody-gs-002 --max-bytes 8388608
uv run python docs/design_review/evidence/2026-11-04_m1-actual-consumers/run_consumers.py --run 14 --output actual-gs-14-001 --completed-receipt docs/design_review/evidence/2026-11-04_m1-cpu-readings/attempt-011/completed-result.json
uv run python docs/design_review/evidence/2026-11-04_m1-actual-consumers/check_historical_pin.py
uv run python docs/design_review/evidence/2026-11-04_m1-actual-consumers/check_diagnostics_cli.py
uv run python docs/design_review/evidence/2026-11-04_m1-actual-consumers/complete_census.py
```

Each command's expanded actual CLI commands, exit codes, stdout, stderr, query values, MCP
requests and whole SDK response JSON are retained under `raw/<output>/`. `context.json` records
Python and installed FastMCP/MCP/SQLAlchemy/PyArrow versions. Exports remain as actual detached
files with their native manifests and SHA256 values. Query-versus-export comparisons cover
all declared record relations, including exact lexical values where present. Native source
requests carry task/product/content digest and the completed run; source continuations retain
that selection and a changed pin is refused.

Library route: Context7 `/prefecthq/fastmcp`, client raw-result contract and in-process client,
then installed repository adapters. The docs distinguish `call_tool_mcp`'s raw MCP result from
the client convenience result. The probe relies on the installed raw result serializer to
count the actual SDK envelope.

## Current observations

| Result | Binding | Outcome and limit |
| --- | --- | --- |
| Source-only Grinstead/Snell | run11, cut7, revision1 | Query/CLI/MCP/support-export and both detached export relation comparisons passed. Two initial harness comparisons failed because they compared the independent export capture UUID to reader capture `cut:7`; the preserved semantic-binding followup passed. |
| Source-only Forbes | run12, cut9, revision1 | Passed the selected live consumer comparisons; 0 records, 1 empty source report, 0 producer-coverage rows. |
| Source-only NIST | run13, cut11, revision1 | Passed the selected live consumer comparisons, including actual source CLI equality; 0 records, 1 empty source report, 0 producer-coverage rows. |
| Selected retained native custody | Source-only GS pin | At 1MiB, cell/trace MCP whole-envelope refusals and formula context-read refusals retained. At the existing 8MiB ceiling, all six selected native query/CLI/MCP reads passed. Separate from candidate-field handoff. |
| Actual CPU Grinstead/Snell | run14, cut13, revision1 | Passed selected query/CLI/registered MCP, support, field/native handoff and both export formats. Candidate-only output: 364 table + 100 definition interpretations. Original 102-interpretation pagination receipt remains partial; separate continued census completes all 464 identities. |
| Historical source-only result after CPU publication | run11/cut7 after run14/cut13 | Passed: the complete CLI page equals the prepublication query page. No selected/default result was moved. |

Source-only results have no candidate records and no extraction-producer coverage. Their empty
record pages correctly retain `source_coverage=not_established_by_record_projection`; one empty
source report does not establish five-family inspection or inspected-empty extraction.
`scientific_support_opposition.availability` is `unmodeled`, with
`no_released_scientific_proposition_projection`, as ADR-0059 requires. No zero opposition count
or scientific comparison is inferred.

Run11's complete MCP record response was 13,425 bytes and support response 14,853 bytes. Both
were admitted at the normal 1MiB interactive budget and refused at their exact envelope size
minus one, while their semantic bodies were smaller. The typed refusal retains
`oversized_item` and the full-envelope reason. Native source item pagination and changed-pin
refusal passed. Ordinary diagnostics omission and explicit inclusion for these source-only
results are vacuous because no producer coverage is present.

The first-run capture comparison defect is in the probe, not evidence of a product defect.
`raw/source-only-11-001/summary.json` remains unchanged with both failed comparisons.
`raw/source-only-11-export-binding-followup.json` compares release/realization/revision and the
record run/cut, retaining the distinct capture IDs. Later probe runs also require the exported
record projection digest. The probe was extended after run12 to add actual source CLI equality
and record detail/CLI continuation when output exists; earlier receipts cover only operations
they actually contain.

The GS native inventory contained 506 retained items, including 1 table and 49 formula items.
The selected native reads were the table's first cell and its trace, plus the first two formula
occurrences and their traces. The cell retained blank text, native cell index and header flags;
no missing value was invented. Formula view retained original/recognized text, recognition
standing, interpretation metadata and PDF regions. Native traces retained available parent and
derivation/alignment custody. These comparisons assess equality between actual transports;
they do not independently establish recognition or interpretation correctness.

The original 1MiB custody probe retains four failed delivery assertions: the table cell and
trace produced query/CLI bodies of 644,791 and 645,066 bytes, but registered MCP correctly
refused their larger text-plus-structured envelopes; the two formula views refused during query
hydration. Most table response bytes are the attached companion rather than the cell row.
The formula refusal comes through `_recorded_interpretations` → `stored_native_analysis` →
`load_source_view` → `integrated_source_context` → the published-source budget preflight.
At 8MiB, formula response bodies were only 9,735 and 9,732 bytes and all selected query/CLI/MCP
values matched. This is a whole-source-view hydration usability limitation: a small final formula
response can require a much larger allowed read. No product fix was attempted in the frozen run.
The original failures remain unchanged under `raw/native-custody-gs-001`; the successful followup
is `raw/native-custody-gs-002/summary.json`.

## Actual CPU result

The coordinator published the completed CPU result under run 14 / cut 13 with the same frozen release,
realization `m1-result:14:<release-id>` and revision 1. `raw/actual-gs-14-001/context.json` records
source hashes for the probe and relevant production consumers, along with installed library
versions (Python 3.14.10, FastMCP 4.1.3, MCP 2.3.0, SQLAlchemy 2.1.6, PyArrow 26.0.0). The explicit
reader identity is retained in `database-identity.json`.

The finite record projection has 464 interpretations, all carrying `candidate` admission:
364 table and 100 definition. No formula_context, measurement or assertion family record output
is present. All 19 declared record relations, including 2,808 anchors, 500 source-reading
assertion rows and 964 assertion-support rows, compare exactly between query and the actual CLI's
detached JSONL and Parquet exports. Source-reading assertion/support rows do not establish
accepted reading or scientific support. Each export carries its own capture UUID and the same
release/realization/revision plus record run/cut/projection identity. Export source payloads are
explicitly excluded; selected native reads retain their separate scope.

The initial two-record page and support ledger match query, CLI and registered MCP, including
record detail, CLI support JSON export and first CLI continuation. Fifty further query/MCP page
transitions preserve binding and produce 102 distinct interpretations; the probe stops at its
declared 51-page bound with a continuation still available. That is partial pagination coverage,
not a claim to enumerate all output interactively. The detached relation comparison covers the
whole actual finite projection. Changing a normalized family selection while reusing the
continuation produces a typed refusal.

The coordinator then authorized a complete identity census from the saved continuation,
without repeating those first 51 pages. `complete_census.py` resumes after interpretation 102
with limit 20 and an 8 MiB page budget; these presentation bounds are excluded from normalized
selection meaning. Nineteen further query/MCP page transitions return the remaining 362
interpretations and terminate with no continuation. All 464 identities occur exactly once,
with no omission or extra identity relative to the full query projection or either existing
JSONL/Parquet export. The first resumed page also matches the actual CLI. Every complete MCP
envelope fits its requested 8 MiB bound; the largest is 1,187,069 bytes. Each full SDK response
and its byte size is retained.
The original `actual-gs-14-001` receipt remains partial at its own declaration; the complete
followup is `raw/actual-gs-14-census-001/summary.json`.

Actual record and support MCP envelopes were 604,535 and 621,253 bytes, admitted at 1 MiB and
refused at their exact whole-envelope sizes minus one. Six producer-coverage entries retain
selected/origin task locators 34–39, actual done/empty states, separate `records_present`, and
`diagnostics_available=true` with `diagnostics_included=false` and no diagnostic body. Explicit
diagnostic requests refuse at a 1 KiB projection budget; at 32 MiB projection allowance they still
refuse the default 1 MiB response page. Both refusals are retained through query and registered MCP.
The actual explicit-diagnostics CLI followup passed with exit 1 and a structured `RecordReadLimit`
response naming the page byte budget; its stdout and stderr are separately retained.

The inspected support page has 16 source-reading fields marked `not_admitted`; scientific
support/opposition remains `unmodeled`. Four native requests produced from representative table
and definition record evidence preserve run 14, native task 1, integrated product and digest
`e8ee2f72912fe174fdaf76918b7cb347ad245fecdf9c827688814729b9961cba` through query, CLI and MCP:
item `#/texts/273`, cell 3 of `#/tables/0`, scope item `#/groups/1` and item `#/texts/24`.
They use the existing 8 MiB request ceiling after the separate default-budget custody investigation.
The cell's complete MCP envelope is 1,371,563 bytes, so 1 MiB cannot deliver it. This establishes
handoff from actual candidate evidence to native source. Evidence correctness and accepted-family
qualification remain separate. Source custody includes available retained companion lineage; no new child or
recognition work is run.

## Remaining live obligations

The selected actual candidate result consumers have passed their bounded journeys, with the
full identity census completed through the separate continuation followup and retained refusal
paths above. Candidate-backed transport
fidelity does not establish accepted source-reading quality. Actual accepted field facts and
their support/citation/assessment ledger remain **blocked** on an evaluated accepted result.
The missing three family output journeys remain **not_run**, pending actual output. A selected
project/global default transition between actual pinned calls remains **not_run**; only the
coordinator's existing controlled-native evidence and this later-publication historic reread
cover their respective, narrower boundaries. No default change was authorized here.

Five-family quality, calibration, independent-reference agreement, actual resource qualification,
failure/recovery, complete required union and final M1 adoption remain with their existing owners.
No broad product tests, qualification or hygiene commands run in this worker assignment.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 1 current, 0 superseded.


**M1**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Actual candidate query CLI MCP source and export journeys](records/m1.actual-candidate-consumers124.json) | M1-12 | passed | — | 2026-11-04 |
<!-- evidence-index:end -->

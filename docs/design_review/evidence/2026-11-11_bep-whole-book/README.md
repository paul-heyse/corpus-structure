# BEP09 whole-book retained consumer verification

**Prepared · 2026-11-11. Execution: not_run.** The coordinator owns qualification and final
outcomes in [BEP-09](../../../plans/book-processing-efficiency-and-parallelism_2026-11-11.md#BEP-09).
This folder supplies the bounded verification utility; the root runs it only after the final
book pin is available. It makes no accuracy, recognition-completeness or speed claim.

`verify_consumers.py` uses ordinary reader authority, the native enriched-document API, installed
`ci source enriched`, and a fresh actual FastMCP server/client session. It performs no inference,
provider mocking, result selection, promotion, scheduling or protected-reference reads. Its only
inputs are an explicit final run/view binding and the actual retained products reachable from it.

## Explicit binding

Supply `binding.json` containing these fields. Copy `run_id` and the entire `view` triple from the
actual final combined result; the script never queries a latest run or substitutes another pin.

| Field | Required value |
| --- | --- |
| `project` | `nce-grinstead-snell-full-book` |
| `run_id` | Exact positive selected/producing final run integer |
| `view` | Exact object with `task_id`, `product_key`, `content_digest` |
| `source_run_id` | `496` |
| `source_cut_id` | `614` |
| `source_view_count` | `316` |
| `native_pages` | `518` |
| `base_document` | The object below |

```json
{"task_id":1627,"product_key":"integrated","content_digest":"35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb"}
```

## Root execution

Run from the repository root, with the final source and intended database environment retained.
Choose a new `--output` directory for each preparation/live attempt so failed records survive.
The commands below use `consumers/attempt001` within this folder.

```sh
uv run python docs/design_review/evidence/2026-11-11_bep-whole-book/verify_consumers.py prepare --binding docs/design_review/evidence/2026-11-11_bep-whole-book/binding.json --output docs/design_review/evidence/2026-11-11_bep-whole-book/consumers/attempt001 --export-max-bytes 8589934592
uv run python docs/design_review/evidence/2026-11-11_bep-whole-book/verify_consumers.py live --binding docs/design_review/evidence/2026-11-11_bep-whole-book/binding.json --output docs/design_review/evidence/2026-11-11_bep-whole-book/consumers/attempt001
```

Preparation reads the exact protected view/manifests and completed capture. It checks that all316
original source IDs are present and each has exactly one active layer from all six primary
producers. `native-facts.json` retains source IDs, producer accounting, original native health and
family outcome/availability totals. Selector counts describe eligible/examined/unexamined scope,
not page, token or accuracy totals. Full per-layer coverage rows retain partial/failed reasons in
`active-layer-manifests.json`. If native health lacks an exact page range, the518-page context is
reported `blocked`, rather than inferred from the view count.

Preparation selects summary, fully paginated coverage and bounded native/formal annotations.
Within the first eight actual native/construction layers and eight matching nodes per layer, it
also prepares off-page recorded membership, an exact term and a packed reading when the actual
objects exist. Unfound optional samples are `not_run` within that discovery bound, never claims
of absence in the whole book. The member request uses a different page from an actual group;
complete recorded membership must retain at least one explicitly off-page member.

Live execution compares canonical native/CLI/actual-MCP responses, retaining each bounded request
and response. Coverage follows continuations until the exact retained `coverage_total` is reached;
it refuses repeated cursors or exhaustion of the explicit finite page bound. Other responses
remain bounded samples. `consumer-cases.json` is the exact request/digest input to detached replay.
A stopped or failed process leaves its raw prefix; it establishes no complete consumer passage.

## Exact export and detached replay

The root owns these installed export/verify commands. The prepared selection requests the entire
final view closure and all316 sources under an explicit8GiB budget; increase that finite budget
only if the owning export reports it insufficient. No weaker export replaces a refused closure.

```sh
uv run ci review export docs/design_review/evidence/2026-11-11_bep-whole-book/consumers/attempt001/review-selection.json docs/design_review/evidence/2026-11-11_bep-whole-book/review-bundle --exact-closure --json
uv run ci review verify docs/design_review/evidence/2026-11-11_bep-whole-book/review-bundle --manifest-sha256 MANIFEST_SHA256_FROM_EXPORT --json
uv run python docs/design_review/evidence/2026-11-11_bep-whole-book/verify_consumers.py replay --binding docs/design_review/evidence/2026-11-11_bep-whole-book/binding.json --output docs/design_review/evidence/2026-11-11_bep-whole-book/consumers/attempt001 --bundle docs/design_review/evidence/2026-11-11_bep-whole-book/review-bundle --manifest-sha256 MANIFEST_SHA256_FROM_EXPORT
```

Retain the export's manifest digest separately, then substitute it in both latter commands. Replay
uses the production offline verifier before comparing the saved live request responses. Each
replay has a distinct dated output directory. It uses no database or model execution. The
production inspection interface reauthenticates the full package for each request; this can be
substantial for a whole-book bundle. Optional repeated `--request-name` selectors such as
`summary` or `coverage` narrow replay explicitly; they establish only the chosen saved requests.

Successful exact transport/closure verification preserves the native source and companions; it
does not turn inherited display/inline/cell recognition limits, unavailable analytical families
or private interpretations into complete recognition, accuracy or accepted knowledge. The root
retains managed receipts/raw outputs and finalizes accepted evidence through the existing owner.


## Interrupted pre-book test campaign

**Observed2026-11-11; book/consumer execution remains not_run.** The operator cancelled
testing following Cursor/Codex's memory-pressure crash. `raw/test-campaign-oomd.log` records
systemd-oomd killing Cursor's application cgroup at23:47:43 local, with167.1G group usage.
That cgroup can include tests and other Cursor/Codex work; no per-process attribution was
retained. PostgreSQL runs in its separate service cgroup. The held default campaign is
0a78c71ce1a949e38e906c9c5392c1f3; recovery currently refuses unproven settlement. No test
workers were observed after the crash, and nothing was restarted. BEP-E04/E05 in the coordinator
own remaining preflight, test-memory and custody work. This is not evidence of book execution.

# Retained diagnostics, querying and incidents

**Status:** Proposed; 2026-11-01. [Coordinator](../structured-logging-observability_2026-11-01.md)
owns LOG-03/04 state and I04. Consumes working LOG-02 delivery and LOG-01 scope/identity contracts.
Serves O04/O07/O09/O12 and E02/E03/E05.

<a id="LOG-03"></a>
## LOG-03 — Retention and real local reads

Produce process/signal/security-compartment-owned segments of safe application JSONL and native
OTLP JSON. Application event archive owns diagnostic occurrence IDs; OTLP logs/ECS carry the same
ID as projections, not additional occurrences. SDK spans/metrics retain resource/scope, parent/link,
metric kind/unit/temporality, histograms/exemplars and dropped-count semantics. Unknown schemas
are explicitly unsupported, not ignored or parsed as current. Foreign telemetry preserves origin.

Use native file exporters and rolling event handlers, not a custom OTLP receiver. Default policy:
16MiB target segments,7day age retention and2GiB combined archive allowance per installation;
these are configurable operational choices, not capacity claims. One retention owner reconciles
the aggregate budget across process partitions; workers do not each assume the entire allowance.
Prune closed eligible segments, never authoritative product/evidence data or live query/export
snapshots. Budget exhaustion reports diagnostic loss and uses bounded fallback, not unbounded
spooling or a domain-state failure. Explicit export failure remains its own failed operation.

Set restrictive archive permissions and trusted compartment mapping before writes. Process files
alone do not isolate principals or reference-authoring sessions. Every reader receives an authorized
scope before file selection. Local trusted expert SQL is optional, with DuckDB external access and
extension loading constrained; MCP exposes only typed queries, not server paths or SQL.

I04 must settle native rotation stream ownership and snapshot protection before production queries:
choose one short selection/prune coordination mechanism and private pinned snapshot with explicit
close. Prefer established filesystem/locking facilities, without a long-lived snapshot service.
Define crash cleanup based on owned resources and liveness. A cursor identifies the selected
snapshot, time cut, filters and schema; expiry is explicit. Do not silently rerun a later query as
though it were the same page. This is a required investigation, not a deferred implementation TODO.

Define typed event/trace requests: scope, time window, stable filters, opaque continuation; defaults
100rows/page with1000maximum. Results include coverage and source cut; a bounded page does not
establish a bounded scan. Select partitions/time first. Use existing DuckDB read_ndjson/read_json
and typed derived views, retaining raw versions. Cache/index only when repeated scans justify a
rebuildable projection; avoid introducing a shared concurrent DuckDB writer. Preserve numeric,
bool/string attribute distinctions and absent/null values. Never use ignore_errors to hide corruption.

Expose minimal real `ci diagnostics events`, `trace` and `follow` consumers in this package. Closed
segments support snapshot reads; follow handles a bounded active tail and incomplete final record.
Earlier valid records remain accessible after interruption. Coverage distinguishes sampled, dropped,
expired, unavailable, denied and corrupt material. Parent/link identity remains a graph where needed;
if I02 selected Eliot, native parsing must honor its different task identity/completion semantics.
An orphan span is not automatically a failed task.

Completion: independently specified records spanning rotation and a partial tail are queried through
installed Typer; JSON is uncontaminated, duplicates are not double counted, denied compartments
stay inaccessible, and a continuation survives allowed retention or returns explicit expiry.

<a id="LOG-04"></a>
## LOG-04 — Native incident capture and occurrence summaries

Optional incident profile captures DEBUG before console filtering. Use one FingersCrossedHandler
per operation, ERROR escalation, reset=False,512sanitized records and16KiB maximum detached record
size. Reserve up to8MiB detached-record payload per operation from a32MiB process capture
allowance (at most four concurrent reserved buffers). If admission is unavailable, continue the
operation without prehistory and emit explicit capture_unavailable coverage; do not create another
unbudgeted buffer or fail domain work. Release reservation with the operation. This bounds capture
payload/count, not total Python heap overhead; assess detached-object overhead during qualification.
Positive buffer_size is mandatory: zero is unbounded. Record truncation and oldest-record
eviction explicitly. Scoped operation completion releases records; do not retain live frames,
traceback objects, scientific objects or source payloads. Normalize origin and UTC timestamps at
capture, not on the eventual consumer thread.

A classified failed operation emits an explicit ERROR trigger even when failure was returned as a
value; expected refusal/warning and cancellation do not automatically escalate. Apply eligibility,
privacy and size rules before the wrapper: it bypasses wrapped-handler level/filter/bubbling.
Released events keep producer timestamps and occurrence IDs. Previously withheld DEBUG records
are appended once to the canonical occurrence archive on escalation; records already archived
retain references and are not appended again. Any incident projection is derived from those IDs.
Thus events/explain/support see the released context through the same service. Success drops untriggered retained
detail. Stdlib MemoryHandler is not an interchangeable error-only ring because it flushes at
capacity and usually on close.

`ci diagnostics incidents` groups canonical retained occurrences by stable code/operation/provider
and declared signature, showing count scope, first/last and representative event IDs. DedupHandler,
GroupHandler and emit_batch may simplify downstream presentation; never deduplicate before
canonical occurrence retention or use unbounded GroupHandler on an indefinite run. Native ticketing
is deferred until acknowledgment/resolution lifecycle is a real requirement; its default source
location identity is not the stable diagnostic code.

Completion: parallel operations cannot trigger each other's buffers; returned failure releases only
its preceding bounded safe history; success/cancellation controls retain their semantics; eviction
and sampled/expired count scope are visible; grouping does not count OTLP projections twice.

## Sources and physical route

[Logbook](../../libraries/logging/logbook.md) §§3,6–9;
[OTel](../../libraries/logging/OpenTelemetry_Python.md) §§3–5,9,12;
[Eliot](../../libraries/logging/Eliot.md) §§4,9–10;
[JSON logger](../../libraries/logging/python-json-logger.md) §§3–8;
[ECS](../../libraries/logging/ecs-logging.md) §§4–8.
Native storage/formatting is delegated; application code supplies only scoped archives, view meaning
and retention/read lifetime gaps. Compare necessary work over many unrelated runs, long histories,
concurrent readers and empty-result queries. No throughput or bounded-memory claim follows solely
from limiting returned rows. Product source/evidence retention remains a separate owner.

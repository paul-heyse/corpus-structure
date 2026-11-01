# Metrics and operational analysis

**Status:** Proposed; 2026-11-01. [Coordinator](../structured-logging-observability_2026-11-01.md)
owns LOG-07 state. Consumes LOG-01 measurement visibility, LOG-02 SDK ownership and LOG-03 reads;
serves O06/O11/O12 and E01/E04. D6 policy/evaluation measurements remain authoritative.

<a id="LOG-07"></a>
## LOG-07 — Measurements with honest scope and useful navigation

Distinguish three products before recording or aggregating:

| Product | Authority and visibility |
|---|---|
| Process/service health | OTel observations visible to the operator; bounded operation/stage/provider/outcome dimensions, no task/run/principal IDs |
| Run-specific summaries | Existing task/method/evaluation measurements and retained occurrences with their coverage; never sampled trace counts as exact task denominators |
| Explicit scoped instrument streams | Optional bounded instrument/provider scope selected before aggregation, exposed only to that authorized scope |

`ci diagnostics metrics --scope process` is operator-only. `summary/compare --run` uses run products;
reject exact run/principal filters on process aggregates. Archive partitioning cannot undo earlier
cross-user aggregation. Future hosted access must preserve this distinction rather than relying on
post-query filtering. Delayed feedback may link an event to original run/response context without
changing evaluation custody or giving extractors independent reference access.

Use OTel Counters for counts, Histograms for durations, Gauges/observable instruments for current
owned state. Define units, monotonicity and reset/collection semantics. Views select bounded
attributes and suitable explicit/exponential histogram aggregation before data accumulation;
DropAggregation can suppress unwanted streams. Preserve attribute types and aggregation structure
in local DuckDB views. Do not sum cumulative snapshots or mix incompatible histogram boundaries.

Exemplars connect distributions to available traces; missing or unsampled targets are explicit.
Metrics remain available independently of trace sampling. Choose collection policy for short
commands: final collect/flush is required even if a periodic reader never ticks. Use supported
reader add/remove lifecycle where it avoids replacing process providers, qualified at selected pin.
Configure queues/readers/destinations jointly with LOG-02; avoid competing periodic writers.

Inspect instrumentor/SDK health through `config/check/metrics`: active package versions, dropped
records, export failure and queue pressure when native SDK metrics provide them. Experimental
names get a versioned projection; absence is not zero. Maintain an independent minimal loss/error
path so SDK failure is not recursively exported through itself. Alert assessment returns typed
observations and known thresholds for automation; it does not create a scheduler or notification
service. Threshold choice is explicit config and named in the result.

### Instrumentation enhancements and limits

If I01 selects local Logfire, compare MetricsOptions(collect_in_spans=True) for operation summaries
with native metric queries before adding bespoke aggregation. It is experimental and process-local,
not a distributed total. Instrument selected clients to expose provider/model identity, streaming
lifetime, usage and retries when actually observed. Token/cost estimates are labelled with their
source/model; no text-length inference masquerades as provider usage. Source revision/CodeSource
metadata aids investigation but does not establish reproduction. Continuous CPU/allocation profiling
requires a separate artifact/tool; spans do not provide profiles by themselves.

### Acceptance and evolution

Use independent expected counter/delta/cumulative/reset and histogram examples, mixed-type
attributes and two concurrent runs. Verify no principal can read combined process metrics and no
run filter manufactures an exact result from an aggregate lacking run identity. A short installed
command produces its final metric record; exemplars and missing traces are reported honestly.
Actual exporter tests qualify delivery separately from in-memory arithmetic/control assertions.

A new stage/provider supplies its declared measurements and selected bounded dimensions; it does
not add a new storage table or periodic worker automatically. Quantitative overhead or capacity
benefits remain unmeasured until a named end-to-end workload requires measurement.

Sources: [OTel](../../libraries/logging/OpenTelemetry_Python.md) §§4,8,11–12;
[Logfire](../../libraries/logging/pydantic-logfire.md) §§4.3,8,14–16;
[D6](../../design/D6-orchestration-metrics-policies.md) metrics/policy owners.

## Investigative input — 2026-11-01

The direct OTel three-signal probe retained a final counter before the periodic interval; final
collection is a demonstrated native route. Minimal archive projection preserved metric union,
temporality/histogram/exemplar fields, but did not establish complete typed query semantics.
Keep the independent reset/type/scope acceptance cases above. Logfire collect_in_spans is not
selected as a core dependency; any optional process-local summary must honor the explicit
provider boundary established by I01. See I03/I04/I05 receipts in the coordinator.

# Logging telemetry runtime qualification

**2026-11-01; I01/I03/I05; partial investigation, focused mechanisms Tested.**
Inspected source baseline `28f735b8`, with concurrent PDF and sibling logging investigation work
preserved. This folder owns only isolated telemetry probes, pinned-source receipts and results.
No product manifest, product environment, plan, STATUS or architectural authority was edited.
Root owns evidence finalization and coordinator dispositions.

## Questions and conclusions

**I03: passed for the specified isolated family and real three-signal file path.** Python3.14.10
resolved and installed API/SDK/OTLP-proto-http1.45.1, instrumentation-logging/sqlalchemy0.66b1,
OTLP-JSON-file0.66b1, Logfire/logfire-sdk5.4.0, Pydantic2.14.1, SQLAlchemy2.1.5 and HTTPX0.28.1.
The exact spec and transitive lock are in `raw/pyproject.toml` and `raw/uv.lock`. This is not a
product-lock resolution or qualification of every optional instrumentor.

The first attempted file-exporter pin1.45.1 failed: that distribution is released as0.66b1, even
though its SDK family is1.45.1. `raw/install.txt` retains that failed resolution; the corrected
installation is `raw/install-corrected.txt`. HTTPX was then added for the query-client import
(`raw/install-httpx.txt`); the initial missing-import failure is preserved.

Exact native imports (API signatures are recorded in `raw/attempt2/api.stdout`):

- `opentelemetry.exporter.otlp.json.file.FileSpanExporter`
- `opentelemetry.exporter.otlp.json.file.FileMetricExporter`
- `opentelemetry.exporter.otlp.json.file._log_exporter.FileLogExporter`
- `opentelemetry.instrumentation.logging.handler.LoggingHandler`

**The log exporter is a private-module API** at this pin; it is not exported at the package root
and there is no public `log_exporter` module. Keep that qualification boundary explicit in the
selected integration. File exporters accept an explicit path or borrowed stream; their default
stdout is unsuitable for CLI JSON/MCP. The direct probe emitted/read three spans, two correlated
stdlib records retaining extras and a final counter value2. A borrowed StringIO stayed open after
exporter shutdown. Files are newline-delimited OTLP JSON, not one application event per line.

**I01: recommend direct OTel as the core process/provider/native-instrumentation owner.**
Local Logfire remains an eligible explicit-instrumentation tool, but is not a drop-in replacement
for all selected native consumers. `configure(local=True, send_to_logfire=False, console=False)`
leaves the host global provider unchanged: repeated local scopes emit to the local processor,
while native OTel consumers emit to the host processor. Closing the local instance left the host
usable. Thus native FastMCP instrumentation does not automatically use that local Logfire provider.

More importantly, Logfire5.4 Pydantic instrumentation always uses the global Logfire instance:
installed `_internal/main.py` contains an explicit TODO at `instrument_pydantic` to use `self`.
`integrations/pydantic.py` binds `DEFAULT_LOGFIRE_INSTANCE` and checks `GLOBAL_CONFIG._initialized`.
The initial local-plugin probe failed its expectation of a validation span, preserved in
`raw/pydantic.stderr`. Source-guided fresh-process controls confirm: local-only configuration emits
no validation span, whereas global Logfire configuration captures the subsequently defined model
failure and does not capture the pre-instrumentation model. This makes import timing and global
ownership an actual composition constraint, not merely a hypothetical concern. A future choice of
global Logfire is possible, but must explicitly own process instrumentation and address embedded
hosts; it cannot be hidden behind `local=True`.

Package metadata also corrects a guide premise: released Logfire5.4 already depends on the
separate `logfire-sdk==5.4.0` distribution, not only the6beta series. Do not select packaging by
the overview's generalization. Metadata is retained in `raw/package-metadata.json`.

**I05: partial; hard deadline claim is disproved for naive SDK force-flush.** A finite synthetic
exporter sleeping0.25s made `TracerProvider.force_flush(timeout_millis=10)` take approximately0.25s
and returnTrue. The probe passing establishes that this timeout does **not** preempt exporter work;
it does not qualify a bounded cleanup implementation. Pinned shared BatchProcessor force_flush
calls synchronous export and ignores the provided deadline. File exporters likewise perform
ordinary stream write/flush with no cancellation deadline. Metric final force_flush collected a
short command's counter without waiting for a periodic interval.

A real OTLP/HTTP exporter against a controlled loopback server which stalled its response returned
FAILURE in approximately0.11s with an explicit0.1s transport timeout. The expected failure log is
retained in `http_timeout.stderr`; this is actual loopback transport behavior, not successful
delivery. It establishes that transport timeout matters independently of batch timeout; it does
not establish a total multi-signal5s cleanup guarantee or blocked-filesystem bound.

Planning consequence: propagate a shared remaining deadline into supported transport operations;
do not call an SDK force-flush under the assumption that its timeout enforces the budget. A hard
deadline across arbitrary/custom/file exporters needs a qualified execution/isolation strategy or
an explicit supported-destination limitation. This remains an integration obligation; no exporter
supervision framework was implemented here.

## Runs, retained failures and reproduction

- **failed:** first exact installation, nonexistent file-exporter1.45.1 (`raw/install.txt`).
- **passed:** corrected exact isolated family installation (`raw/install-corrected.txt`).
- **failed:** initial API query import without HTTPX and local-Pydantic capture expectation.
  Original `raw/outcomes.json`, stdout/stderr and signal files remain unchanged.
- **passed:** seven fresh-process source-guided controls after HTTPX addition:
  `python3 docs/design_review/evidence/2026-11-01_logging-telemetry-runtime/run_probes.py attempt2`.
  Exact results and raw signal output are under `raw/attempt2/`.
- **not_run:** product integration, application Typer/MCP journeys, actual remote telemetry/query,
  arbitrary instrumentor compatibility, performance/capacity or hard-deadline application acceptance.

The runner uses isolated Python at
`/home/paul/.cache/corpus-logging-investigations/telemetry/.venv/bin/python`, removes inherited
OTEL/LOGFIRE/CORPUS variables plus ambient project-environment selectors, and runs each global
case in a fresh interpreter. The only network telemetry probe uses loopback. Each subprocess has
a15s watchdog; a watchdog expiry is a failed probe, not a passing bounded-shutdown assertion.
No watchdog expiry occurred. To repeat, supply a new output label instead of `attempt2`; output
directories refuse overwrite. Initial evidence is never relabelled by the later corrected tests.
Pinned environment creation used `uv init --bare --python 3.14.10` and exact `uv add` into the
cache project, with UV_PROJECT_ENVIRONMENT/VIRTUAL_ENV removed and UV_LOCKED=0 only there.

## Source provenance and residual boundaries

Context7 was the first documentation route for OpenTelemetry Python, contrib logging and Logfire.
Indexed sources lagged or used main; consequential decisions above were checked against installed
exact packages. `raw/pinned-sources/` retains the source files, and `raw/source-manifest.json`
names each installed path and SHA256. `raw/attempt2/api.stdout` output is signature evidence, not remote delivery.

I06 cheap source qualification: LogfireQueryClient imports only after HTTPX is installed; it accepts
read_token/base_url/timeout/client kwargs, with mandatory min_timestamp on JSON/Arrow/CSV queries.
No credentials were searched and no remote query was sent. Root separately owns I06 query tests.
Its credential/read/write/actual endpoint obligations are not settled by this folder.

No private SDK globals were reset. Tests separate injected host providers from owned local SDKs.
Native global provider installation is tested only in fresh processes. Further Pydantic successful
validation content controls, native FastMCP ownership and complete application startup/import order
remain implementation acceptance work. Existing Pydantic inputs here are synthetic nonsensitive
strings, not corpus documents or evaluator reference data.

## Combined candidate and disposable CLI check

Root subsequently co-resolved structlog26.1.0, Logbook1.10.1, Typer0.27.3 and Rich15.0.0 in the
same isolated telemetry lock; raw/combined-install.txt retains resolution output, and raw spec/lock
are the final combined inputs. cli_composition.py passed a fresh disposable Typer app with Rich
warning on stderr, result-only JSON stdout and an actual native file span. This is not installed
production ci or a full three-branch occurrence bridge. Its command uses the isolated interpreter;
raw/cli-composition.txt retains the result.

## Records

<!-- evidence-index:start -->
Generated by `just evidence index` from `records/`; do not edit by hand. 2 current, 0 superseded.


**logging-investigations**

| Record | Package | Outcome | Informs | Finalized |
|---|---|---|---|---|
| [Qualify isolated Python dependency family and native telemetry file APIs](records/logging.i03.json) | LOG-00 | passed | I03, LOG-00 | 2026-11-01 |
| [Qualify provider ownership and shutdown deadline feasibility](records/logging.i05.json) | LOG-02 | partial | I05, LOG-02 | 2026-11-01 |
<!-- evidence-index:end -->

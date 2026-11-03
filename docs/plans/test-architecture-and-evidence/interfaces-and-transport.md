# Actual interfaces and transport

**Status:** Implemented; operator-selected verification accepted2026-11-02. The
[coordinator](../test-architecture-and-evidence_2026-11-02.md) owns TA-10/11 and DTA-016 disposition.

## Foundation and target

Keep current in-memory FastMCP journeys, actual pooled lifespan controls, CLI query/continuation/
explanation/export and real ordered-event SQL serializer coverage. These are meaningful assurance.
Add observations at the two boundaries they do not establish: a useful post-initialize subprocess
tool interaction, and the production serializer's emitted chunk bound. No provider/model call is
needed for these infrastructure boundaries.

## TA-10 — Complete current semantic MCP over stdio

Use the installed pinned FastMCP4.1.3 `Client(StdioTransport(command,args,env,cwd,keep_alive=False))`
route rather than extending the test's handwritten initialize-only JSON-RPC exchange. Select the
actual installed CLI/MCP command and bounded current composed native fixture. Pass explicit owned
clone, run, released inputs and purpose credentials from TA-03; do not inherit the real project
or silently use the transport's default environment/working directory. Keep secrets out of logs.

Exercise initialize/list_tools, a deterministic lease/read/propose or equivalent supported semantic
tool journey, and a meaningful refusal after initialization with independent expected native result.
Observe the same pinned realization and actual restricted session. A successful transport handshake
alone cannot satisfy the semantic journey. Keep in-memory tests for their faster scoped contracts;
a single wire journey need not duplicate every tool case.

Default keep_alive=True retains the subprocess across connection contexts. Explicit False scopes
the normal lifetime, while existing supervision still owns bounded timeout/cancellation/drain and
all owned descendants. Fault-inject an early client exit and a tool failure; ensure transport closure
and native connections settle before database disposal. Preserve both primary and cleanup errors.
Do not infer hard-kill recovery solely from an async context manager or mocked child.

Acceptance: actual subprocess PID/start context, explicit target/purpose, one exact tool result and
refusal, normal/early/failure child settlement, and no fallback to a same-process Client(server).
Use existing result receipts; this establishes wire/native scope, not live-provider grading or the
complete UM product union. Missing server/role prerequisites are reported rather than mocked passes.

## TA-11 — Observe chunk and stream behavior on the production formatter

`tests/semantic/test_pdf_record_reader.NativeRows` substitutes its own iter_native_json. Retain it
only for a distinct independent reference role, not production chunk sizing. Extend the existing
real ordered-event SQL path (`test_native_export_uses_one_ordered_sql_cursor`) so the actual
PublishedPdfReader.iter_native_json emits measured chunks for the large Unicode/extension case.

Assert the existing production chunk contract from its owning code/consumer: bound each emitted
chunk without first joining the whole output, then independently verify exact reconstructed JSON,
negative zero and native logical digest. Preserve missing-membership/corrupt-pin refusals, one
ordered cursor and exact row ordering/multiplicity. Use tiny boundary and large Unicode cases to
expose encoding-size errors; do not invent a stricter bound than production promises. If the
contract is byte-based, count bytes rather than characters. A type-preserving roundtrip alone
cannot establish chunk bounds or independent content correctness.

Exercise early stop/cancellation/consumer error and prove the underlying real result closes.
Detached materialized outputs and borrowed readers have separate lifetimes. Reuse existing Arrow/
ADBC snapshot/driver controls where they already establish the promised property; do not introduce
another serializer, JSON decoder or connection owner merely to make the test easy.

Acceptance includes production implementation identity, independently authored expected content,
per-chunk bound, exact large/small output and failure/early-close resource settlement. A bounded
structural control is not an end-to-end memory or throughput measurement. If a real serializer
bug is exposed, implement only its bounded correction with affected publication/read/export
consumers, coordinating frozen native artifacts through the existing forward route.

## Library contracts and review boundaries

- [FastMCP transports](https://github.com/prefecthq/fastmcp/blob/main/docs/clients/transports.mdx)
- [Repository FastMCP orientation](../../libraries/python_introspection/fastmcp.md)
- [Arrow capabilities](../../libraries/analytical_infrastructure/pyarrow.md)
- [ADBC PostgreSQL capabilities](../../libraries/postgresql/adbc-driver-postgresql.md)

Context7 and installed fastmcp/client/transports/stdio.py:25–95,218 confirm the selected subprocess
API/lifetime surface; that is Interface-checked, not an actual stdio run. Preserve current server
lifespan and native context contracts. The native companion owns acquisition/recovery; this one
owns client/consumer lifetime. TA-12 judges their assembled interaction independently.

## Implementation boundary — 2026-11-02

`test_current_cli_stdio_journey_and_settlement` runs the installed CLI with SDK `StdioTransport`
against explicit owned native coordinates. Four modes cover exact accepted proposal/observation
release, early exit, a post-initialize wrong-task refusal, and cancellation. It observes the actual
child PID, restricted PostgreSQL session and their settlement before clone disposal. Existing
same-process controls remain independently useful.

`test_native_export_uses_one_ordered_sql_cursor` now consumes the production formatter directly.
Its large Unicode scalar exceeds the promised chunk bound; every emitted byte chunk is checked
before aggregation. Exact reconstructed content/negative zero and one ordered SQL cursor remain
asserted. Real SQLAlchemy result closure is observed after normal completion, generator close,
consumer error and borrower cancellation. The substituted scalar replay is explicitly a reference
control. This is bounded formatter/resource evidence, not a memory or throughput measurement.

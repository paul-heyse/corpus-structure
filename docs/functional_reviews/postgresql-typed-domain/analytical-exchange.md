# Analytical access and faithful exchange

**2026-11-09 · Proposed recommendations.** Source inspected at `d18183a22`, unchanged through
`f917260f8`. [Transfer discovery](../../library_leverage/libraries/postgresql/discovery/typed-copy-and-arrow-transfer.md)
separates existing adoption from additional consumer capabilities. Evidence is static, not native qualification.

<a id="O08"></a>
## O08 — Directional exchange preserving declared meaning

External structured imports and scientific/annotation exports could support richer values without
per-consumer coercion. ArrowWriteProfile already checks ordered wire/schema metadata and creates
fresh encoders; publication borrows the Core transaction, and companion export authenticates pins
and publishes completed Parquet artifacts.

Prefer extending existing directional profiles for the first selected new value family: source
value → logical Arrow → wire type → admitted value → export. Separate exact lexical/source fields
from permitted analytical normalization. Analytics already retains decimal lexical values/rounding
and exact hex-float policy; replace only a demonstrated remaining conversion.

Nested import can use pgpq lists/structs where array/composite shape is faithful. Declare child
nullability, dimensions/lower bounds, qualified OIDs and object lifecycle. Generated DDL and physical
positional compatibility do not establish semantic identity. Existing model/migration owners govern
native objects. [pgpq capabilities](../../libraries/postgresql/pgpq.md). NumPy/network/temporal or
spatial values similarly require selected declared meaning rather than a generic adapter sweep.

Compare typed Psycopg COPY TO/set_types for row consumers, ADBC for Arrow reads and retained native
JSON text where exact serialization is required. One universal Arrow/PostgreSQL schema conflates
directions. arrow-json is a conditional nested bridge only with explicit SQL-null/JSON-null/precision
handling. For Rust consumers, compare pgpq traits/caller-owned buffers as a separate integration,
not an assumed arbitrary Python encoder-plugin seam.

Deliver one selected external structured dataset through protected publication and an independently
consumed faithful export. Include SQL/JSON null, null/empty nested values, precision and temporal
normalization. Keep original bytes where lexical evidence matters. Migrate and retire replaced
consumer coercions while preserving independent fixtures. Failed encoding/constraints abort the
stream/transaction; partial files remain unpublished, encoders per-stream and OIDs generation-bound.
Native composites/extra normalization activate only for the selected exchange contract.

<a id="O09"></a>
## O09 — Owned research streams and replayable packages

A notebook, Polars/Arrow tool or external engine could query bounded published data and reproduce
analysis offline. Existing capture already provides resident/spooled packets and ends database
snapshots before high-level analysis. Extend that custody rather than add another instance authority.

Prefer a bounded model-bound research query entry point exposing result schema, source/release pins
and an owned stream or detached package. ADBC fetch_arrow and Arrow C Array/C Stream capsules can
avoid mandatory PyArrow table materialization for compatible consumers; ownership transfers once
and readers close before connection/cursor reuse. This does not eliminate PostgreSQL decoding.
[ADBC25 Python APIs](https://arrow.apache.org/adbc/25/python/api/adbc_driver_manager.html).

Small parameterized reads can combine positional $n, adbc_prepare inputs and adbc_execute_schema
outputs after an explicit admitted query profile. Bound PqResultArrayReader may buffer a complete
result per binding and execute later bindings during consumption. Keep effectful queries outside
this read interface and large captures on the current COPY-compatible route.
[Statement](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/statement.cc),
[result reader](https://github.com/apache/arrow-adbc/blob/apache-arrow-adbc-25/c/driver/postgresql/result_reader.cc).

An independent external-input operation could use destination-aware adbc_ingest(mode=append) into
model-created staging, including integer→NUMERIC/annotated JSON→JSONB. It cannot borrow Core's session.
Select only where one ADBC-owned transaction can perform the complete admitted operation; otherwise
retain pgpq/Psycopg. create_append is not migration. This is a conditional new input operation, not
an alternate path around protected publication.

For live exploratory federation compare DuckDB read_adbc/ATTACH TYPE adbc with explicit remote SQL:
attached-table filter pushdown, autocommit, concurrency and metadata caching must be qualified
independently. [Extension contract](https://duckdb.org/community_extensions/extensions/adbc).
Prefer manifest-bound Parquet/IPC for reproducible offline work. A PostgreSQL replay consumer could
instead use Copy(writer=FileWriter), with schema/type/version manifest and atomic file publication;
binary COPY alone is not a self-describing portable dataset. Query execution via SQLFrame/PythonExecutor
remains a conditional laboratory alternative, not an independent production semantic authority.

Deliver a capsule consumer, admitted bounded bound query and offline replay after disconnection.
Retain completeness, schema, logical/file digests and cancellation; remove replaced hydration/export
glue. D3/D8 must distinguish live exploration from reproducible capture. Activate routes for the
selected research/import consumer; extension compatibility and directional type mappings remain
explicit feasibility questions for that choice. No performance improvement is quantified.

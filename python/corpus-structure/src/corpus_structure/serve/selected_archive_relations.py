"""Typed Parquet support relations over invocation-owned archive bytes."""

from datetime import datetime
from itertools import groupby

import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
from duckdb import ColumnExpression as column

from corpus_structure.semantic.acquired_selected_relations import SelectedRelationLookup
from corpus_structure.semantic.data_operation_json import json_bytes, native_json_loads

ARCHIVE_KEY = "_archive_key"


def with_archive_key(schema):
    return schema.insert(0, pa.field(ARCHIVE_KEY, pa.string(), nullable=False))


def encode_support(record, encodings):
    values = {}
    for name, encoding in encodings.items():
        value = record[name]
        if value is not None:
            if encoding == "json":
                value = json_bytes(value).decode()
            elif encoding == "timestamp":
                value = datetime.fromisoformat(value)
            elif encoding == "binary":
                if not isinstance(value, str) or not value.startswith("\\x"):
                    raise ValueError("selected archive byte column differs from its native shape")
                value = bytes.fromhex(value[2:])
            elif encoding != "native":
                raise ValueError("selected archive has an unsupported column encoding")
        values[name] = value
    return values


def _arrow_value_bytes(value):
    if isinstance(value, str):
        return 4 + len(value.encode())
    if isinstance(value, bytes):
        return 4 + len(value)
    if isinstance(value, (list, tuple)):
        return 4 + sum(_arrow_value_bytes(item) for item in value)
    return 8


def write_support_fragments(root, records, codec, *, batch_bytes):
    """Write ordered relation runs with one open writer and bounded pending data."""
    previous = None
    for relation, group in groupby(records, key=lambda row: row["relation"]):
        schema, encodings = codec(relation)
        path = root / f"{relation.replace('.', '_')}.parquet"
        if path.exists():
            raise ValueError("selected archive repeats a relation run")
        count = size = 0
        pending = []
        # Retain the child field names and nullability of the declared Arrow schema.
        with pq.ParquetWriter(path, schema, use_compliant_nested_type=False) as writer:
            for packet in group:
                key = packet["key"]
                if not key.startswith(relation + ":") or (previous is not None and key <= previous):
                    raise ValueError("selected archive keys are repeated or out of order")
                previous = key
                row = {ARCHIVE_KEY: key, **encode_support(packet["record"], encodings)}
                row_bytes = sum(_arrow_value_bytes(value) for value in row.values())
                if pending and (size + row_bytes > batch_bytes or len(pending) >= 64):
                    writer.write_batch(pa.RecordBatch.from_pylist(pending, schema=schema))
                    pending.clear()
                    size = 0
                pending.append(row)
                size += row_bytes
                count += 1
            if pending:
                writer.write_batch(pa.RecordBatch.from_pylist(pending, schema=schema))
        yield relation, path, count


class ArchivedSelectedRelations(SelectedRelationLookup):
    """The detached reader shares the live lookup contract over authenticated files."""

    def __init__(self, fragments, reader, *, populations=None, max_bytes=None, max_records=None):
        self.reader = reader
        self.population_archive = populations
        self.cut = None
        self.has_frontier = False
        self.retained_bytes = 0
        self.retained_records = 0
        self.max_bytes = max_bytes
        self.max_records = max_records
        self._support_validated = False
        self._relations = {}
        self._frontier = None
        for relation, (path, count, schema, encodings) in fragments.items():
            with pq.ParquetFile(path) as parquet:
                if parquet.metadata.num_rows != count or not parquet.schema_arrow.equals(
                    schema, check_metadata=True
                ):
                    raise ValueError("selected support fragment differs from its sealed shape")
            self._relations[relation] = (
                ds.dataset(path, schema=schema, format="parquet"),
                encodings,
            )

    def charge(self, size):
        self.retained_bytes += size
        self.retained_records += 1
        if (self.max_bytes is not None and self.retained_bytes > self.max_bytes) or (
            self.max_records is not None and self.retained_records > self.max_records
        ):
            raise ValueError("detached structural closure exceeds its examined bound")

    def attach_frontier(self, path, cut):
        self.cut = cut
        self.has_frontier = True
        self._frontier = ds.dataset(path, format="parquet")

    def _scan(self, relation, *, fields=None, validate=False):
        if relation not in self._relations:
            return
        dataset, encodings = self._relations[relation]
        predicate = None
        for name, value in (fields or {}).items():
            if name not in encodings:
                raise ValueError("selected support lookup requires a declared column")
            field = ds.field(name)
            if value is None:
                match = field.is_null()
            else:
                match = field == encode_support({name: value}, {name: encodings[name]})[name]
            predicate = match if predicate is None else predicate & match
        for batch in dataset.scanner(
            filter=predicate,
            batch_size=64,
            batch_readahead=0,
            fragment_readahead=0,
            use_threads=False,
        ).to_batches():
            for row in batch.to_pylist():
                key = row.pop(ARCHIVE_KEY)
                for name, encoding in encodings.items():
                    value = row[name]
                    if value is not None:
                        if encoding == "json":
                            row[name] = native_json_loads(value)
                        elif encoding == "timestamp":
                            row[name] = value.isoformat()
                        elif encoding == "binary":
                            row[name] = "\\x" + value.hex()
                packet = {"key": key, "relation": relation, "record": row}
                if validate:
                    self.charge(len(json_bytes(packet)))
                yield self.reader.record(packet, validate=validate)

    def validate_support(self):
        if self._support_validated:
            return
        for relation in sorted(self._relations):
            previous = None
            for packet in self._scan(relation, validate=True):
                key = packet["key"]
                if not key.startswith(relation + ":") or (previous is not None and key <= previous):
                    raise ValueError("selected archive keys are repeated or out of order")
                previous = key
        self._support_validated = True

    def rows(self, relation):
        yield from self.rows_for(relation)

    def rows_for(self, relation, **fields):
        for packet in self._scan(relation, fields=fields):
            yield packet["record"]

    def records(self):
        for relation in sorted(self._relations):
            yield from self._scan(relation)

    def _frontier_scan(self, kind, identity=None):
        if self._frontier is None:
            return
        predicate = ds.field("kind") == kind
        if identity is not None:
            predicate &= ds.field("identity") == identity
        for batch in self._frontier.scanner(
            columns=["payload"],
            filter=predicate,
            batch_size=64,
            batch_readahead=0,
            fragment_readahead=0,
            use_threads=False,
        ).to_batches():
            for payload in batch.column(0).to_pylist():
                yield self.reader.frontier(kind, native_json_loads(payload))

    def frontier_rows(self, kind):
        yield from self._frontier_scan(kind)

    def frontier_row(self, kind, identity):
        return next(self._frontier_scan(kind, identity), None)


class ChargedArchivePopulations:
    """Meter canonical population records consumed by cold identity verification."""

    def __init__(self, archive, charge):
        self.archive = archive
        self.header_count = archive.header_count
        self.charge = charge

    def rows(self, relation, **fields):
        for row in self.archive.rows(relation, **fields):
            self.charge(len(json_bytes(row)))
            yield row

    def item(self, product_id, collection, partition_key, item_key):
        # The partition's rows are charged by the commitment scan. References
        # still resolve exact item addresses in the same authenticated archive.
        return self.archive.item(product_id, collection, partition_key, item_key)


FRONTIER_SCHEMA = pa.schema(
    [
        pa.field("kind", pa.string(), nullable=False),
        pa.field("identity", pa.string(), nullable=False),
        pa.field("payload", pa.binary(), nullable=False),
    ]
)


def append_frontier_page(writer, page):
    for kind, identity in (
        ("obligations", "obligation_id"),
        ("uses", "use_id"),
        ("original_source_admissions", "admission_id"),
    ):
        rows = [
            {
                "kind": kind,
                "identity": row[identity],
                "payload": json_bytes(
                    {key: value for key, value in row.items() if key != "products"}
                ),
            }
            for row in page.get(kind, ())
        ]
        if rows:
            writer.write_batch(pa.RecordBatch.from_pylist(rows, schema=FRONTIER_SCHEMA))


def seal_frontier(path, destination, *, charge):
    """Sort captured identities once and refuse conflicting repeated observations."""
    from corpus_structure.analytics import connection

    with connection() as engine:
        rows = engine.from_parquet(str(path)).distinct()
        keys = rows.select(column("kind"), column("identity"))
        if keys.except_all(keys.distinct()).limit(1).fetchall():
            raise ValueError("selected frontier repeats an identity with different facts")
        sorted_rows = rows.sort(column("kind"), column("identity"))
        with (
            sorted_rows.to_arrow_reader(batch_size=64) as reader,
            pq.ParquetWriter(destination, FRONTIER_SCHEMA) as writer,
        ):
            for batch in reader:
                for payload in batch.column(2):
                    charge(len(payload.as_py()))
                writer.write_batch(batch.cast(FRONTIER_SCHEMA))

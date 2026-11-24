"""Typed selected population fragments shared by native export and detached replay."""

from collections.abc import Mapping
from contextlib import contextmanager
from hashlib import sha256

from .data_operation_json import native_json_loads
from .data_operation_values import decode_semantic_value, semantic_value
from .identity import canonical_bytes

POPULATION_HEADERS = "kb.data_product_population"
POPULATION_ITEMS = "kb.data_product_population_item"
KEY_FIELDS = ("product_id", "collection", "partition_key")
HEADER_FIELDS = (
    *KEY_FIELDS,
    "ordinal",
    "partition_digest",
    "item_count",
    "group_digests",
    "placement",
)
ITEM_FIELDS = (*KEY_FIELDS, "ordinal", "address_key", "canonical_text")


def population_fields():
    """Shared output names of the native branch projection."""
    return (*HEADER_FIELDS, *ITEM_FIELDS[len(KEY_FIELDS) + 1 :])


def _schema(relation, cut_id):
    import pyarrow as pa

    names = HEADER_FIELDS if relation == POPULATION_HEADERS else ITEM_FIELDS
    return pa.schema(
        [
            pa.field(name, pa.int64() if name in {"ordinal", "item_count"} else pa.string(), False)
            for name in names
        ],
        metadata={b"cs.cut": cut_id.encode(), b"cs.relation": relation.encode()},
    )


def write_population_fragments(connection, handle, root, cut_id):
    """Stream selected native rows into two independently typed, sealed fragments."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    from .demand_results import stream_selected_archive_population

    for relation in (POPULATION_HEADERS, POPULATION_ITEMS):
        schema = _schema(relation, cut_id)
        name = relation.replace(".", "_") + ".parquet"
        count = 0
        with pq.ParquetWriter(root / name, schema) as writer:
            for rows in stream_selected_archive_population(
                connection, handle, items=relation == POPULATION_ITEMS
            ):
                writer.write_batch(
                    pa.RecordBatch.from_pylist(
                        [{name: row[name] for name in schema.names} for row in rows], schema=schema
                    )
                )
                count += len(rows)
        yield relation, name, count


@contextmanager
def open_population_fragments(root, manifest):
    present = {POPULATION_HEADERS, POPULATION_ITEMS} & manifest.relations.keys()
    if not present:
        yield None
        return
    if present != {POPULATION_HEADERS, POPULATION_ITEMS}:
        raise ValueError("selected population archive requires both sealed relations")

    import pyarrow.parquet as pq

    from corpus_structure.analytics import connection

    with connection() as engine:
        relations = {}
        for relation in present:
            record = manifest.relations[relation]
            path = root / record.file
            with pq.ParquetFile(path) as parquet:
                if parquet.metadata.num_rows != record.rows or not parquet.schema_arrow.equals(
                    _schema(relation, manifest.cut_id), check_metadata=True
                ):
                    raise ValueError("selected population fragment differs from its sealed shape")
            relations[relation] = engine.from_parquet(str(path))
        archive = PopulationArchive(relations, manifest.relations[POPULATION_HEADERS].rows)
        archive.verify_relations()
        try:
            yield archive
        finally:
            archive.close()


def _where(relation, fields):
    from duckdb import ColumnExpression, ConstantExpression

    for name, value in fields.items():
        if name not in relation.columns:
            raise ValueError("selected population lookup requires a declared column")
        relation = relation.filter(ColumnExpression(name) == ConstantExpression(value))
    return relation


class PopulationArchive:
    """Invocation-owned relational replay over the authenticated physical files."""

    def __init__(self, relations, header_count):
        self.relations = relations
        self.header_count = header_count
        self._closed = False

    def _require_open(self):
        if self._closed:
            raise ValueError("selected archive populations are closed")

    def close(self):
        self._closed = True
        self.relations.clear()

    def verify_relations(self):
        from functools import reduce
        from operator import and_

        from duckdb import ColumnExpression as col
        from duckdb import ConstantExpression as value
        from duckdb import FunctionExpression as fn

        headers = self.relations[POPULATION_HEADERS]
        items = self.relations[POPULATION_ITEMS]
        keys = tuple(col(field) for field in KEY_FIELDS)
        for relation, columns in (
            (headers, keys),
            (items, (*keys, col("ordinal"))),
            (items, (*keys, col("address_key"))),
        ):
            projected = relation.select(*columns)
            if projected.except_all(projected.distinct()).limit(1).fetchall():
                raise ValueError("selected population archive repeats an exact key")
        condition = reduce(
            and_, (col("member", field) == col("header", field) for field in KEY_FIELDS)
        )
        if (
            items.set_alias("member")
            .join(headers.set_alias("header"), condition, how="anti")
            .limit(1)
            .fetchall()
        ):
            raise ValueError("selected archive item has no authenticated population header")
        actual = items.aggregate(
            [
                *keys,
                fn("count_star").alias("count"),
                fn("min", col("ordinal")).alias("first"),
                fn("max", col("ordinal")).alias("last"),
            ]
        )
        expected = headers.filter(col("item_count") > value(0)).select(
            *keys,
            col("item_count").alias("count"),
            value(0).cast("BIGINT").alias("first"),
            (col("item_count") - value(1)).alias("last"),
        )
        if actual.except_all(expected).union_all(expected.except_all(actual)).limit(1).fetchall():
            raise ValueError("selected archive population counts or ordinals differ")

    def rows(self, relation, **fields):
        from duckdb import ColumnExpression as col

        self._require_open()
        query = _where(self.relations[relation], fields).sort(
            *(col(field) for field in (*KEY_FIELDS, "ordinal"))
        )
        with query.to_arrow_reader(batch_size=256) as reader:
            for batch in reader:
                for row in batch.to_pylist():
                    self._require_open()
                    if relation == POPULATION_HEADERS:
                        for name in ("group_digests", "placement"):
                            row[name] = native_json_loads(row[name])
                    yield row

    def item(self, product_id, collection, partition_key, item_key):
        from duckdb import ColumnExpression as col

        self._require_open()
        matches = (
            _where(
                self.relations[POPULATION_ITEMS],
                dict(
                    product_id=product_id,
                    collection=collection,
                    partition_key=partition_key,
                    address_key=canonical_bytes(item_key).decode(),
                ),
            )
            .select(col("canonical_text"))
            .limit(2)
            .fetchall()
        )
        if not matches:
            raise KeyError(item_key)
        if len(matches) != 1:
            raise ValueError("selected population archive repeats an exact item address")
        return decode_semantic_value(native_json_loads(matches[0][0]))


class LivePopulationArchive:
    """A lazy exact item borrower of an online selected support index and native cut."""

    def __init__(self, connection, index, cut, max_bytes):
        self.connection, self.index, self.cut, self.max_bytes = connection, index, cut, max_bytes
        self.handle = None
        self._last_header = None

    def rows(self, relation, **fields):
        if relation == POPULATION_HEADERS:
            if set(fields) == set(KEY_FIELDS):
                return self._exact_headers(fields)
            return self.index.rows_for(relation, **fields) if fields else self.index.rows(relation)
        if relation != POPULATION_ITEMS or set(fields) != set(KEY_FIELDS):
            raise ValueError("online population items require one exact partition address")
        return self._items(fields)

    def _exact_headers(self, fields):
        header = self._header(tuple(fields[name] for name in KEY_FIELDS))
        if header is not None:
            yield header

    def _header(self, key):
        from .demand_results import stream_selected_archive_population

        if self._last_header is not None and self._last_header[0] == key:
            return self._last_header[1]
        header = self.index.mapping(POPULATION_HEADERS, KEY_FIELDS).get(key)
        if header is None:
            for batch in stream_selected_archive_population(
                self.connection, self._handle(), items=False, partition=key
            ):
                for row in batch:
                    if header is not None:
                        raise ValueError("selected archive repeats an exact population header")
                    header = {name: row[name] for name in HEADER_FIELDS}
                    for name in ("group_digests", "placement"):
                        header[name] = native_json_loads(header[name])
        self._last_header = key, header
        return header

    def _items(self, fields):
        from .demand_results import stream_selected_archive_population

        key = tuple(fields[field] for field in KEY_FIELDS)
        parent = self._header(key)
        if parent is None:
            raise KeyError(key)
        examined = 0
        count = 0
        for batch in stream_selected_archive_population(
            self.connection, self._handle(), items=True, partition=key
        ):
            for row in batch:
                if row["ordinal"] != count or tuple(row[name] for name in KEY_FIELDS) != key:
                    raise ValueError("selected archive rows differ from their requested partition")
                count += 1
                examined += 16 + sum(
                    len(row[name].encode("utf-8"))
                    for name in (*KEY_FIELDS, "address_key", "canonical_text")
                )
                if examined > self.max_bytes:
                    raise ValueError("selected archive population exceeds max_bytes")
                yield row
        if count != parent["item_count"]:
            raise ValueError("selected archive rows differ from the admitted item count")

    def _handle(self):
        from .demand_results import _open_selected_archive

        if self.handle is None:
            self.handle = _open_selected_archive(
                self.connection, self.cut, max_bytes=self.max_bytes, batch_rows=64
            )
        return self.handle

    def item(self, product_id, collection, partition_key, item_key):
        from sqlalchemy import bindparam, func, select
        from sqlalchemy.dialects.postgresql import JSONB

        parent = self._header((product_id, collection, partition_key))
        if parent is None:
            raise KeyError(item_key)
        projection = func.ops.read_selected_archive_item(
            self._handle(),
            product_id,
            collection,
            partition_key,
            bindparam("selected_item_address", list(item_key), type_=JSONB()),
        ).table_valued("product_id", "partition_digest", "canonical_text")
        selected = self.connection.execute(select(projection)).one_or_none()
        if selected is None:
            raise KeyError(item_key)
        actual, digest, content = selected
        if (actual, digest) != (product_id, parent["partition_digest"]):
            raise ValueError("selected archive item differs from its acquired population")
        if content is None:
            raise ValueError("selected archive population item exceeds max_bytes")
        return decode_semantic_value(native_json_loads(content))

    def close(self):
        from .demand_results import _close_selected_archive

        if self.handle is not None:
            _close_selected_archive(self.connection, self.handle)
            self.handle = None
        self._last_header = None


def verify_population_partition(header, items, declaration, item_meaning, item_body):
    """Independently fold ordered already-canonical text into the retained identity."""
    from .data_operation_identity import canonical_identity
    from .data_operation_partitions import PartitionCommitment, _project
    from .reference_resolution import _field

    partition = sha256()
    groups = {name: sha256() for name in declaration["field_groups"]}
    folds = (partition, *groups.values())
    for domain, fold in (
        ("partition", partition),
        *(("partition-group", g) for g in groups.values()),
    ):
        prefix, _ = canonical_identity(domain, []).canonical_input.rsplit(b"[]", 1)
        fold.update(prefix + b"[")

    count = 0
    for row in items:
        if row["ordinal"] != count:
            raise ValueError("selected archive item ordinals differ from their declared order")
        text = row["canonical_text"].encode()
        tagged = native_json_loads(text)
        if canonical_bytes(tagged) != text:
            raise ValueError("selected archive item text is noncanonical")
        item_meaning.validate(tagged)
        decoded = decode_semantic_value(tagged)
        item_body.validate(decoded)
        if not isinstance(decoded, Mapping):
            raise ValueError("selected archive item is not a declared record")
        expected_address = canonical_bytes(
            [_field(decoded, path) for path in declaration["address"]]
        )
        if expected_address.decode() != row["address_key"]:
            raise ValueError("selected archive item address differs from its declared record")
        if count:
            for fold in folds:
                fold.update(b",")
        partition.update(text)
        for name, paths in declaration["field_groups"].items():
            groups[name].update(canonical_bytes(semantic_value(_project(decoded, paths))))
        count += 1
    for fold in folds:
        fold.update(b"]]]")
    if (
        "partition:" + partition.hexdigest() != header["partition_digest"]
        or {name: "partition-group:" + fold.hexdigest() for name, fold in groups.items()}
        != header["group_digests"]
        or count != header["item_count"]
    ):
        raise ValueError("selected archive items differ from the retained partition commitments")
    placement = header["placement"]
    if (
        type(placement) is not dict
        or set(placement) != {"start", "end"}
        or not (
            type(placement["start"]) is int
            and type(placement["end"]) is int
            and 0 <= placement["start"] <= placement["end"]
        )
    ):
        raise ValueError("selected archive partition placement is invalid")
    return PartitionCommitment(
        header["collection"],
        header["partition_key"],
        header["ordinal"],
        placement["start"],
        placement["end"],
        header["partition_digest"],
        count,
    )

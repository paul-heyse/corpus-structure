"""Invocation-owned disk index for exact selected witness transfer and replay.

The native reader owns selection and trust. This temporary index deduplicates its
admitted rows and supports bounded lookups; it grants no persistent authority.
"""

import json
from collections.abc import Mapping

from sqlalchemy import Column, Index, LargeBinary, MetaData, Table, Text, func, literal, select

from .data_operation_json import json_bytes, native_json_loads
from .selected_support_contract import SelectedSupportReader
from .sqlite_scratch import open_scratch, seal_reads

_METADATA = MetaData()
_RECORDS = Table(
    "records",
    _METADATA,
    Column("key", Text, primary_key=True),
    Column("relation", Text, nullable=False),
    Column("payload", LargeBinary, nullable=False),
)
_FRONTIER = Table(
    "frontier",
    _METADATA,
    Column("kind", Text, primary_key=True),
    Column("identity", Text, primary_key=True),
    Column("payload", LargeBinary),
)
_INDEXED = (
    ("id",),
    ("kind_contract",),
    ("product_id", "member_id"),
    ("product_id", "collection", "partition_key"),
    ("derivation_id", "role", "position"),
    ("derivation_id", "occurrence"),
)


def _member(field: str, *, indexed: bool):
    path = "$.record." + (field if field.isidentifier() else json.dumps(field, ensure_ascii=False))
    return func.json_extract(_RECORDS.c.payload, literal(path, literal_execute=indexed))


for _fields in _INDEXED:
    Index(
        "record_" + "_".join(_fields),
        _RECORDS.c.relation,
        *(_member(field, indexed=True) for field in _fields),
    )


def _selected(relation, fields, values):
    indexed = any(group[: len(fields)] == fields for group in _INDEXED)
    return select(_RECORDS.c.payload).where(
        _RECORDS.c.relation == relation,
        *(
            _member(field, indexed=indexed) == literal(value)
            for field, value in zip(fields, values, strict=True)
        ),
    )


class _RecordMapping(Mapping):
    """Private disk-backed transfer index; JSON IDs alone enter SQLite expressions."""

    def __init__(self, index, relation, fields):
        self.index, self.relation, self.fields = index, relation, fields

    def __getitem__(self, key):
        values = (key,) if len(self.fields) == 1 else key
        rows = self.index.connection.execute(
            _selected(self.relation, self.fields, values).limit(2)
        ).fetchall()
        if not rows:
            raise KeyError(key)
        if len(rows) != 1:
            raise ValueError("detached records repeat a nominal identity")
        return self.index.reader.loads(rows[0][0], validate=False)["record"]

    def __iter__(self):
        for row in self.values():
            yield (
                row[self.fields[0]]
                if len(self.fields) == 1
                else tuple(row[field] for field in self.fields)
            )

    def __len__(self):
        return self.index.connection.execute(
            select(func.count()).select_from(_RECORDS).where(_RECORDS.c.relation == self.relation)
        ).fetchone()[0]

    def values(self):
        return self.index.rows(self.relation)


class SelectedRecordIndex:
    def __init__(self, path, *, reader=None):
        self.reader = SelectedSupportReader() if reader is None else reader
        self.connection = open_scratch(path)
        self.retained_bytes = 0
        self.retained_records = 0
        self.cut = None
        self.has_frontier = False
        try:
            _METADATA.create_all(self.connection)
        except BaseException:
            self.connection.close()
            raise

    def freeze(self):
        """Seal the acquired support against writes through this private connection."""
        seal_reads(self.connection)

    def append(self, payload, *, allow_equal=False):
        row = self.reader.loads(payload)
        previous = self.connection.execute(
            select(_RECORDS.c.payload).where(_RECORDS.c.key == row["key"])
        ).fetchone()
        if previous is not None:
            if allow_equal and previous[0] == payload:
                return
            raise ValueError("detached closure repeats a selected record key")
        self.connection.execute(
            _RECORDS.insert().values(key=row["key"], relation=row["relation"], payload=payload)
        )
        self.retained_bytes += len(payload)
        self.retained_records += 1

    def append_page(self, page):
        """Retain exact pinned frontier projections separately from raw support rows."""
        from .demand_results import CutSelection

        cut = CutSelection.from_native(page)
        if self.cut is not None and self.cut.content != cut.content:
            raise ValueError("selected frontier pages belong to different native cuts")
        self.cut, self.has_frontier = cut, True
        for kind, identity_field in (
            ("obligations", "obligation_id"),
            ("uses", "use_id"),
            ("original_source_admissions", "admission_id"),
        ):
            population = page.get(kind, ()) if kind == "original_source_admissions" else page[kind]
            for row in population:
                # Body-bearing products already have native record custody. Keep the
                # exact frontier/selection fields without copying their bodies again.
                value = {key: value for key, value in row.items() if key != "products"}
                identity, payload = row[identity_field], json_bytes(value)
                previous = self.connection.execute(
                    select(_FRONTIER.c.payload).where(
                        _FRONTIER.c.kind == kind, _FRONTIER.c.identity == identity
                    )
                ).fetchone()
                if previous is not None:
                    if previous[0] != payload:
                        raise ValueError(
                            "selected frontier repeats an identity with different facts"
                        )
                    continue
                self.connection.execute(
                    _FRONTIER.insert().values(kind=kind, identity=identity, payload=payload)
                )
                self.retained_bytes += len(payload)
                self.retained_records += 1

    def frontier_rows(self, kind):
        for (payload,) in self.connection.execute(
            select(_FRONTIER.c.payload)
            .where(_FRONTIER.c.kind == kind)
            .order_by(_FRONTIER.c.identity)
        ):
            yield self.reader.frontier(kind, native_json_loads(payload))

    def frontier_row(self, kind, identity):
        payload = self.connection.scalar(
            select(_FRONTIER.c.payload).where(
                _FRONTIER.c.kind == kind, _FRONTIER.c.identity == identity
            )
        )
        return None if payload is None else self.reader.frontier(kind, native_json_loads(payload))

    def records(self):
        for (payload,) in self.connection.execute(
            select(_RECORDS.c.payload).order_by(_RECORDS.c.key)
        ):
            yield self.reader.loads(payload, validate=False)

    def rows(self, relation):
        for (payload,) in self.connection.execute(
            select(_RECORDS.c.payload)
            .where(_RECORDS.c.relation == relation)
            .order_by(_RECORDS.c.key)
        ):
            yield self.reader.loads(payload, validate=False)["record"]

    def rows_for(self, relation, **fields):
        for (payload,) in self.connection.execute(
            _selected(relation, tuple(fields), fields.values()).order_by(_RECORDS.c.key)
        ):
            yield self.reader.loads(payload, validate=False)["record"]

    def mapping(self, relation, fields):
        return _RecordMapping(self, relation, tuple(fields))

    def close(self):
        self.connection.close()

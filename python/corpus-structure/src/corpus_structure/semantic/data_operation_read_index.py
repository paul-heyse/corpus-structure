"""Invocation-owned disk index for exact selected witness transfer and replay.

The native reader owns selection and trust. This temporary index deduplicates its
admitted rows and supports bounded lookups; it grants no persistent authority.
"""

import sqlite3
from collections.abc import Mapping

from .data_operation_json import wire_json_loads


class _RecordMapping(Mapping):
    """Private disk-backed transfer index; JSON IDs alone enter SQLite expressions."""

    def __init__(self, index, relation, fields):
        self.index, self.relation, self.fields = index, relation, fields

    def __getitem__(self, key):
        values = (key,) if len(self.fields) == 1 else key
        predicates = " AND ".join(
            "json_extract(payload, '$.record." + field + "')=?" for field in self.fields
        )
        rows = self.index.connection.execute(
            "SELECT payload FROM records WHERE relation=? AND " + predicates + " LIMIT 2",
            (self.relation, *values),
        ).fetchall()
        if not rows:
            raise KeyError(key)
        if len(rows) != 1:
            raise ValueError("detached records repeat a nominal identity")
        return wire_json_loads(rows[0][0])["record"]

    def __iter__(self):
        for row in self.values():
            yield (
                row[self.fields[0]]
                if len(self.fields) == 1
                else tuple(row[field] for field in self.fields)
            )

    def __len__(self):
        return self.index.connection.execute(
            "SELECT count(*) FROM records WHERE relation=?", (self.relation,)
        ).fetchone()[0]

    def values(self):
        return self.index.rows(self.relation)


class SelectedRecordIndex:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            "CREATE TABLE records(key TEXT PRIMARY KEY, relation TEXT NOT NULL, payload BLOB NOT NULL)"
        )
        for fields in (
            ("id",),
            ("kind_contract",),
            ("product_id", "member_id"),
            ("derivation_id", "role", "position"),
            ("derivation_id", "occurrence"),
        ):
            expression = ",".join(
                "json_extract(payload, '$.record." + field + "')" for field in fields
            )
            self.connection.execute(
                "CREATE INDEX record_"
                + "_".join(fields)
                + " ON records(relation,"
                + expression
                + ")"
            )

    def append(self, payload, *, allow_equal=False):
        row = wire_json_loads(payload)
        previous = self.connection.execute(
            "SELECT payload FROM records WHERE key=?", (row["key"],)
        ).fetchone()
        if previous is not None:
            if allow_equal and previous[0] == payload:
                return
            raise ValueError("detached closure repeats a selected record key")
        self.connection.execute(
            "INSERT INTO records VALUES(?,?,?)", (row["key"], row["relation"], payload)
        )

    def rows(self, relation):
        for (payload,) in self.connection.execute(
            "SELECT payload FROM records WHERE relation=? ORDER BY key", (relation,)
        ):
            yield wire_json_loads(payload)["record"]

    def rows_for(self, relation, **fields):
        predicates = " AND ".join(
            "json_extract(payload, '$.record." + field + "')=?" for field in fields
        )
        for (payload,) in self.connection.execute(
            "SELECT payload FROM records WHERE relation=? AND " + predicates + " ORDER BY key",
            (relation, *fields.values()),
        ):
            yield wire_json_loads(payload)["record"]

    def mapping(self, relation, fields):
        return _RecordMapping(self, relation, fields)

    def close(self):
        self.connection.close()

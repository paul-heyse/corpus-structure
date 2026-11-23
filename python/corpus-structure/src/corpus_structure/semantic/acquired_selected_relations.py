"""Read selected facts through the same operations in live and detached custody."""

from collections import defaultdict
from collections.abc import Iterator, Mapping
from typing import Any, Protocol

import pyarrow as pa

from .data_operation_json import json_bytes, native_json_loads
from .selected_support_contract import SelectedSupportReader

_INDEX_FIELDS = (
    "id",
    "product_id",
    "member_id",
    "derivation_id",
    "use_id",
    "kind_contract",
    "role",
    "position",
    "occurrence",
    "collection",
    "partition_key",
)
_FRONTIER_IDENTITIES = {
    "obligations": "obligation_id",
    "uses": "use_id",
    "original_source_admissions": "admission_id",
}


class AcquiredSelectedRelations(Protocol):
    reader: SelectedSupportReader
    cut: Any
    has_frontier: bool
    population_archive: Any
    retained_bytes: int
    retained_records: int

    def rows(self, relation: str) -> Iterator[dict]: ...
    def rows_for(self, relation: str, **fields: Any) -> Iterator[dict]: ...
    def mapping(self, relation: str, fields) -> Mapping: ...
    def frontier_rows(self, kind: str) -> Iterator[dict]: ...
    def frontier_row(self, kind: str, identity: str) -> dict | None: ...
    def records(self) -> Iterator[dict]: ...


class _SelectedMapping(Mapping):
    def __init__(self, relations, relation, fields):
        self.relations = relations
        self.relation = relation
        self.fields = tuple(fields)

    def __getitem__(self, key):
        values = (key,) if len(self.fields) == 1 else key
        rows = self.relations.rows_for(self.relation, **dict(zip(self.fields, values, strict=True)))
        row = next(rows, None)
        if row is None:
            raise KeyError(key)
        if next(rows, None) is not None:
            raise ValueError("selected records repeat a nominal identity")
        return row

    def __iter__(self):
        for row in self.values():
            if len(self.fields) == 1:
                yield row[self.fields[0]]
            else:
                yield tuple(row[field] for field in self.fields)

    def __len__(self):
        return sum(1 for _ in self.values())

    def values(self):
        return self.relations.rows(self.relation)


class SelectedRelationLookup:
    def mapping(self, relation, fields):
        return _SelectedMapping(self, relation, fields)


class LiveSelectedRelations(SelectedRelationLookup):
    """An invocation owns a bounded set of support facts, with columnar lookup keys."""

    def __init__(self):
        self.reader = SelectedSupportReader()
        self.cut = None
        self.has_frontier = False
        self.population_archive = None
        self.retained_bytes = 0
        self.retained_records = 0
        self._pending: dict[str, tuple[str, bytes, dict[str, bytes]]] | None = {}
        self._relations = {}
        self._lookups = {}
        self._frontier = defaultdict(dict)
        self._closed = False

    def _require_open(self):
        if self._closed:
            raise ValueError("selected relations are closed")

    def append(self, payload, *, allow_equal=False):
        self.append_record(native_json_loads(payload), payload=payload, allow_equal=allow_equal)

    def append_record(self, row, *, payload=None, allow_equal=False):
        if self._pending is None:
            raise ValueError("selected relations are already sealed")
        if payload is None:
            payload = json_bytes(row)
        key = row["key"]
        previous = self._pending.get(key)
        if previous is not None:
            if allow_equal and previous[1] == payload:
                return
            raise ValueError("selected closure repeats a record key")
        record = row["record"]
        keys = {field: json_bytes(record[field]) for field in _INDEX_FIELDS if field in record}
        self._pending[key] = (row["relation"], payload, keys)
        self.retained_bytes += len(payload)
        self.retained_records += 1

    def append_page(self, page):
        if self._pending is None:
            raise ValueError("selected relations are already sealed")
        from .demand_results import CutSelection

        cut = CutSelection.from_native(page)
        if self.cut is not None and self.cut.content != cut.content:
            raise ValueError("selected frontier pages belong to different native cuts")
        self.cut, self.has_frontier = cut, True
        for kind, field in _FRONTIER_IDENTITIES.items():
            for row in page.get(kind, ()):
                identity = row[field]
                payload = json_bytes(
                    {key: value for key, value in row.items() if key != "products"}
                )
                previous = self._frontier[kind].get(identity)
                if previous is not None:
                    if previous != payload:
                        raise ValueError(
                            "selected frontier repeats an identity with different facts"
                        )
                    continue
                self._frontier[kind][identity] = payload
                self.retained_bytes += len(payload)
                self.retained_records += 1

    def freeze(self):
        self._require_open()
        if self._pending is None:
            return
        grouped = defaultdict(list)
        for key, (relation, payload, lookup) in sorted(self._pending.items()):
            grouped[relation].append((key, payload, lookup))
        self._pending = None
        for relation, rows in grouped.items():
            keys, payloads, records = zip(*rows, strict=True)
            columns = {
                field: pa.array(
                    [record.get(field) for record in records],
                    type=pa.binary(),
                )
                for field in _INDEX_FIELDS
                if any(field in record for record in records)
            }
            self._relations[relation] = pa.table(
                {
                    "_key": pa.array(keys, type=pa.string()),
                    "_payload": pa.array(payloads, type=pa.large_binary()),
                    **columns,
                }
            )

    def rows(self, relation):
        yield from self.rows_for(relation)

    def rows_for(self, relation, **fields):
        self.freeze()
        table = self._relations.get(relation)
        if table is None:
            return
        indexed = tuple(
            sorted(name for name in fields if name in _INDEX_FIELDS and name in table.column_names)
        )
        unresolved = {name: value for name, value in fields.items() if name not in indexed}
        offsets = range(table.num_rows)
        if indexed:
            index_key = (relation, indexed)
            if index_key not in self._lookups:
                lookup = defaultdict(list)
                for offset, key in enumerate(
                    zip(*(table[field].to_pylist() for field in indexed), strict=True)
                ):
                    lookup[key].append(offset)
                self._lookups[index_key] = lookup
            offsets = self._lookups[index_key].get(
                tuple(json_bytes(fields[name]) for name in indexed), ()
            )
        for offset in offsets:
            payload = table["_payload"][offset]
            row = self.reader.loads(payload.as_py(), validate=False)["record"]
            if all(field in row and row[field] == value for field, value in unresolved.items()):
                yield row

    def frontier_rows(self, kind):
        self._require_open()
        for _, payload in sorted(self._frontier[kind].items()):
            yield self.reader.frontier(kind, native_json_loads(payload))

    def frontier_row(self, kind, identity):
        self._require_open()
        payload = self._frontier[kind].get(identity)
        return None if payload is None else self.reader.frontier(kind, native_json_loads(payload))

    def records(self):
        self.freeze()
        for _, payload in sorted(
            (key.as_py(), payload)
            for table in self._relations.values()
            for key, payload in zip(table["_key"], table["_payload"], strict=True)
        ):
            yield self.reader.loads(payload.as_py(), validate=False)

    def close(self):
        self._closed = True
        self._pending = None
        self._relations.clear()
        self._lookups.clear()
        self._frontier.clear()
        self.population_archive = None

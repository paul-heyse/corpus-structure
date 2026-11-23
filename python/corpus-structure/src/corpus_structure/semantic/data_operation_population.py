"""Model-derived Arrow populations with exact scalar and field-state interpretation."""

from __future__ import annotations

import json
from collections.abc import Generator, Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, replace
from decimal import Decimal
from functools import cached_property
from typing import Any, Literal

import pyarrow as pa

from .data_operation_partitions import validate_collection_paths
from .data_operation_value_codec import decode_semantic_value, semantic_value
from .data_operation_values import OptionalValue
from .identity import canonical_bytes
from .population_ipc import SealedPopulationIpc
from .types import PreparedRelease, PropertyDefinition
from .value_codec import decimal_digit_limit

_MISSING = object()
_STATES: dict[Literal["known-absent", "unknown", "unavailable"], int] = {
    "known-absent": 3,
    "unknown": 4,
    "unavailable": 5,
}
_INTEGER = pa.struct([pa.field("narrow", pa.int64()), pa.field("wide", pa.string())])


@dataclass(frozen=True)
class _ValueShape:
    arrow: pa.DataType
    encoding: str
    fields: tuple[tuple[PropertyDefinition, _ValueShape], ...] = ()
    members: tuple[tuple[str, _ValueShape], ...] = ()
    child: _ValueShape | None = None
    choices: frozenset[str] | None = None

    def encode(self, value: Any, digits: int):
        if self.encoding == "record":
            if not isinstance(value, Mapping):
                raise ValueError("population record requires a mapping")
            names = {prop.name for prop, _ in self.fields}
            if value.keys() - names:
                raise ValueError("population record contains undeclared fields")
            return {
                prop.name: _encode_field(prop, shape, value.get(prop.name, _MISSING), digits)
                for prop, shape in self.fields
            }
        if self.encoding == "variant":
            matches = []
            for name, shape in self.members:
                try:
                    encoded = shape.encode(value, digits)
                except TypeError, ValueError:
                    continue
                matches.append((name, encoded))
            if len(matches) != 1:
                raise ValueError("population record requires one concrete nominal variant")
            name, encoded = matches[0]
            return {
                "variant": name,
                **{key: encoded if key == name else None for key, _ in self.members},
            }
        if self.encoding == "list":
            if not isinstance(value, (list, tuple)):
                raise ValueError("population multivalued field requires a sequence")
            assert self.child is not None
            return [self.child.encode(item, digits) for item in value]
        if self.encoding == "integer":
            if type(value) is not int:
                raise ValueError("population integer requires an exact integer")
            return (
                {"narrow": value, "wide": None}
                if -(2**63) <= value < 2**63
                else {"narrow": None, "wide": str(value)}
            )
        if self.encoding == "int64":
            if type(value) is not int or not -(2**63) <= value < 2**63:
                raise ValueError("population bounded integer exceeds int64")
            return value
        if self.encoding in {"string", "boolean"}:
            expected = str if self.encoding == "string" else bool
            if type(value) is not expected:
                raise ValueError("population scalar differs from its declared type")
            if self.choices is not None and value not in self.choices:
                raise ValueError("population enum value is outside its declared range")
            return value
        tagged = semantic_value(value, decimal_fixed_point_digits=digits)
        if self.encoding != "json" and tagged[0] != self.encoding:
            raise ValueError("population scalar differs from its exact declared type")
        return canonical_bytes(tagged).decode()

    def decode(self, value, digits: int):
        if value is None:
            raise ValueError("population value requires its declared payload")
        if self.encoding == "record":
            if value is None:
                raise ValueError("population record cannot be null")
            result = {}
            for prop, shape in self.fields:
                decoded = _decode_field(prop, shape, value[prop.name], digits)
                if decoded is not _MISSING:
                    result[prop.name] = decoded
            return result
        if self.encoding == "variant":
            name = value["variant"]
            selected = dict(self.members).get(name)
            if (
                selected is None
                or value[name] is None
                or any(value[key] is not None for key, _ in self.members if key != name)
            ):
                raise ValueError("population has inconsistent nominal variant columns")
            return selected.decode(value[name], digits)
        if self.encoding == "list":
            assert self.child is not None
            return [self.child.decode(item, digits) for item in value]
        if self.encoding == "integer":
            narrow, wide = value["narrow"], value["wide"]
            if (narrow is None) == (wide is None):
                raise ValueError("population integer requires exactly one representation")
            if wide is None:
                return narrow
            parsed = int(wide)
            if str(parsed) != wide or -(2**63) <= parsed < 2**63:
                raise ValueError("population wide integer is noncanonical")
            return parsed
        if self.encoding in {"string", "boolean", "int64"}:
            if value is None:
                raise ValueError("population required scalar cannot be null")
            if self.choices is not None and value not in self.choices:
                raise ValueError("population enum value is outside its declared range")
            return value
        if value is None:
            raise ValueError("population exact scalar cannot be null")
        tagged = json.loads(value)
        decoded = decode_semantic_value(tagged, decimal_fixed_point_digits=digits)
        if canonical_bytes(tagged).decode() != value or (
            self.encoding != "json" and tagged[0] != self.encoding
        ):
            raise ValueError("population exact scalar is noncanonical")
        return decoded


def _field_type(prop, shape):
    if prop.required and not prop.nullable:
        return shape.arrow
    return pa.struct(
        [pa.field("state", pa.uint8(), nullable=False), pa.field("value", shape.arrow)]
    )


def _validate_property(prop, value):
    if value is None:
        if not prop.nullable:
            raise ValueError("population field does not permit explicit null")
        return
    if prop.equals_string is not None and value != prop.equals_string:
        raise ValueError("population field differs from its declared constant")
    if prop.multivalued:
        if prop.minimum_cardinality is not None and len(value) < prop.minimum_cardinality:
            raise ValueError("population field has too few values")
        if prop.maximum_cardinality is not None and len(value) > prop.maximum_cardinality:
            raise ValueError("population field has too many values")
    elif type(value) in {int, float, Decimal}:
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError("population numeric value must be finite")
        if prop.minimum is not None and number < Decimal(prop.minimum):
            raise ValueError("population scalar is below its declared minimum")
        if prop.maximum is not None and number > Decimal(prop.maximum):
            raise ValueError("population scalar exceeds its declared maximum")
    if isinstance(value, str) and (prop.pattern or prop.patterns):
        import re

        if any(
            re.search(pattern, value) is None
            for pattern in (prop.pattern, *prop.patterns)
            if pattern
        ):
            raise ValueError("population scalar violates its declared pattern")


def _encode_field(prop, shape, value, digits):
    state = 1
    if value is _MISSING:
        if prop.required:
            raise ValueError("population record lacks a required field")
        state, value = 0, None
    elif isinstance(value, OptionalValue):
        if prop.required and not prop.nullable:
            raise ValueError("required population field does not admit optional states")
        state = 6 if value.state == "present" else _STATES[value.state]
        if state != 6 and value.value is not None:
            raise ValueError("population absence state cannot carry a value")
        value = value.value
    elif value is None:
        _validate_property(prop, value)
        state = 2
    if state in {1, 6}:
        _validate_property(prop, value)
        encoded = None if value is None else shape.encode(value, digits)
    else:
        encoded = None
    return encoded if prop.required and not prop.nullable else {"state": state, "value": encoded}


def _decode_field(prop, shape, value, digits):
    if prop.required and not prop.nullable:
        decoded = shape.decode(value, digits)
        _validate_property(prop, decoded)
        return decoded
    if value is None or value["state"] not in range(7):
        raise ValueError("population field requires an explicit valid state")
    state, payload = value["state"], value["value"]
    if state in {0, 2, 3, 4, 5}:
        if payload is not None:
            raise ValueError("population absence/null state has a payload")
        if state == 0:
            if prop.required:
                raise ValueError("population record lacks a required field")
            return _MISSING
        if state == 2:
            _validate_property(prop, None)
            return None
        return OptionalValue(next(name for name, code in _STATES.items() if code == state))
    decoded = None if payload is None and state == 6 else shape.decode(payload, digits)
    _validate_property(prop, decoded)
    return OptionalValue("present", decoded) if state == 6 else decoded


def _project_item_shape(shape: _ValueShape, fields: set[str]) -> _ValueShape:
    if shape.encoding == "record":
        selected = tuple((prop, child) for prop, child in shape.fields if prop.name in fields)
        return replace(
            shape,
            arrow=pa.struct([field for field in shape.arrow if field.name in fields]),
            fields=selected,
        )
    if shape.encoding != "variant":
        raise ValueError("population projection requires a model-derived record layout")
    # Selecting nominal arms exposes which concrete arm is present. A projected
    # discriminator must already distinguish those arms under the read contract.
    constants = [
        {
            prop.name: prop.equals_string
            for prop, _ in member.fields
            if prop.equals_string is not None
        }
        for _, member in shape.members
    ]
    if not any(
        all(field in values for values in constants)
        and len({values[field] for values in constants}) == len(constants)
        for field in fields
    ):
        raise ValueError("population projection would expose an undeclared nominal variant")
    members = tuple((name, _project_item_shape(member, fields)) for name, member in shape.members)
    arrows = [shape.arrow.field("variant")]
    arrows.extend(shape.arrow.field(name).with_type(member.arrow) for name, member in members)
    return replace(
        shape,
        arrow=pa.struct(arrows),
        members=members,
    )


def _project_member(values, shape: _ValueShape):
    """Share only selected child arrays and keep each nominal arm's validity."""
    return pa.chunked_array(
        [
            pa.StructArray.from_arrays(
                [chunk.field(field.name) for field in shape.arrow],
                fields=list(shape.arrow),
                mask=chunk.is_null(),
            )
            for chunk in values.chunks
        ],
        type=shape.arrow,
    )


@dataclass(frozen=True)
class PopulationLayout:
    """One release-bound item shape. Admission rules and authority remain with their owners."""

    schema: pa.Schema
    _shape: _ValueShape
    _digits: int
    _field_groups: tuple[tuple[str, tuple[str, ...]], ...]
    groups: tuple[str, ...] = ()

    def for_groups(self, groups: Iterable[str]) -> PopulationLayout:
        """Derive the exact selected top-level field groups from the captured declaration."""
        selected = tuple(sorted(set(groups)))
        if selected == self.groups and selected:
            return self
        declared = dict(self._field_groups)
        if (
            not selected
            or not set(selected) <= declared.keys()
            or (self.groups and not set(selected) <= set(self.groups))
        ):
            raise ValueError("population projection requires admitted field groups")
        fields = {path for name in selected for path in declared[name]}
        if any("." in path for path in fields):
            raise ValueError("nested population field groups require a nested projection layout")
        shape = _project_item_shape(self._shape, fields)
        metadata = dict(self.schema.metadata or {})
        metadata[b"projection_groups"] = canonical_bytes(selected)
        return replace(
            self,
            schema=pa.schema(list(shape.arrow), metadata=metadata),
            _shape=shape,
            groups=selected,
        )

    def from_rows(self, rows: Iterable[Mapping[str, Any]]) -> AcquiredPopulation:
        encoded = [self._shape.encode(row, self._digits) for row in rows]
        table = pa.Table.from_pylist(encoded, schema=self.schema)
        return AcquiredPopulation._from_table(self, _immutable_table(table))

    def acquire(self, table: pa.Table) -> AcquiredPopulation:
        if not table.schema.equals(self.schema, check_metadata=True):
            raise ValueError("population table differs from its release schema")
        return self._acquire_owned(_immutable_table(table))

    @contextmanager
    def open_ipc(
        self,
        payload: SealedPopulationIpc,
        *,
        request_digest: str,
        projection_digest: str,
        max_bytes: int,
    ) -> Generator[AcquiredPopulation]:
        """Validate the authenticated mapping and borrow it without another IPC copy."""
        with payload.open(
            schema=self.schema,
            request_digest=request_digest,
            projection_digest=projection_digest,
            max_bytes=max_bytes,
        ) as table:
            yield self._acquire_owned(table)

    def _acquire_owned(self, table: pa.Table) -> AcquiredPopulation:
        table.validate(full=True)
        for batch in table.to_batches():
            for row in batch.to_pylist():
                self._shape.decode(row, self._digits)
        return AcquiredPopulation._from_table(self, table)


def _immutable_table(table: pa.Table) -> pa.Table:
    """Detach external buffers and expose immutable backing bytes at acquisition."""
    sink = pa.BufferOutputStream()
    with pa.ipc.new_file(sink, table.schema) as writer:
        writer.write_table(table)
    content = sink.getvalue().to_pybytes()
    with pa.ipc.open_file(pa.BufferReader(content)) as reader:
        return reader.read_all()


@dataclass(frozen=True, init=False)
class AcquiredPopulation:
    layout: PopulationLayout
    table: pa.Table

    def __init__(self, *args, **kwargs):
        raise TypeError("population requires layout acquisition")

    @classmethod
    def _from_table(cls, layout, table):
        value = object.__new__(cls)
        object.__setattr__(value, "layout", layout)
        object.__setattr__(value, "table", table)
        return value

    def project(self, names: Iterable[str]) -> pa.Table:
        return self.table.select(list(names))

    def project_groups(self, groups: Iterable[str]) -> AcquiredPopulation:
        layout = self.layout.for_groups(groups)
        if layout is self.layout:
            return self
        if layout._shape.encoding == "variant":
            arrays = [self.table["variant"]]
            arrays.extend(
                _project_member(self.table[name], member) for name, member in layout._shape.members
            )
            table = pa.Table.from_arrays(arrays, schema=layout.schema)
        else:
            table = self.table.select(layout.schema.names).replace_schema_metadata(
                layout.schema.metadata
            )
        return AcquiredPopulation._from_table(layout, table)

    @cached_property
    def _rows(self):
        from .data_operation_consumers import _freeze_consumer

        return tuple(
            _freeze_consumer(self.layout._shape.decode(row, self.layout._digits))
            for batch in self.table.to_batches()
            for row in batch.to_pylist()
        )

    def immutable_rows(self):
        """Reuse immutable nominal rows for this acquired partition's lifetime."""
        return iter(self._rows)

    def rows(self):
        """Return detached working records with the decoded public container shapes."""
        return (_working_row(row) for row in self._rows)


def _working_row(value):
    from .data_operation_values import CollectionValue

    if isinstance(value, OptionalValue):
        return OptionalValue(value.state, _working_row(value.value))
    if isinstance(value, CollectionValue):
        return CollectionValue(value.kind, tuple(_working_row(item) for item in value.members))
    if isinstance(value, Mapping):
        return {name: _working_row(item) for name, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_working_row(item) for item in value]
    return value


def population_layout(prepared: PreparedRelease, kind, collection: str) -> PopulationLayout:
    """Derive a collection's exact Arrow shape from its effective model and declarations."""
    definition = prepared.index.definitions[kind.name]
    declaration = json.loads(kind.facts)["collections"][collection]
    if declaration["unit"] != "partitioned":
        raise ValueError("typed population requires a partitioned collection")
    slot = next(prop for prop in definition.properties if prop.name == collection)
    validate_collection_paths(declaration, slot.range, prepared.index.definitions)
    recipe = json.loads(
        next(
            artifact.content
            for artifact in prepared.artifacts
            if artifact.kind == "boundary_recipe.json"
        )
    )
    primitives = recipe["primitives"]

    def record(name, parents):
        if name in parents:
            raise ValueError("recursive population records need an explicit finite layout")
        current = prepared.index.definitions[name]
        if current.abstract:
            members = tuple(
                (child.name, record(child.name, (*parents, name)))
                for child in prepared.definitions
                if name in child.ancestors and not child.abstract
            )
            if not members:
                raise ValueError("population abstract range lacks concrete variants")
            fields = [
                pa.field("variant", pa.string(), nullable=False),
                *(pa.field(key, shape.arrow) for key, shape in members),
            ]
            return _ValueShape(pa.struct(fields), "variant", members=members)
        fields = tuple(
            (prop, property_shape(prop, (*parents, name))) for prop in current.properties
        )
        return _ValueShape(
            pa.struct(
                [
                    pa.field(prop.name, _field_type(prop, shape), nullable=False)
                    for prop, shape in fields
                ]
            ),
            "record",
            fields=fields,
        )

    def property_shape(prop, parents):
        if prop.range in prepared.index.definitions and prop.inlined:
            shape = record(prop.range, parents)
        elif prop.range in prepared.vocabulary_names or prop.range in prepared.index.definitions:
            choices = (
                prepared.enum_members(prop.range)
                if prop.range in prepared.vocabulary_names
                else None
            )
            shape = _ValueShape(pa.string(), "string", choices=choices)
        else:
            primitive = primitives.get(prop.range, prop.range)
            primitive = {
                "uri": "string",
                "uriorcurie": "string",
                "double": "float",
            }.get(primitive, primitive)
            if primitive == "integer":
                bounded = (
                    prop.minimum is not None
                    and prop.maximum is not None
                    and -(2**63) <= int(prop.minimum) <= int(prop.maximum) < 2**63
                )
                shape = _ValueShape(
                    pa.int64() if bounded else _INTEGER,
                    "int64" if bounded else "integer",
                )
            elif primitive in {"string", "boolean"}:
                shape = _ValueShape(pa.string() if primitive == "string" else pa.bool_(), primitive)
            elif primitive in {"decimal", "float", "date", "datetime", "json"}:
                shape = _ValueShape(pa.string(), primitive)
            else:
                raise ValueError("unsupported population primitive " + primitive)
        if prop.multivalued:
            shape = _ValueShape(
                pa.list_(pa.field("item", shape.arrow, nullable=False)),
                "list",
                child=shape,
            )
        return shape

    shape = record(slot.range, ())
    metadata = {
        "release_id": prepared.release_id,
        "kind": kind.semantic_id,
        "collection": collection,
        "population_codec": "1",
    }
    return PopulationLayout(
        pa.schema(list(shape.arrow), metadata=metadata),
        shape,
        decimal_digit_limit(),
        tuple((name, tuple(paths)) for name, paths in sorted(declaration["field_groups"].items())),
    )

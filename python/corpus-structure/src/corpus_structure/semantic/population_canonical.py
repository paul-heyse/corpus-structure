"""Canonical item text and ordered commitments from acquired population columns."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256

import pyarrow as pa
import pyarrow.compute as pc
from duckdb import CaseExpression, Expression, LambdaExpression
from duckdb import ColumnExpression as col
from duckdb import ConstantExpression as literal
from duckdb import FunctionExpression as call

from corpus_structure.analytics import AnalyticalConnection, configured

from .data_operation_identity import ENCODING_VERSION
from .data_operation_population import AcquiredPopulation, _ValueShape
from .identity import canonical_bytes
from .types import PropertyDefinition

_ITEM_ORDINAL = "item_ordinal"
_CANONICAL_TEXT = "canonical_text"
_ITEM_SCHEMA = pa.schema(
    [
        pa.field(_ITEM_ORDINAL, pa.int32(), nullable=False),
        pa.field(_CANONICAL_TEXT, pa.string(), nullable=False),
    ]
)

type _Fields = Callable[[str], Expression]


@dataclass(frozen=True, slots=True)
class CanonicalPopulation:
    items: pa.Table
    partition_digest: str
    group_digests: dict[str, str]


def _concat(*parts: Expression | str) -> Expression:
    return call("concat", *(literal(part) if isinstance(part, str) else part for part in parts))


def _encoded_json_string(value: Expression) -> Expression:
    encoded = call("to_json", value).cast("VARCHAR")
    # Protect literal backslashes before normalizing DuckDB's upper-case C0 escapes.
    # A raw C0 character cannot collide with the output of to_json.
    marker = chr(1)
    normalized = call("replace", encoded, literal("\\\\"), literal(marker))
    for control in (11, 14, 15, *range(26, 32)):
        upper = f"\\u{control:04X}"
        normalized = call("replace", normalized, literal(upper), literal(upper.lower()))
    normalized = call("replace", normalized, literal(marker), literal("\\\\"))
    has_control = call("regexp_matches", value, literal(r"[\x0b\x0e\x0f\x1a-\x1f]"))
    return CaseExpression(has_control, normalized).otherwise(encoded)


def _tag(tag: str, encoded: Expression) -> Expression:
    return _concat(f'["{tag}",', encoded, "]")


def _extract(value: Expression) -> _Fields:
    return lambda name: call("struct_extract", value, literal(name))


def _mapping(fields: list[tuple[str, Expression]]) -> Expression:
    if not fields:
        return literal('["mapping",[]]')
    pairs = call(
        "list_value",
        *(
            call("row", literal(canonical_bytes(name).decode()), value)
            for name, value in sorted(fields, key=lambda field: field[0])
        ),
    )
    pair = col("pair")
    key = call("struct_extract", pair, literal(1))
    value = call("struct_extract", pair, literal(2))
    present = call("list_filter", pairs, LambdaExpression("pair", value.is_not_null()))
    encoded = call(
        "list_transform", present, LambdaExpression("pair", _concat("[", key, ",", value, "]"))
    )
    contents = call("array_to_string", encoded, literal(","))
    return _concat('["mapping",[', contents, "]]")


def _variant(
    shape: _ValueShape, get: _Fields, branch: Callable[[_ValueShape, _Fields], Expression]
) -> Expression:
    variant = get("variant")
    result = literal(None)
    for name, child in reversed(shape.members):
        encoded = branch(child, _extract(get(name)))
        result = CaseExpression(variant == literal(name), encoded).otherwise(result)
    return result


def _field(
    prop: PropertyDefinition, shape: _ValueShape, physical: Expression, depth: int
) -> Expression:
    if prop.required and not prop.nullable:
        return _value(shape, physical, depth)
    get = _extract(physical)
    state, payload = get("state"), get("value")
    present = state == literal(6)
    value = _concat(
        CaseExpression(present, literal('["present",')).otherwise(literal("")),
        CaseExpression(payload.is_null(), literal('["null"]')).otherwise(
            _value(shape, payload, depth)
        ),
        CaseExpression(present, literal("]")).otherwise(literal("")),
    )
    return (
        CaseExpression(state == literal(0), literal(None))
        .when(state == literal(2), literal('["null"]'))
        .when(state == literal(3), literal('["known-absent"]'))
        .when(state == literal(4), literal('["unknown"]'))
        .when(state == literal(5), literal('["unavailable"]'))
        .otherwise(value)
    )


def _record(shape: _ValueShape, get: _Fields, depth: int) -> Expression:
    if shape.encoding == "variant":
        return _variant(shape, get, lambda member, fields: _record(member, fields, depth))
    if shape.encoding != "record":
        raise ValueError("canonical item requires a nominal record")
    return _mapping(
        [(prop.name, _field(prop, child, get(prop.name), depth)) for prop, child in shape.fields]
    )


def _value(shape: _ValueShape, value: Expression, depth: int) -> Expression:
    match shape.encoding:
        case "record" | "variant":
            return _record(shape, _extract(value), depth)
        case "list":
            assert shape.child is not None
            parameter = f"item_{depth}"
            member = LambdaExpression(parameter, _value(shape.child, col(parameter), depth + 1))
            contents = call("array_to_string", call("list_transform", value, member), literal(","))
            return _tag("sequence", _concat("[", contents, "]"))
        case "int64" | "integer":
            if shape.encoding == "integer":
                get = _extract(value)
                narrow = get("narrow")
                value = CaseExpression(narrow.is_not_null(), narrow.cast("VARCHAR")).otherwise(
                    get("wide")
                )
            return _tag("integer", _concat('"', value.cast("VARCHAR"), '"'))
        case "string":
            return _tag("string", _encoded_json_string(value))
        case "boolean":
            return _tag("boolean", value.cast("VARCHAR"))
        case "decimal" | "float" | "date" | "datetime" | "json":
            # Acquisition already establishes the complete canonical tag and payload.
            return value
        case _:
            raise ValueError(f"unsupported canonical population encoding {shape.encoding!r}")


def _projected(shape: _ValueShape, get: _Fields, path: tuple[str, ...]) -> Expression:
    if shape.encoding == "variant":
        return _variant(shape, get, lambda member, fields: _projected(member, fields, path))
    name, *rest = path
    for prop, child in shape.fields:
        if prop.name == name:
            physical = get(name)
            if not rest:
                return _field(prop, child, physical, 0)
            if prop.required and not prop.nullable:
                return _projected(child, _extract(physical), tuple(rest))
            optional = _extract(physical)
            # The projection traverses plain records. Wrapped present is a value itself.
            nested = _projected(child, _extract(optional("value")), tuple(rest))
            return CaseExpression(optional("state") == literal(1), nested).otherwise(literal(None))
    raise ValueError(f"unresolved canonical population field {'.'.join(path)!r}")


@lru_cache(maxsize=128)
def _projections(
    shape: _ValueShape, field_groups: tuple[tuple[str, tuple[str, ...]], ...]
) -> tuple[Expression, ...]:
    result = [_record(shape, col, 0).alias(_CANONICAL_TEXT)]
    for index, (_, paths) in enumerate(field_groups):
        group = _mapping([(path, _projected(shape, col, tuple(path.split(".")))) for path in paths])
        result.append(group.alias(f"group_{index}"))
    return tuple(result)


class _SequenceCommitment:
    def __init__(self, domain: str):
        self.domain = domain
        prefix = canonical_bytes(["ddo", domain, ENCODING_VERSION])[:-1] + b',["sequence",['
        self.digest = sha256(prefix)
        self._started = False

    def append(self, values: pa.Array) -> None:
        if not len(values):
            return
        if values.null_count:
            raise ValueError("canonical population emitted an unencoded item")
        if self._started:
            self.digest.update(b",")
        offsets = pa.array([0, len(values)], type=pa.int32())
        (joined,) = pc.call_function(
            "binary_join", [pa.ListArray.from_arrays(offsets, values), pa.scalar(",")]
        )
        self.digest.update(joined.as_buffer())
        self._started = True

    def key(self) -> str:
        self.digest.update(b"]]]")
        return f"{self.domain}:{self.digest.hexdigest()}"


def canonical_population(
    population: AcquiredPopulation,
    *,
    engine: AnalyticalConnection,
    batch_size: int | None = None,
) -> CanonicalPopulation:
    """Encode a partition in acquired item order and fold its declared field groups."""
    layout = population.layout
    projections = _projections(layout._shape, layout._field_groups)
    # Statement-scoped ordering key, distinct from any nominal field or business address.
    ordinal = "_ddo_population_ordinal"
    names = {name.lower() for name in layout.schema.names}
    while ordinal in names:
        ordinal += "_"
    table = population.table.append_column(
        ordinal, pa.array(range(population.table.num_rows), type=pa.int32())
    )
    selected_batch_size = configured().batch_size if batch_size is None else batch_size
    relation = (
        engine.from_arrow(table)
        .select(col(ordinal).alias(_ITEM_ORDINAL), *projections)
        .sort(col(_ITEM_ORDINAL).asc())
    )
    partition = _SequenceCommitment("partition")
    groups = {name: _SequenceCommitment("partition-group") for name, _ in layout._field_groups}
    item_batches = []
    with relation.to_arrow_reader(batch_size=selected_batch_size) as reader:
        for batch in reader:
            partition.append(batch.column(1))
            for index, commitment in enumerate(groups.values(), start=2):
                commitment.append(batch.column(index))
            item_batches.append(batch.select([0, 1]))
    items = (
        pa.Table.from_batches(item_batches).cast(_ITEM_SCHEMA)
        if item_batches
        else _ITEM_SCHEMA.empty_table()
    )
    return CanonicalPopulation(
        items,
        partition.key(),
        {name: commitment.key() for name, commitment in groups.items()},
    )

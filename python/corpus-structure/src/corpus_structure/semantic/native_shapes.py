"""Native JSON shape guards from the existing effective semantic definitions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from .types import PreparedRelease


def _record_shape_guards(
    prepared: PreparedRelease,
    class_name: str,
    expression: str,
    *,
    fields: Mapping[str, tuple[str, str]] | None = None,
    field_names: str | None = None,
    deferred_arrays: frozenset[str] = frozenset(),
) -> str:
    definitions = {definition.name: definition for definition in prepared.definitions}
    vocabularies = {
        v.enum: tuple(member.value for member in v.members) for v in prepared.vocabularies
    }

    def quoted(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    def present(expression: str, key: str, storage: str) -> str:
        return (
            f"{expression} ? {key}" if storage == "jsonb" else f"({expression}->{key}) IS NOT NULL"
        )

    def invalid_record(class_name: str, expression: str, *, root=False, storage="jsonb") -> str:
        definition = definitions[class_name]
        if definition.abstract:
            members = [
                d.name for d in definitions.values() if class_name in d.ancestors and not d.abstract
            ]
            if not members:
                raise ValueError(
                    f"abstract parsing boundary has no concrete variants: {class_name}"
                )
            return (
                "("
                + " AND ".join(
                    "(" + invalid_record(name, expression, storage=storage) + ")"
                    for name in members
                )
                + ")"
            )
        allowed_fields = ",".join(quoted(prop.name) for prop in definition.properties)
        invalid = [
            (
                f"EXISTS(SELECT FROM unnest({field_names}) key "
                if root and field_names
                else f"EXISTS(SELECT FROM {storage}_object_keys({expression}) key "
            )
            + f"WHERE key<>ALL(ARRAY[{allowed_fields}]))"
        ]
        for prop in definition.properties:
            key = quoted(prop.name)
            value, value_storage = (
                fields[prop.name]
                if root and fields and prop.name in fields
                else (f"{expression}->{key}", storage)
            )
            has_field = (
                f"{key}=ANY({field_names})"
                if root and field_names
                else present(expression, key, storage)
            )
            scalar = (
                f"({value})#>>'{{}}'"
                if root and fields and prop.name in fields
                else f"{expression}->>{key}"
            )
            if prop.required:
                invalid.append(f"NOT ({has_field})")
            if prop.multivalued:
                predicate = f"{value_storage}_typeof({value}) IS DISTINCT FROM 'array'"
                if (
                    prop.range
                    in {"ParsingString", "PdfString", "PdfDigest", "PdfPointer", "string"}
                    or prop.range in vocabularies
                ):
                    predicate += (
                        f" OR EXISTS(SELECT FROM {value_storage}_array_elements({value}) element "
                        f"WHERE {value_storage}_typeof(element) IS DISTINCT FROM 'string')"
                    )
                if prop.range in definitions and not (root and prop.name in deferred_arrays):
                    predicate += (
                        f" OR EXISTS(SELECT FROM {value_storage}_array_elements({value}) "
                        "nested_record "
                        f"WHERE {value_storage}_typeof(nested_record) "
                        "IS DISTINCT FROM 'object' OR ("
                        + invalid_record(prop.range, "nested_record", storage=value_storage)
                        + "))"
                    )
                if prop.minimum_cardinality is not None and prop.minimum_cardinality > 0:
                    predicate += (
                        f" OR {value_storage}_array_length({value}) < {prop.minimum_cardinality}"
                    )
                if prop.maximum_cardinality is not None:
                    predicate += (
                        f" OR {value_storage}_array_length({value}) > {prop.maximum_cardinality}"
                    )

            elif prop.range in {"ParsingBoolean", "PdfBoolean", "boolean"}:
                predicate = f"{value_storage}_typeof({value}) IS DISTINCT FROM 'boolean'"
            elif prop.range in {"ParsingInteger", "PdfInteger", "integer"}:
                predicate = (
                    f"{value_storage}_typeof({value}) IS DISTINCT FROM 'number' "
                    f"OR {scalar} !~ '^[0-9]+$'"
                )
            elif prop.range in {"PdfNumber", "float", "double", "decimal"}:
                predicate = f"{value_storage}_typeof({value}) IS DISTINCT FROM 'number'"
            elif (
                prop.range in {"ParsingString", "PdfString", "PdfDigest", "PdfPointer", "string"}
                or prop.range in vocabularies
            ):
                predicate = f"{value_storage}_typeof({value}) IS DISTINCT FROM 'string'"
                if prop.range in vocabularies:
                    choices = ",".join(quoted(member) for member in vocabularies[prop.range])
                    predicate += f" OR {scalar} NOT IN ({choices})"
            elif prop.range in definitions:
                predicate = (
                    f"{value_storage}_typeof({value}) IS DISTINCT FROM 'object' OR ("
                    + invalid_record(prop.range, value, storage=value_storage)
                    + ")"
                )
            else:
                raise ValueError(
                    f"unsupported required parsing native shape: {class_name}/{prop.name}"
                )
            invalid.append(f"({has_field} AND ({predicate}))")
            if prop.equals_string is not None:
                invalid.append(f"{scalar} IS DISTINCT FROM {quoted(prop.equals_string)}")
            for pattern in prop.patterns or ((prop.pattern,) if prop.pattern else ()):
                if prop.multivalued:
                    invalid.append(
                        f"({has_field} AND EXISTS(SELECT FROM "
                        f"{value_storage}_array_elements_text({value}) element "
                        f"WHERE element !~ {quoted(pattern)}))"
                    )
                else:
                    invalid.append(f"({has_field} AND {scalar} !~ {quoted(pattern)})")
            if prop.minimum is not None:
                invalid.append(f"({has_field} AND ({scalar})::numeric < {prop.minimum})")
            if prop.maximum is not None:
                invalid.append(f"({has_field} AND ({scalar})::numeric > {prop.maximum})")
        return " OR ".join(invalid)

    def guards(class_name: str, expression: str) -> str:
        return (
            f"IF jsonb_typeof({expression}) IS DISTINCT FROM 'object' THEN "
            f"RAISE EXCEPTION 'parsing record must be an object: {class_name}' "
            "USING ERRCODE='23514'; END IF;\n"
            f"IF {invalid_record(class_name, expression, root=True)} THEN "
            f"RAISE EXCEPTION 'parsing record shape differs: {class_name}' "
            "USING ERRCODE='23514'; END IF;\n"
        )

    return guards(class_name, expression)


def record_shape_guards(prepared: PreparedRelease, class_name: str, expression: str) -> str:
    return _record_shape_guards(prepared, class_name, expression)


@dataclass(frozen=True)
class DecomposedRecordGuards:
    envelope: str
    rows: Mapping[str, str]


def decomposed_record_guards(
    prepared: PreparedRelease,
    class_name: str,
    expression: str,
    *,
    field_names: str,
    collections: Mapping[str, tuple[str, str]],
    records: Mapping[str, str],
) -> DecomposedRecordGuards:
    """One model supplies closed envelope/cardinalities AND each normalized row guard.

    Collection values are cached JSON text; the owning SQL loops cast one record
    at a time. Returning all row guards together prevents a transport-only shape
    check from being mistaken for complete protected publication validation.
    """
    definition = next(d for d in prepared.definitions if d.name == class_name)
    properties = {p.name: p for p in definition.properties}
    classes = {d.name for d in prepared.definitions}
    fields = {name: (array, "json") for name, (array, _) in collections.items()}
    fields.update({name: (value, "jsonb") for name, value in records.items()})
    rows = {}
    for name, (_, record) in collections.items():
        prop = properties[name]
        if not prop.multivalued or prop.range not in classes:
            raise ValueError(f"decomposed record collection has no modeled record range: {name}")
        rows[name] = record_shape_guards(prepared, prop.range, record)
    if any(
        p.multivalued and p.range in classes and p.name not in collections
        for p in definition.properties
    ):
        raise ValueError("every top-level record collection needs a complete row guard binding")
    return DecomposedRecordGuards(
        _record_shape_guards(
            prepared,
            class_name,
            expression,
            fields=fields,
            field_names=field_names,
            deferred_arrays=frozenset(collections),
        ),
        rows,
    )

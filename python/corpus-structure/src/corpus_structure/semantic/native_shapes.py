"""Native JSON shape guards from the existing effective semantic definitions."""
from __future__ import annotations

from .types import PreparedRelease

def record_shape_guards(prepared: PreparedRelease, class_name: str, expression: str) -> str:
    definitions = {definition.name: definition for definition in prepared.definitions}
    vocabularies = {
        v.enum: tuple(member.value for member in v.members) for v in prepared.vocabularies
    }

    def quoted(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    def invalid_record(class_name: str, expression: str) -> str:
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
                + " AND ".join("(" + invalid_record(name, expression) + ")" for name in members)
                + ")"
            )
        fields = ",".join(quoted(prop.name) for prop in definition.properties)
        invalid = [
            f"EXISTS(SELECT FROM jsonb_object_keys({expression}) key "
            f"WHERE key<>ALL(ARRAY[{fields}]))"
        ]
        for prop in definition.properties:
            key = quoted(prop.name)
            value = f"{expression}->{key}"
            if prop.required:
                invalid.append(f"NOT ({expression} ? {key})")
            if prop.multivalued:
                predicate = f"jsonb_typeof({value}) IS DISTINCT FROM 'array'"
                if prop.range in {"ParsingString", "PdfString", "PdfDigest", "PdfPointer", "string"} or prop.range in vocabularies:
                    predicate += (
                        f" OR EXISTS(SELECT FROM jsonb_array_elements({value}) element "
                        "WHERE jsonb_typeof(element) IS DISTINCT FROM 'string')"
                    )
                if prop.range in definitions:
                    predicate += (
                        f" OR EXISTS(SELECT FROM jsonb_array_elements({value}) nested_record "
                        "WHERE jsonb_typeof(nested_record) IS DISTINCT FROM 'object' OR ("
                        + invalid_record(prop.range, "nested_record")
                        + "))"
                    )
                if prop.minimum_cardinality is not None and prop.minimum_cardinality > 0:
                    predicate += f" OR jsonb_array_length({value}) < {prop.minimum_cardinality}"
                if prop.maximum_cardinality is not None:
                    predicate += f" OR jsonb_array_length({value}) > {prop.maximum_cardinality}"

            elif prop.range in {"ParsingBoolean", "boolean"}:
                predicate = f"jsonb_typeof({value}) IS DISTINCT FROM 'boolean'"
            elif prop.range in {"ParsingInteger", "PdfInteger", "integer"}:
                predicate = (
                    f"jsonb_typeof({value}) IS DISTINCT FROM 'number' "
                    f"OR {expression}->>{key} !~ '^[0-9]+$'"
                )
            elif prop.range in {"PdfNumber", "float", "double", "decimal"}:
                predicate = f"jsonb_typeof({value}) IS DISTINCT FROM 'number'"
            elif prop.range in {"ParsingString", "PdfString", "PdfDigest", "PdfPointer", "string"} or prop.range in vocabularies:
                predicate = f"jsonb_typeof({value}) IS DISTINCT FROM 'string'"
                if prop.range in vocabularies:
                    choices = ",".join(quoted(member) for member in vocabularies[prop.range])
                    predicate += f" OR {expression}->>{key} NOT IN ({choices})"
            elif prop.range in definitions:
                predicate = (
                    f"jsonb_typeof({value}) IS DISTINCT FROM 'object' OR ("
                    + invalid_record(prop.range, value)
                    + ")"
                )
            else:
                raise ValueError(
                    f"unsupported required parsing native shape: {class_name}/{prop.name}"
                )
            invalid.append(f"({expression} ? {key} AND ({predicate}))")
            if prop.equals_string is not None:
                invalid.append(
                    f"{expression}->>{key} IS DISTINCT FROM {quoted(prop.equals_string)}"
                )
            for pattern in prop.patterns or ((prop.pattern,) if prop.pattern else ()):
                invalid.append(f"({expression} ? {key} AND {expression}->>{key} !~ {quoted(pattern)})")
            if prop.minimum is not None:
                invalid.append(
                    f"({expression} ? {key} AND ({expression}->>{key})::numeric < {prop.minimum})"
                )
            if prop.maximum is not None:
                invalid.append(
                    f"({expression} ? {key} AND ({expression}->>{key})::numeric > {prop.maximum})"
                )
        return " OR ".join(invalid)

    def guards(class_name: str, expression: str) -> str:
        return (
            f"IF jsonb_typeof({expression}) IS DISTINCT FROM 'object' THEN "
            f"RAISE EXCEPTION 'parsing record must be an object: {class_name}' "
            "USING ERRCODE='23514'; END IF;\n"
            f"IF {invalid_record(class_name, expression)} THEN "
            f"RAISE EXCEPTION 'parsing record shape differs: {class_name}' "
            "USING ERRCODE='23514'; END IF;\n"
        )

    return guards(class_name, expression)

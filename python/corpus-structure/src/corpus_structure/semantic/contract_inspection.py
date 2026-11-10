"""Bounded observations of one immutable release, shared by operator transports."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict
from hashlib import sha256
from typing import Any, Literal, cast

from pydantic import BaseModel, ValidationError

from .identity import canonical_bytes
from .refusals import InvalidContinuation, SemanticRefusal
from .types import PreparedRelease

MAX_REPORT_BYTES = 1024 * 1024


def inspect_contract(
    prepared: PreparedRelease,
    subject_kind: Literal["class", "property", "operation"],
    subject_id: str,
    *,
    property: str | None = None,
    view: Literal["summary", "detail"] = "summary",
    after: str | None = None,
    limit: int = 20,
    input_json: str | bytes | None = None,
    validation_purpose: Literal["structural", "accepted"] | None = None,
    correction_detail: bool = False,
    raw_evidence: bool = False,
    max_errors: int = 100,
    max_depth: int = 8,
    max_bytes: int = 262144,
) -> BaseModel:
    """Inspect effective products; successful input validation grants no effect authority.

    JSON-valued descriptive declarations and boundary fragments use explicitly named
    ``*_json`` fields to preserve arbitrary authored shape and exact scalar encodings.
    Continuations page the same immutable selection and do not resubmit input validation.
    """
    from .inspection_metadata import get_inspection
    from .operation_reporting import (
        _report,
        explain_operation,
        validation_failure_report,
        validation_report,
    )

    if subject_kind not in {"class", "property", "operation"} or view not in {"summary", "detail"}:
        raise SemanticRefusal("inspect_contract/request: unsupported subject kind or view")
    if isinstance(limit, bool) or not 1 <= limit <= 100:
        raise SemanticRefusal("inspect_contract/limit: expected 1 through 100")
    if (subject_kind == "property") != (property is not None):
        raise SemanticRefusal(
            "inspect_contract/property: property subjects require their owning class and property"
        )
    if (input_json is None) != (validation_purpose is None):
        raise SemanticRefusal(
            "inspect_contract/input: supply input and explicit validation purpose together"
        )
    if validation_purpose not in {None, "structural", "accepted"}:
        raise SemanticRefusal("inspect_contract/validation_purpose: unsupported purpose")
    if after is not None and input_json is not None:
        raise SemanticRefusal(
            "inspect_contract/input: continuation pages do not resubmit validation"
        )
    input_bytes = input_json.encode() if isinstance(input_json, str) else input_json
    if input_bytes is not None and (
        subject_kind == "operation" or len(input_bytes) > MAX_REPORT_BYTES
    ):
        raise SemanticRefusal("inspect_contract/input: expected bounded class input")
    metadata = get_inspection(prepared)
    entries: list[dict[str, Any]] = []
    skeleton = None
    placeholders = []
    explanation = None
    validated = None
    input_digest = None
    if subject_kind == "operation":
        # The operation owner resolves IDs and owns all preconditions/effect explanations.
        explanation = explain_operation(prepared, subject_id).model_dump(mode="json")
        entries = [dict(category="operation", name=subject_id)]
        if view == "detail":
            entries.extend(_correspondences(prepared, operation_id=subject_id))
    else:
        definition = prepared.index.definitions.get(subject_id) or prepared.index.by_iri.get(
            subject_id
        )
        if definition is None:
            raise SemanticRefusal(f"inspect_contract/subject: missing class {subject_id!r}")
        subject_id = definition.name
        if property is not None and property not in prepared.index.properties_by_class[subject_id]:
            raise SemanticRefusal(
                f"inspect_contract/subject/{subject_id}: missing property {property!r}"
            )
        schema = cast(dict[str, Any], prepared.json_schema(subject_id, mode="validation"))
        if "$ref" in schema:
            reference = schema["$ref"]
            if reference.startswith("#/$defs/"):
                schema = schema["$defs"][
                    reference.removeprefix("#/$defs/").replace("~1", "/").replace("~0", "~")
                ]
        # Pydantic aliases and required-presence come from its actual released boundary.
        recipe = next(a for a in prepared.artifacts if a.kind == "boundary_recipe.json")
        aliases = json.loads(recipe.content)["aliases"].get(subject_id, {})
        class_meta = metadata.get("classes", {}).get(subject_id, {})
        if subject_kind == "class":
            entries.append(
                dict(
                    category="class",
                    name=subject_id,
                    iri=definition.iri,
                    metadata_json=canonical_bytes(
                        _jsonable(class_meta.get("metadata", {}))
                    ).decode()
                    if view == "detail"
                    else None,
                    contributors=_contributors(class_meta) if view == "detail" else [],
                )
            )
        for prop in definition.properties:
            if property is not None and property != prop.name:
                continue
            selected = class_meta.get("properties", {}).get(prop.name, {})
            alias = aliases.get(prop.name, prop.name)
            fragment = schema.get("properties", {}).get(alias, {})
            entries.append(
                dict(
                    category="property",
                    name=prop.name,
                    iri=prop.iri,
                    range=prop.range,
                    required=alias in schema.get("required", []),
                    multivalued=prop.multivalued,
                    minimum_cardinality=prop.minimum_cardinality,
                    maximum_cardinality=prop.maximum_cardinality,
                    minimum=prop.minimum,
                    maximum=prop.maximum,
                    patterns=list(prop.patterns or ((prop.pattern,) if prop.pattern else ())),
                    constraint_scope=prop.constraint_scope,
                    alias=alias,
                    boundary_schema_json=canonical_bytes(fragment).decode(),
                    metadata_json=canonical_bytes(_jsonable(selected.get("metadata", {}))).decode()
                    if view == "detail"
                    else None,
                    contributors=_contributors(selected) if view == "detail" else [],
                    attribution="known contributors; precedence unresolved"
                    if view == "detail" and selected
                    else None,
                )
            )
        if view == "detail":
            vocab_names = {
                p.range for p in definition.properties if property is None or p.name == property
            }
            vocabulary_detail = prepared.vocabulary_metadata
            for vocabulary in prepared.vocabularies:
                if vocabulary.enum in vocab_names:
                    # Page membership separately from the field describing its range.
                    for member in vocabulary.members:
                        entries.append(
                            dict(
                                category="vocabulary_member",
                                name=f"{vocabulary.enum}/{member.value}",
                                metadata_json=canonical_bytes(
                                    _jsonable(
                                        dict(
                                            **asdict(member),
                                            detail_status=vocabulary_detail["status"],
                                            detail=next(
                                                (
                                                    row
                                                    for row in vocabulary_detail.get("enums", {})
                                                    .get(vocabulary.enum, {})
                                                    .get("members", ())
                                                    if row["value"] == member.value
                                                ),
                                                None,
                                            ),
                                            enum_provenance={
                                                "contributors": [
                                                    row
                                                    for row in metadata.get("enums", {})
                                                    .get(vocabulary.enum, {})
                                                    .get("contributors", ())
                                                    if row["path"]
                                                    in {
                                                        f"enums/{vocabulary.enum}",
                                                        f"enums/{vocabulary.enum}/permissible_values/{member.value}",
                                                    }
                                                ]
                                            },
                                            enum_provenance_status=metadata.get(
                                                "enum_detail_status", "unavailable"
                                            ),
                                        )
                                    )
                                ).decode(),
                            )
                        )
            if prepared.execution_model_id:
                from .contracts import bound_execution_model

                for operation in bound_execution_model(prepared).operations:
                    if subject_id in (*operation.inputs, *operation.results):
                        entries.append(
                            dict(
                                category="related_operation",
                                name=operation.id,
                                metadata_json=canonical_bytes(
                                    dict(inputs=operation.inputs, results=operation.results)
                                ).decode(),
                            )
                        )
            entries.extend(_correspondences(prepared, class_name=subject_id))
            # Keep unresolved required values outside the executable payload.
            skeleton = "{}"
            placeholders = [
                dict(
                    path="/" + aliases.get(p.name, p.name).replace("~", "~0").replace("/", "~1"),
                    range=p.range,
                    reason="required value unresolved; supply explicit input",
                )
                for p in definition.properties
                if aliases.get(p.name, p.name) in schema.get("required", [])
            ]
        if input_json is not None:
            assert validation_purpose is not None
            input_digest = sha256(
                input_json.encode() if isinstance(input_json, str) else input_json
            ).hexdigest()
            try:
                validator = (
                    prepared.validate_json
                    if validation_purpose == "structural"
                    else prepared.validate_accepted_json
                )
                validator(subject_id, input_json)
            except ValidationError as error:
                validated = validation_failure_report(
                    error,
                    prepared=prepared,
                    scope=validation_purpose,
                    detail=correction_detail,
                    raw_evidence=raw_evidence,
                    max_errors=max_errors,
                    max_depth=max_depth,
                    max_bytes=max_bytes,
                ).model_dump(mode="json")
            else:
                validated = validation_report((), prepared=prepared).model_dump(mode="json")
    binding = sha256(
        canonical_bytes(
            dict(
                version=1,
                release=prepared.release_id,
                artifacts=prepared.artifacts_sha256,
                kind=subject_kind,
                subject=subject_id,
                property=property,
                view=view,
                limit=limit,
            )
        )
    ).hexdigest()
    offset = 0
    if after is not None:
        prefix, separator, value = after.partition(".")
        if not separator or prefix != binding or not value.isascii() or not value.isdigit():
            raise InvalidContinuation("inspection continuation differs from selected contract")
        offset = int(value)
        if not 0 < offset < len(entries):
            raise InvalidContinuation("inspection continuation is outside selected contract")
    entries = [{"patterns": [], "contributors": [], **entry} for entry in entries]
    chosen = entries[offset : offset + limit]
    end = offset + len(chosen)
    report = _report(
        "ContractInspection",
        dict(
            release_id=prepared.release_id,
            artifacts_sha256=prepared.artifacts_sha256,
            subject_kind=subject_kind,
            subject_id=subject_id,
            property=property,
            view=view,
            detail_status=metadata["status"],
            detail_reason=metadata.get("reason"),
            inspection_artifact_digest=metadata.get("artifact_digest"),
            entries=chosen,
            total=len(entries),
            next_after=f"{binding}.{end}" if end < len(entries) else None,
            complete=end == len(entries),
            skeleton_json=skeleton if offset == 0 else None,
            placeholders=placeholders if offset == 0 else [],
            input_digest=input_digest,
            validation_purpose=validation_purpose,
            validation_report=validated,
            operation_explanation=explanation,
            support_statement=(
                "Released boundary support only; native admission and source support "
                "are separate obligations."
            ),
        ),
    )
    if len(canonical_bytes(report.model_dump(mode="json"))) > MAX_REPORT_BYTES:
        if len(chosen) > 1:
            # Narrow page work only; input validation is not repeated.
            data = report.model_dump(mode="json")
            while len(chosen) > 1:
                chosen.pop()
                end = offset + len(chosen)
                data.update(entries=chosen, next_after=f"{binding}.{end}", complete=False)
                report = _report(
                    "ContractInspection",
                    {
                        k: v
                        for k, v in data.items()
                        if k not in {"report_version", "report_schema_digest"}
                    },
                )
                if len(canonical_bytes(report.model_dump(mode="json"))) <= MAX_REPORT_BYTES:
                    return report
        from .query import ReadLimit

        raise ReadLimit(
            "inspection detail exceeds byte budget; select a property or smaller page",
            reason="oversized_item",
        )
    return report


def _contributors(record):
    return [
        dict(
            module=c["module"],
            path=c["path"],
            source_digest=c["source_digest"],
            role=c["role"],
            declaration_json=canonical_bytes(_jsonable(c.get("declaration", {}))).decode(),
        )
        for c in record.get("contributors", [])
    ]


def _jsonable(value):
    if isinstance(value, Mapping):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _correspondences(prepared, *, class_name=None, operation_id=None) -> list[dict[str, Any]]:
    if not prepared.execution_model_id:
        return []
    from .contracts import bound_execution_model

    result = []
    for operation in bound_execution_model(prepared).operations:
        if operation_id is not None and operation.id != operation_id:
            continue
        for call in operation.calls:
            relevant = class_name is None or call.result_class == class_name
            fields = [(field.name, field) for field in (*call.parameters, *call.result_fields)]
            fields.extend(
                (record.name + "/" + field.name, field)
                for record in call.records
                for field in record.fields
            )
            for field_path, field in fields:
                if (
                    not relevant
                    and field.semantic_type != class_name
                    and (field.resolved is None or field.resolved.model_class != class_name)
                ):
                    continue
                result.append(
                    dict(
                        category="physical_correspondence",
                        name=f"{operation.id}/{call.id}/{field_path}",
                        metadata_json=canonical_bytes(
                            dict(
                                operation=operation.id,
                                call=call.id,
                                semantic_class=field.resolved.model_class
                                if field.resolved
                                else None,
                                semantic_type=field.semantic_type,
                                result_class=call.result_class,
                                source_reference=field.source,
                                native_type=field.native_type,
                                physical_kind=field.resolved.kind if field.resolved else None,
                                nullable=field.nullable,
                                multivalued=field.multivalued,
                                standing=(
                                    "released correspondence; semantic class and "
                                    "physical kind remain distinct"
                                ),
                            )
                        ).decode(),
                    )
                )
    return result

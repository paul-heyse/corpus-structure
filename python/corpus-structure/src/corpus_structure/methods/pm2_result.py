"""Retain bounded native model observations through the existing private result contract."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.semantic.contributions import (
    contribution_identity,
    occurrence_identity,
    operation_identity,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import declared_families
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    SourceSlice,
    evidence_anchor,
    record_source_pin,
)

from .pm2_products import PARSER_QUESTIONS, ParserProducts
from .pm2_source import (
    D1SourceField,
    MappedSource,
    PM2SourceMap,
    PM2TokenMap,
    ProviderSpan,
    SourceMapRefused,
    map_d1,
    map_dipo,
    map_hanlp,
    map_maverick,
)

if TYPE_CHECKING:
    from corpus_structure.semantic.types import PreparedRelease


def _parser_products(provider, mapping, request, reply, prepared) -> ParserProducts:
    if provider == "maverick" and isinstance(mapping, PM2TokenMap):
        from .pm2_maverick_products import maverick_products

        return maverick_products(mapping, request, reply)
    if provider == "hanlp" and isinstance(mapping, PM2TokenMap):
        from .pm2_hanlp_products import hanlp_products

        return hanlp_products(mapping, request, reply)
    if provider == "dipo" and isinstance(mapping, PM2SourceMap):
        from .pm2_dipo_products import dipo_products

        return dipo_products(mapping, request, reply, prepared=prepared)
    raise ValueError("parser operation differs from its qualified provider map")


def d1_evidence(
    mapping: PM2SourceMap,
    reply: Mapping[str, Any],
    *,
    field: D1SourceField | None,
    source_path: str | None,
    native: bool = False,
) -> dict[str, MappedSource | SourceMapRefused]:
    """Map each located answer independently. An unreturned pointer supplies no evidence."""
    if (field.path if field is not None else None) != source_path:
        raise ValueError("d1 rendered field differs from the authorized source path")
    rendered = mapping.provider_text if field is None else field.rendered_state
    if reply.get("outcome") == "succeeded" and rendered != reply.get("rendered_state"):
        raise ValueError("d1 returned a different rendered state")
    located: dict[str, MappedSource | SourceMapRefused] = {}
    for key, answer in reply.get("native", {}).get("answers", {}).items():
        if answer.get("span") is None:
            continue
        try:
            start, end = answer["span"]
            located[key] = map_d1(
                mapping,
                ProviderSpan(start, end, answer["text"]),
                scope_digest=mapping.scope_digest,
                field=field,
                path=answer.get("path"),
                native=native,
            )
        except SourceMapRefused as exc:
            located[key] = exc
    return located


def _native_evidence(
    mapping: PM2SourceMap | PM2TokenMap,
    provider: str,
    request: Mapping[str, Any],
    reply: Mapping[str, Any],
    field: D1SourceField | None,
    source_path: str | None,
) -> dict[str, MappedSource | SourceMapRefused]:
    if provider == "d1" and isinstance(mapping, PM2SourceMap):
        rendered = reply["rendered_state"]
        state = rendered if field is None else json.loads(rendered)
        if canonical_bytes(state) != canonical_bytes(request["state"]):
            raise ValueError("d1 rendered state differs from the admitted request")
        return d1_evidence(
            mapping,
            reply,
            field=field,
            source_path=source_path,
            native=request.get("interpretation", {}).get("version") == "2",
        )

    located: dict[str, MappedSource | SourceMapRefused] = {}
    if provider == "dipo" and isinstance(mapping, PM2SourceMap):
        text = mapping.provider_text
        if text != request["text"]:
            raise ValueError("Dipo request differs from its exact character map")
        for index, edu in enumerate(reply["edus"]):
            start, end = edu["chars"]
            literal = text[start:end]
            if " ".join(literal.split()) != edu["text"]:
                raise ValueError("Dipo EDU differs from the retained source text")
            try:
                located[str(index)] = map_dipo(
                    mapping, (ProviderSpan(start, end, literal),), scope_digest=mapping.scope_digest
                )
            except SourceMapRefused as exc:
                located[str(index)] = exc
        return located

    if not isinstance(mapping, PM2TokenMap) or provider not in {"hanlp", "maverick"}:
        raise ValueError("unsupported native profile and source map combination")
    sentences = [
        [token.text for token in mapping.sentence_tokens(index)]
        for index in sorted({token.sentence for token in mapping.tokens})
    ]
    if request["sentences"] != sentences:
        raise ValueError("native request differs from its exact token map")
    scope = mapping.mapping.scope_digest
    if provider == "maverick":
        if reply["tokens"] != [token.text for token in mapping.tokens]:
            raise ValueError("Maverick returned a different token population")
        for first, last in reply["mentions"]:
            key = f"{first}:{last}"
            try:
                located[key] = map_maverick(mapping, first, last, scope_digest=scope)
            except SourceMapRefused as exc:
                located[key] = exc
    else:
        native = reply["native"]
        if native["tok"] != sentences:
            raise ValueError("HanLP returned a different token population")
        (dependency_head,) = (key for key in native if key.split("/")[0] == "dep")
        for sentence, arcs in enumerate(native[dependency_head]):
            (root,) = (index for index, arc in enumerate(arcs) if arc[0] == 0)
            key = f"{sentence}:root"
            try:
                located[key] = map_hanlp(mapping, sentence, ((root, root + 1),), scope_digest=scope)
            except SourceMapRefused as exc:
                located[key] = exc
    return located


def pm2_input_digest(
    mapping: PM2SourceMap | PM2TokenMap,
    profile: Mapping[str, Any],
    request: Mapping[str, Any],
    *,
    question: str,
    operation_version: str,
    source_path: str | None = None,
) -> str:
    """Pass this effective input identity to existing task admission and reuse."""
    return sha256(
        canonical_bytes(
            {
                "source_map": mapping.input_digest,
                "profile": dict(profile),
                "source_path": source_path,
                "operation": [question, operation_version],
                "request": json.dumps(
                    dict(request), ensure_ascii=False, allow_nan=False, separators=(",", ":")
                ),
            }
        )
    ).hexdigest()


def pm2_unit_result(
    ref: UnitRef,
    mapping: PM2SourceMap | PM2TokenMap,
    *,
    profile: Mapping[str, Any],
    request: Mapping[str, Any],
    reply: dict[str, Any],
    question: str,
    operation_version: str,
    input_digest: str,
    source_path: str | None = None,
    field: D1SourceField | None = None,
    prepared: PreparedRelease | None = None,
) -> UnitResult:
    """Bind the native reply, exact selected evidence, and eligible physical locations.

    A projected spelling that differs from the native field survives in the report.
    Only source-owner-confirmed native pieces enter the physical occurrence inventory.
    """
    outcome = reply["outcome"]
    if outcome not in {"succeeded", "empty", "limited", "failed"}:
        raise ValueError("unexpected native result outcome")
    if input_digest != pm2_input_digest(
        mapping,
        profile,
        request,
        question=question,
        operation_version=operation_version,
        source_path=source_path,
    ):
        raise ValueError("admitted task input differs from the effective PM2 input")
    operation_key = operation_identity(question, operation_version, ref.unit_key, input_digest)
    source_map = mapping.mapping if isinstance(mapping, PM2TokenMap) else mapping
    pin = record_source_pin(source_map.context.primary)
    if (ref.unit_type, ref.unit_id, ref.unit_key) != (
        TaskUnitType.SOURCE_VIEW,
        pin["source_view_id"],
        pin["source"],
    ):
        raise ValueError("admitted task unit differs from the PM2 source view")
    provider = str(profile["provider"])
    parser_operation = question in PARSER_QUESTIONS.values()
    if parser_operation and question != PARSER_QUESTIONS.get(provider):
        raise ValueError("parser question differs from the admitted provider")
    products = ()
    evidence = {}
    if outcome == "succeeded":
        if parser_operation:
            parsed = _parser_products(provider, mapping, request, reply, prepared)
            evidence, products = parsed.locations, parsed.products
        else:
            evidence = _native_evidence(mapping, provider, request, reply, field, source_path)
            if provider == "d1" and "interpretation" in request:
                from .pm2_interpretation_products import interpretation_products

                family = (
                    None
                    if prepared is None
                    else declared_families(prepared.registry_rows).get(question)
                )
                if family is None:
                    raise ValueError("interpretation question is not in the selected release")
                if request["interpretation"].get("version", family.version) != operation_version:
                    raise ValueError("interpretation rendering differs from the admitted version")
                assessed = request["interpretation"]["assessed_scope"]
                (scope,) = source_map.context.pieces
                if (
                    not isinstance(scope, SourceSlice)
                    or assessed["pin"] != pin
                    or assessed["scope_digest"] != source_map.scope_digest
                    or assessed["projection_extent"] != [scope.start, scope.end]
                ):
                    raise ValueError("interpretation scope differs from the authenticated source")
                products = interpretation_products(family, dict(request), reply, evidence)
    rows, coordinates, locations = [], [], {}
    for name, result in evidence.items():
        if result.scope_digest != source_map.scope_digest:
            raise ValueError("mapped model result belongs to another source scope")
        if isinstance(result, SourceMapRefused):
            locations[name] = {
                "outcome": "unsupported",
                "reason": str(result.reason),
                "detail": str(result),
            }
            continue
        if (
            result.source_map_digest != source_map.input_digest
            or result.provider_path != source_path
            or (isinstance(mapping, PM2TokenMap) and result.input_digest != mapping.input_digest)
        ):
            raise ValueError("mapped model result belongs to another provider input")
        location = {
            "selected_projection": list(result.anchors),
            "provider_map_digest": result.input_digest,
        }
        locations[name] = location
        try:
            native = [
                evidence_anchor(source_map.context, piece, native=True) for piece in result.pieces
            ]
        except ContextRefused as exc:
            location.update(
                outcome="unsupported", reason="native_occurrence_unavailable", detail=str(exc)
            )
            continue
        anchors, texts = zip(*native, strict=True)
        coordinates.extend(texts)
        row = {
            "contract": "RetainedContributionSemantics",
            "kind": "occurrence",
            "semantic_type": "source_occurrence",
            "operation_key": operation_key,
            "item_key": name,
            "pin": pin,
            "anchors": anchors,
            "occurrence_id": occurrence_identity(anchors),
            "disposition": "unassessed",
            "standing": "retained_private",
            "score_state": "missing",
        }
        row["contribution_id"] = contribution_identity(row)
        rows.append(row)
        location.update(outcome="succeeded", occurrence_id=row["occurrence_id"])
    retained = {row["item_key"]: row["contribution_id"] for row in rows}
    defined_keys = set(evidence)
    for product in products:
        if product.key in defined_keys or not set(product.members) <= defined_keys:
            raise ValueError("parser product has a duplicate key or an unavailable member")
        defined_keys.add(product.key)
        members = tuple(retained[key] for key in product.members if key in retained)
        row = {
            "contract": "RetainedContributionSemantics",
            "kind": "composite" if members else "proposal",
            "semantic_type": product.semantic_type,
            "operation_key": operation_key,
            "item_key": product.key,
            "pin": pin,
            "members": members,
            "anchors": (),
            "disposition": "unassessed",
            "standing": "retained_private",
            "score_state": "missing",
            "value": source_value(
                {
                    **product.value,
                    "location_keys": list(product.members),
                    "unlocated_members": [key for key in product.members if key not in retained],
                }
            ),
            "computation_dependencies": (input_digest,),
        }
        row["contribution_id"] = contribution_identity(row)
        retained[product.key] = row["contribution_id"]
        rows.append(row)
    report: dict[str, Any] = {
        "native": reply,
        "locations": locations,
        "scope_digest": source_map.scope_digest,
        "input_digest": input_digest,
        "source_map_digest": source_map.input_digest,
        "authorized_source_path": source_path,
        "source_map": {
            "context_pieces": [asdict(piece) for piece in source_map.context.pieces],
            "segments": [asdict(segment) for segment in source_map.segments],
            "protected_atoms": source_map.protected_atoms,
            "tokens": [asdict(token) for token in mapping.tokens]
            if isinstance(mapping, PM2TokenMap)
            else [],
        },
        "effective_profile_digest": sha256(canonical_bytes(dict(profile))).hexdigest(),
        "request": dict(request),
    }
    operation = {
        "operation_key": operation_key,
        "question": question,
        "operation_version": operation_version,
        "outcome": outcome,
        "inspected_count": 0 if outcome in {"limited", "failed"} else 1,
        "emitted_count": len(rows),
        "report_digest": sha256(canonical_bytes(report)).hexdigest(),
        "computation_dependencies": (input_digest,),
    }
    if outcome in {"limited", "failed"}:
        operation["reason"] = reply["reason"]
    unit_outcome = ObservationOutcome.PRODUCED if rows else ObservationOutcome.EMPTY
    if outcome == "failed":
        unit_outcome = ObservationOutcome.FAILED
    return UnitResult(
        ref=ref,
        outcome=unit_outcome,
        error=reply["reason"] if outcome == "failed" else None,
        parse_detail={"pm2_native": report},
        contribution_operations=(operation,),
        contributions=tuple(rows),
        contribution_coordinate_texts=tuple(coordinates),
    )

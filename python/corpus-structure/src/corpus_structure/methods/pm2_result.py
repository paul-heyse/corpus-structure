"""Map native observations into declared source contributions and exact locations."""

from __future__ import annotations

import json
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

from corpus_structure.semantic.contributions import (
    contribution_identity,
    contribution_payload_contracts,
    occurrence_identity,
    validate_contribution_semantics,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    evidence_anchor,
    record_source_pin,
)

from .pm2_products import (
    ParserProducts,
    parser_member_types,
    parser_value_for_contract,
    parser_view,
)
from .pm2_source import (
    D1SourceField,
    MappedSource,
    PM2SourceMap,
    PM2TokenMap,
    ProviderSpan,
    SourceMapRefused,
    map_d1,
)

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
    if reply.get("outcome") in ("succeeded", "empty") and rendered != reply.get("rendered_state"):
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


def pm2_contribution_values(
    mapping,
    evidence,
    products,
    *,
    prepared,
    provider,
    input_digest,
    operation_key,
    question,
    source_path=None,
    parser_operation=True,
):
    """Project declared source occurrences and products with ordered member semantics."""
    source_map = mapping.mapping if isinstance(mapping, PM2TokenMap) else mapping
    pin = record_source_pin(source_map.context.primary)
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
    member_types = dict.fromkeys(evidence, "source_occurrence")
    contracts = (
        contribution_payload_contracts(prepared.index.definitions.values())
        if prepared is not None and parser_operation
        else {}
    )
    for product in products:
        if product.key in defined_keys or not set(product.members) <= defined_keys:
            raise ValueError("parser product has a duplicate key or an unavailable member")
        defined_keys.add(product.key)
        members = tuple(retained[key] for key in product.members if key in retained)
        payload_contract = contracts.get(product.semantic_type)
        value = (
            parser_value_for_contract(product.semantic_type, product.value)
            if payload_contract is not None
            else product.value
        )
        row = {
            "contract": payload_contract or "RetainedContributionSemantics",
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
                    **value,
                    "location_keys": list(product.members),
                    "unlocated_members": [key for key in product.members if key not in retained],
                }
            ),
            "computation_dependencies": (input_digest,),
        }
        if payload_contract is not None and prepared is not None:
            validate_contribution_semantics(
                prepared, row, question=question, payload_contracts=contracts
            )
            references = parser_member_types(parser_view(row))
            if tuple(references) != product.members or any(
                member_types.get(key) != kind for key, kind in references.items()
            ):
                raise ValueError("released parser roles differ from their exact source members")
        row["contribution_id"] = contribution_identity(row)
        retained[product.key] = row["contribution_id"]
        member_types[product.key] = product.semantic_type
        rows.append(row)
    return tuple(rows), tuple(coordinates), locations

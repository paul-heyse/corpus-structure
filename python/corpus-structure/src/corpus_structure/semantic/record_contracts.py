"""Released private source records and field evidence, before native publication.

LinkML owns family roles and scalar shapes. This operation owns their cross-object
relationships and occurrence identity. Coordinates are checked against explicit pinned
inputs; authenticating those pins against persisted custody remains native admission.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from graphlib import CycleError, TopologicalSorter
from hashlib import sha256
from typing import Any

from pydantic import BaseModel

from .identity import canonical_bytes
from .types import ClassDefinition, Diagnostic, PreparationError, PreparedRelease


def record_product_classes(definitions: tuple[ClassDefinition, ...]) -> frozenset[str]:
    """Released private product placement, shared by graph lowering and admission."""
    return frozenset(
        definition.name
        for definition in definitions
        if definition.name == "SourceRecordProduct" or "SourceRecordProduct" in definition.ancestors
    )


def validate_record_declarations(definitions: tuple[ClassDefinition, ...]) -> None:
    """Refuse unsupported family semantics before generating or archiving a release."""
    classes = {definition.name: definition for definition in definitions}
    products = record_product_classes(definitions)
    for definition in definitions:
        if definition.name in products:
            continue
        for prop in definition.properties:
            if prop.range in products:
                raise PreparationError(
                    (
                        Diagnostic(
                            "record_product_placement",
                            definition.name + "/" + prop.name,
                            "knowledge graph property cannot range into a private record product",
                            "unsupported",
                        ),
                    )
                )
    families = set()
    for definition in definitions:
        if "SemanticRecordFields" not in definition.ancestors:
            continue
        properties = {prop.name: prop for prop in definition.properties}
        family = properties.get("family")
        recipe = properties.get("occurrence_recipe")
        reason = None
        if family is None or not family.equals_string or family.equals_string in families:
            reason = "record families require one unique nonempty released family identifier"
        elif recipe is None or recipe.equals_string != "source-anchor-membership-1":
            reason = "unsupported released record occurrence recipe"
        else:
            families.add(family.equals_string)
            roles = tuple(
                prop
                for prop in definition.properties
                if prop.name not in {"family", "occurrence_recipe"}
            )
            if not roles:
                reason = "released record family requires explicit field roles"
            elif any(
                not prop.required
                or prop.multivalued
                or not prop.inlined
                or prop.constraint_scope != "shape"
                or prop.range not in classes
                or (
                    prop.range != "RecordField"
                    and "RecordField" not in classes[prop.range].ancestors
                )
                for prop in roles
            ):
                reason = (
                    "record roles require scalar inlined RecordField ranges and explicit states"
                )
        if reason is not None:
            raise PreparationError(
                (
                    Diagnostic(
                        "record_contract",
                        definition.name,
                        reason,
                        "unsupported",
                    ),
                )
            )


def _identity(kind: str, value: Any) -> str:
    return kind + ":" + sha256(canonical_bytes(value)).hexdigest()


def _pin(pin: Mapping[str, Any]) -> dict[str, Any]:
    # Native sequence IDs locate custody; source/product/projection determine meaning.
    return {key: value for key, value in pin.items() if key != "source_view_id"}


def anchor_identity(anchor: Mapping[str, Any]) -> str:
    return _identity(
        "record-anchor",
        {
            **{key: value for key, value in anchor.items() if key != "anchor_id"},
            "pin": _pin(anchor["pin"]),
        },
    )


def evidence_set_identity(evidence: Mapping[str, Any]) -> str:
    members = tuple(evidence["anchors"])
    return _identity(
        "record-set",
        [
            evidence["role"],
            evidence["ordering"],
            evidence["usage"],
            tuple(sorted(members)) if evidence["ordering"] == "unordered" else members,
        ],
    )


def record_identity(release_id: str, record: Mapping[str, Any]) -> str:
    return _identity(
        "record",
        [
            release_id,
            record["family"],
            record["occurrence_recipe"],
            _pin(record["pin"]),
            tuple(sorted(record["occurrence_anchors"])),
        ],
    )


def interpretation_identity(record: Mapping[str, Any]) -> str:
    return _identity(
        "record-interpretation",
        [
            record["record_id"],
            record["contract"],
            record["policy_version"],
            sorted(record["fields"], key=lambda field: field["role"]),
            sorted(record.get("evidence_sets", ()), key=lambda evidence: evidence["set_id"]),
            sorted(record.get("computation_dependencies", ())),
            sorted(record.get("assertion_members", ())),
        ],
    )


def _unique(rows, key: str, meaning: str):
    result = {row[key]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"duplicate {meaning}")
    return result


def _text_key(pin, space, pointer):
    return canonical_bytes([_pin(pin), space, pointer])


def bind_record_candidates(
    prepared: PreparedRelease,
    *,
    source: str,
    records: Sequence[Mapping[str, Any]],
    coordinate_texts: Sequence[Mapping[str, Any]] = (),
) -> tuple[BaseModel, ...]:
    """Validate typed candidates using the actual prepared family boundary.

    No missing role/state, evidence, classification cue or diagnostic is fabricated.
    A complete source-reading claim needs an independent producer's pinned coordinate
    input. This version supports one source/product/projection/recipe pin per record;
    typed related-source mappings are a later context contract. This pure check does
    not qualify provider inference or persisted publication.
    """
    contexts = {}
    for raw in coordinate_texts:
        row = prepared.validate_python("RecordCoordinateText", raw).model_dump(mode="python")
        key = _text_key(row["pin"], row["space"], row["pointer"])
        if key in contexts and contexts[key] != row["text"]:
            raise ValueError("conflicting pinned coordinate text")
        contexts[key] = row["text"]
    result = []
    seen = set()
    for raw in records:
        model = prepared.validate_python("SourceRecord", raw)
        row = model.model_dump(mode="python")
        if row["pin"]["source"] != source:
            raise ValueError("record source pin differs from producing source")
        definition = prepared.index.definitions.get(row["contract"])
        if definition is None or "SemanticRecordFields" not in definition.ancestors:
            raise ValueError("record contract is not a released family declaration")
        properties = {prop.name: prop for prop in definition.properties}
        for name in ("family", "occurrence_recipe"):
            if (
                properties[name].equals_string is None
                or properties[name].equals_string != row[name]
            ):
                raise ValueError("record family/occurrence recipe differs from released contract")
        if row["occurrence_recipe"] != "source-anchor-membership-1":
            raise ValueError("unsupported record occurrence recipe")
        fields = _unique(row["fields"], "role", "record role")
        if not row["policy_version"]:
            raise ValueError("record requires a nonempty acceptance policy version")
        prepared.validate_python(
            row["contract"],
            {"family": row["family"], "occurrence_recipe": row["occurrence_recipe"], **fields},
        )
        anchors = _unique(row["anchors"], "anchor_id", "record anchor")
        for identity, anchor in anchors.items():
            if anchor_identity(anchor) != identity:
                raise ValueError("record anchor identity differs from content")
            if anchor["pin"] != row["pin"]:
                raise ValueError("record anchor source pin differs from record")
            start, end = anchor.get("start"), anchor.get("end")
            if (start is None) != (end is None):
                raise ValueError("record anchor needs paired coordinate bounds")
            if anchor["space"] == "model_context":
                raise ValueError("model context is not source evidence")
            if anchor["precision"] == "exact":
                if start is None or not start < end:
                    raise ValueError("exact record anchor needs a nonempty source interval")
                key = _text_key(anchor["pin"], anchor["space"], anchor["pointer"])
                if key not in contexts:
                    raise ValueError("exact record anchor lacks pinned coordinate text")
                text = contexts[key]
                if end > len(text) or text[start:end] != anchor.get("source_piece"):
                    raise ValueError("record anchor does not reconstruct literal source text")
            elif start is not None:
                raise ValueError("coarse record anchor cannot claim exact coordinate bounds")
        occurrence = tuple(row["occurrence_anchors"])
        if len(set(occurrence)) != len(occurrence) or not set(occurrence) <= anchors.keys():
            raise ValueError("invalid record occurrence anchor membership")
        if record_identity(prepared.release_id, row) != row["record_id"]:
            raise ValueError("record occurrence identity differs from source membership")
        # Several coherent alternatives may share an occurrence; exact duplicates may not.
        identity = (row["record_id"], row["interpretation_id"])
        if identity in seen:
            raise ValueError("duplicate record interpretation")
        seen.add(identity)
        sets = _unique(row.get("evidence_sets", ()), "set_id", "record evidence set")
        for identity, evidence in sets.items():
            members = tuple(evidence["anchors"])
            if len(set(members)) != len(members) or not set(members) <= anchors.keys():
                raise ValueError("invalid evidence set anchor membership")
            if evidence["role"] not in fields or evidence_set_identity(evidence) != identity:
                raise ValueError("evidence set differs from released role or content")
        try:
            TopologicalSorter(
                {role: tuple(field.get("premises", ())) for role, field in fields.items()}
            ).prepare()
        except CycleError as error:
            raise ValueError("derived record field premises form a cycle") from error
        for role, field in fields.items():
            role_type = prepared.index.definitions[properties[role].range]
            meaning_changing = "MeaningChangingRecordField" in role_type.ancestors
            if field["meaning_changing"] != meaning_changing:
                raise ValueError("field meaning-changing standing differs from released role")
            used = tuple(field.get("evidence_sets", ()))
            if len(set(used)) != len(used) or not set(used) <= sets.keys():
                raise ValueError("invalid field evidence set membership")
            if any(sets[key]["role"] != role for key in used):
                raise ValueError("field evidence set belongs to another role")
            if (field["evidence_status"] == "available") != bool(used):
                raise ValueError("field evidence availability differs from actual sets")
            alternatives = field.get("alternatives", ())
            _unique(alternatives, "alternative_id", "field alternative")
            for alternative in alternatives:
                if not set(alternative.get("evidence_sets", ())) <= sets.keys():
                    raise ValueError("alternative evidence set is unavailable")
                if any(sets[key]["role"] != role for key in alternative.get("evidence_sets", ())):
                    raise ValueError("alternative evidence set belongs to another role")
            state = field["state"]
            if state != "present":
                if "value" in field or "original" in field or "original_pieces" in field:
                    raise ValueError("nonpresent field cannot claim an actual value")
                if not field.get("reason"):
                    raise ValueError("nonpresent field requires an explicit reason")
            else:
                if "value" not in field:
                    raise ValueError("present field requires a typed value")
                if field["evidence_status"] == "unavailable" and not field.get("reason"):
                    raise ValueError("present field with unavailable evidence requires a reason")
                pieces = tuple(anchors[anchor] for key in used for anchor in sets[key]["anchors"])
                kind, value = field["kind"], field["value"]
                if kind == "classified":
                    classification_kinds = {
                        prop.equals_string
                        for definition in prepared.definitions
                        if definition.name == "RecordClassification"
                        or "RecordClassification" in definition.ancestors
                        for prop in definition.properties
                        if prop.name == "kind"
                    }
                    if value["kind"] not in classification_kinds:
                        raise ValueError("classified field is not a literal extracted value")
                    if any(sets[key]["usage"] != "classification_cue" for key in used):
                        raise ValueError(
                            "classification association is not located source cue evidence"
                        )
                if kind == "native":
                    if value["kind"] != "native_location" or not any(
                        piece["space"] == "native" and piece["pointer"] == value["pointer"]
                        for piece in pieces
                    ):
                        raise ValueError("native field needs its actual native source pointer")
                    if any(sets[key]["usage"] != "native" for key in used):
                        raise ValueError("native field requires native evidence membership")
                if kind == "literal":
                    if any(sets[key]["usage"] != "literal" for key in used):
                        raise ValueError("literal field requires literal source evidence")
                    originals = field.get("original_pieces")
                    original = field.get("original")
                    if (original is None) == (originals is None):
                        raise ValueError(
                            "literal field requires one original spelling representation"
                        )
                    if value["kind"] == "text_sequence":
                        if originals is None or tuple(value["items"]) != tuple(originals):
                            raise ValueError("literal sequence differs from original source pieces")
                    elif (
                        value["kind"] not in {"text", "decimal"}
                        or value.get("text", value.get("lexical")) != original
                    ):
                        raise ValueError("literal value differs from original source spelling")
                    if row["standing"] == "accepted":
                        if not pieces or any(piece["precision"] != "exact" for piece in pieces):
                            raise ValueError("accepted literal field needs exact located evidence")
                        # Each set independently establishes the field. Distinct sets may
                        # share genuine source pieces; their union cannot invent repeats.
                        for key in used:
                            evidence = sets[key]
                            if len(evidence["anchors"]) > 1 and evidence["ordering"] != "ordered":
                                raise ValueError(
                                    "literal reconstruction requires an ordered evidence set"
                                )
                            previous_ends = {}
                            for anchor in evidence["anchors"]:
                                piece = anchors[anchor]
                                coordinate = _text_key(
                                    piece["pin"], piece["space"], piece["pointer"]
                                )
                                if piece["start"] < previous_ends.get(coordinate, 0):
                                    raise ValueError(
                                        "literal evidence intervals overlap or reverse source order"
                                    )
                                previous_ends[coordinate] = piece["end"]
                            reconstructed = tuple(
                                anchors[anchor]["source_piece"] for anchor in evidence["anchors"]
                            )
                            if originals is not None:
                                if tuple(originals) != reconstructed:
                                    raise ValueError(
                                        "literal sequence does not reconstruct field evidence"
                                    )
                            elif "".join(reconstructed) != original:
                                raise ValueError(
                                    "literal field does not reconstruct field evidence"
                                )
                if kind in {"normalized", "derived"}:
                    if not field.get("policy"):
                        raise ValueError("normalized/derived field requires its policy")
                    if kind == "normalized" and not field.get("original"):
                        raise ValueError("normalized field requires original spelling")
                    if kind == "derived" and (
                        not field.get("rule")
                        or not field.get("premises")
                        or not set(field["premises"]) <= fields.keys()
                        or role in field["premises"]
                        or any(
                            fields[premise]["state"] != "present" for premise in field["premises"]
                        )
                    ):
                        raise ValueError("derived field requires present premises and rule")
            required = "RequiredRecordField" in role_type.ancestors
            if row["standing"] == "accepted":
                if required and state != "present":
                    raise ValueError("accepted record is missing a required role")
                if state == "unresolved" and field["meaning_changing"]:
                    raise ValueError("accepted record has an unresolved meaning-changing role")
                if required and field["evidence_status"] != "available":
                    raise ValueError("accepted required role lacks located evidence")
                if any(
                    anchors[anchor]["precision"] == "unavailable"
                    for key in used
                    for anchor in sets[key]["anchors"]
                ):
                    raise ValueError("accepted field cannot use unavailable source locations")
        if interpretation_identity(row) != row["interpretation_id"]:
            raise ValueError("interpretation identity differs from fields or dependencies")
        result.append(model)
    return tuple(result)

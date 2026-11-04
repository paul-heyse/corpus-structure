"""Pure, release-derived assertions about source readings, never scientific claims.

The private record binder owns scalar/field validity. This adapter derives its ordinary
value subset before release hashing and retains direct sealed-record support separately.
Publication and whole-record admission remain the native/domain-policy owners.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import yaml
from linkml_runtime.dumpers import json_dumper
from pydantic import BaseModel

from .consolidation import SourceItem, assemble
from .identity import canonical_bytes, occurrence_key
from .publication import EvidenceRow, PublicationBatch
from .record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)
from .types import PreparationProfile, PreparedRelease, SourceArtifact, SourceBundle

_NAMESPACE = "https://corpus-structure.dev/semantic/source-reading/"
_FAMILIES = {
    "definition": "DefinitionReading",
    "assertion": "QualifiedAssertionReading",
    "measurement": "MeasurementReading",
    "table": "TableAssertionReading",
    "formula_context": "FormulaContextReading",
}
_VALUE_FIELDS = frozenset(
    {
        "kind",
        "state",
        "meaning_changing",
        "evidence_status",
        "value",
        "original",
        "original_pieces",
        "reason",
        "policy",
        "rule",
        "premises",
    }
)
_MODULE = "source-readings"
_ROOT = "source-reading-root"


def _scalar_name(name: str) -> str:
    return "SourceReading" + (name[6:] if name.startswith("Record") else name)


def _field_name(name: str) -> str:
    return "SourceReading" + name.replace("RecordField", "").removesuffix("Field") + "Value"


def source_reading_inputs(bundle: SourceBundle) -> SourceBundle:
    """Derive graph declarations from the effective supplied LinkML family contracts.

    Call after observation inputs, before prepare_release. No release ID or prepared
    registry is needed. The resulting source bytes are archived/hashed normally.
    """
    from .prepare import _view

    if any(source.name in {_MODULE, _ROOT} for source in bundle.sources):
        if bundle.root != _ROOT:
            raise ValueError("reserved source-reading module already supplied")
        original_root = yaml.safe_load(next(s.content for s in bundle.sources if s.name == _ROOT))[
            "imports"
        ][0]
        original = SourceBundle(
            original_root, tuple(s for s in bundle.sources if s.name not in {_MODULE, _ROOT})
        )
        if source_reading_inputs(original) != bundle:
            raise ValueError("source-reading declarations differ from effective family contracts")
        return bundle
    view = _view(bundle, PreparationProfile(version="semantic-2"))
    classes = {str(name): definition for name, definition in view.all_classes().items()}
    if "SemanticRecordFields" not in classes:
        raise ValueError("source reading derivation requires observation record declarations")
    families: dict[str, tuple[str, list[Any]]] = {}
    for name in sorted(classes):
        if name == "SemanticRecordFields" or "SemanticRecordFields" not in view.class_ancestors(
            name
        ):
            continue
        slots = {str(slot.name): slot for slot in view.class_induced_slots(name)}
        family = slots["family"].equals_string or ""
        if family not in _FAMILIES or family in families:
            raise ValueError("unsupported or duplicate source-reading family")
        families[family] = (
            name,
            [slot for key, slot in slots.items() if key not in {"family", "occurrence_recipe"}],
        )
    if not families:
        raise ValueError("source reading derivation requires an effective family")
    scalar_classes = {
        name
        for name in classes
        if name == "RecordScalar" or "RecordScalar" in view.class_ancestors(name)
    }
    field_classes = {str(slot.range) for _, roles in families.values() for slot in roles}
    names = {name: _scalar_name(name) for name in scalar_classes}
    names.update({name: _field_name(name) for name in field_classes})
    if len(set(names.values())) != len(names) or set(names.values()) & set(classes):
        raise ValueError("derived source-reading value name collision")

    def attribute(slot, *, owner: str):
        body = json_dumper.to_dict(slot)
        # Induced ownership is compiler metadata, not another declared relationship.
        for key in (
            "name",
            "owner",
            "domain_of",
            "from_schema",
            "domain",
            "is_a",
            "mixins",
            "pattern",
        ):
            body.pop(key, None)
        body["slot_uri"] = "reading:" + owner + "/" + str(slot.name)
        if str(slot.range) in names:
            body["range"] = names[str(slot.range)]
        elif str(slot.range) in classes:
            raise ValueError(
                "graph-safe reading value cannot reference private class " + str(slot.range)
            )
        return body

    derived: dict[str, Any] = {
        "SourceReading": {
            "is_a": "Entity",
            "abstract": True,
            "class_uri": "reading:SourceReading",
            "annotations": {"cs:scope": "local", "cs:case": "preserve"},
        }
    }
    for name in sorted(scalar_classes | field_classes):
        target = names[name]
        attrs = {
            str(slot.name): attribute(slot, owner=target)
            for slot in view.class_induced_slots(name)
            if name in scalar_classes or str(slot.name) in _VALUE_FIELDS
        }
        body: dict[str, Any] = {"class_uri": "reading:" + target, "attributes": attrs}
        if name in scalar_classes:
            original = classes[name]
            if original.is_a and str(original.is_a) in scalar_classes:
                body["is_a"] = names[str(original.is_a)]
            if original.abstract:
                body["abstract"] = True
        derived[target] = body
    for family, (_, roles) in sorted(families.items()):
        target = _FAMILIES[family]
        if target in classes:
            raise ValueError("derived source-reading class collision")
        attrs = {}
        for slot in roles:
            if not slot.required or slot.multivalued or not slot.inlined:
                raise ValueError("reading roles require scalar required inlined fields")
            attrs[str(slot.name)] = {
                "range": names[str(slot.range)],
                "required": True,
                "inlined": True,
                "slot_uri": "reading:" + target + "/" + str(slot.name),
            }
        derived[target] = {
            "is_a": "SourceReading",
            "class_uri": "reading:" + target,
            "attributes": attrs,
        }
    module = {
        "id": _NAMESPACE,
        "name": "semantic_source_readings",
        "default_range": "string",
        "prefixes": {"reading": _NAMESPACE},
        "default_prefix": "reading",
        "classes": derived,
    }
    return SourceBundle(
        _ROOT,
        (
            *bundle.sources,
            SourceArtifact(_MODULE, yaml.safe_dump(module, sort_keys=True).encode()),
            SourceArtifact(
                _ROOT,
                yaml.safe_dump(
                    {
                        "id": _NAMESPACE + "root",
                        "name": "semantic_source_reading_root",
                        "imports": [bundle.root, _MODULE],
                    },
                    sort_keys=True,
                ).encode(),
            ),
        ),
    )


@dataclass(frozen=True)
class RecordAssertionBinding:
    record_id: str
    interpretation_id: str
    role: str
    reading_id: str
    fact_id: str
    occurrence_id: str


@dataclass(frozen=True)
class RecordAssertionSupport:
    """Finite join to the actual sealed field/set/anchor; no Agent observation ID."""

    origin_task_id: int
    record_id: str
    interpretation_id: str
    role: str
    set_id: str
    anchor_id: str
    evidence_id: str
    occurrence_id: str


@dataclass(frozen=True)
class RecordAssertionDiagnostic:
    record_id: str
    interpretation_id: str
    reason: str


@dataclass(frozen=True)
class RecordAssertionLowering:
    batch: PublicationBatch
    assertions: tuple[RecordAssertionBinding, ...]
    support: tuple[RecordAssertionSupport, ...]
    diagnostics: tuple[RecordAssertionDiagnostic, ...]


def reading_identity(release_id: str, record_id: str, interpretation_id: str) -> str:
    return (
        "source-reading:"
        + sha256(canonical_bytes([release_id, record_id, interpretation_id])).hexdigest()
    )


def lower_record_assertions(
    prepared: PreparedRelease,
    realization_id: str,
    batch_id: str,
    reports: Sequence[Mapping[str, Any]],
) -> RecordAssertionLowering:
    """Lower complete candidate readings, with no selected facts or acceptance overlay.

    Reports are detached native sealed-cut reports with truthful ``source_uri``,
    ``provider`` and ``operation_version`` producer descriptors. Every role, including
    nonpresent ones, must have its own sealed evidence set. Incomplete readings yield
    diagnostics and no partial graph. Persisted task/source authentication stays native.
    """
    items: list[SourceItem] = []
    pending_bindings: list[tuple[str, str, str, str, str]] = []
    support: list[RecordAssertionSupport] = []
    diagnostics: list[RecordAssertionDiagnostic] = []
    seen: dict[tuple[str, str], bytes] = {}
    for report in reports:
        if not report.get("records"):
            continue
        if type(report.get("origin_task_id")) is not int or report["origin_task_id"] < 1:
            raise ValueError("source readings require actual origin task custody")
        if any(
            not isinstance(report.get(k), str) or not report[k]
            for k in ("source_uri", "provider", "operation_version")
        ):
            raise ValueError("source readings require actual producer and source descriptors")
        for model in report["records"]:
            raw = (
                model.model_dump(mode="python", exclude_unset=True)
                if isinstance(model, BaseModel)
                else dict(model)
            )
            row = prepared.validate_json("SourceRecord", canonical_bytes(raw)).model_dump(
                mode="python", exclude_unset=True
            )
            key = row["record_id"], row["interpretation_id"]
            content = canonical_bytes(row)
            if key in seen:
                if seen[key] != content:
                    raise ValueError("record identity has conflicting immutable contents")
                continue
            seen[key] = content
            local_items: list[SourceItem] = []
            local_support: list[tuple[str, str, str, str]] = []
            try:
                prepared.validate_python("SourceRecord", row)
                if (
                    row["pin"]["source"] != report["source"]
                    or record_identity(prepared.release_id, row) != key[0]
                    or interpretation_identity(row) != key[1]
                ):
                    raise ValueError("source-reading identity/source differs from sealed record")
                definition = prepared.index.definitions[row["contract"]]
                if "SemanticRecordFields" not in definition.ancestors:
                    raise ValueError("reading contract is not an effective record family")
                contract = {p.name: p for p in definition.properties}
                if (
                    contract["family"].equals_string != row["family"]
                    or contract["occurrence_recipe"].equals_string != row["occurrence_recipe"]
                ):
                    raise ValueError("reading family differs from effective record contract")
                fields = {f["role"]: f for f in row["fields"]}
                expected = set(contract) - {"family", "occurrence_recipe"}
                if len(fields) != len(row["fields"]) or set(fields) != expected:
                    raise ValueError("reading roles differ from complete effective family")
                prepared.validate_python(
                    row["contract"],
                    {
                        "family": row["family"],
                        "occurrence_recipe": row["occurrence_recipe"],
                        **fields,
                    },
                )
                anchors = {a["anchor_id"]: a for a in row["anchors"]}
                sets = {s["set_id"]: s for s in row.get("evidence_sets", ())}
                if len(anchors) != len(row["anchors"]) or any(
                    anchor_identity(a) != k for k, a in anchors.items()
                ):
                    raise ValueError("reading anchor content differs from identity")
                if len(sets) != len(row.get("evidence_sets", ())):
                    raise ValueError("duplicate reading evidence set")
                reading = reading_identity(prepared.release_id, *key)
                class_name = _FAMILIES[row["family"]]
                for role in sorted(fields):
                    field = fields[role]
                    used = tuple(field.get("evidence_sets", ()))
                    if (
                        field["evidence_status"] != "available"
                        or not used
                        or len(set(used)) != len(used)
                    ):
                        raise ValueError("reading role lacks its own sealed evidence: " + role)
                    located = {}
                    for set_id in used:
                        evidence_set = sets[set_id]
                        if (
                            evidence_set["role"] != role
                            or evidence_set_identity(evidence_set) != set_id
                        ):
                            raise ValueError(
                                "reading field support belongs to another role or content"
                            )
                        for anchor_id in evidence_set["anchors"]:
                            anchor = anchors[anchor_id]
                            evidence_id = (
                                "reading-evidence:"
                                + sha256(
                                    canonical_bytes(
                                        [
                                            prepared.release_id,
                                            report["origin_task_id"],
                                            *key,
                                            role,
                                            set_id,
                                            anchor_id,
                                        ]
                                    )
                                ).hexdigest()
                            )
                            locator = {
                                k: anchor[k]
                                for k in ("space", "pointer", "precision", "start", "end")
                                if k in anchor
                            }
                            locator.update(
                                record_id=key[0],
                                interpretation_id=key[1],
                                role=role,
                                set_id=set_id,
                                anchor_id=anchor_id,
                            )
                            located[evidence_id] = EvidenceRow(
                                evidence_id,
                                report["source_uri"],
                                canonical_bytes(locator).decode(),
                                report["provider"],
                                report["operation_version"],
                            )
                            local_support.append((role, set_id, anchor_id, evidence_id))
                    value = {name: value for name, value in field.items() if name in _VALUE_FIELDS}
                    local_items.append(
                        SourceItem(
                            reading,
                            class_name,
                            role,
                            value,
                            {"modality": "asserted", "polarity": True},
                            report["source"],
                            reading + "/" + role,
                            "stated",
                            tuple(located.values()),
                        )
                    )
                # Check the released value boundary before retaining any role. The
                # combined graph is lowered once, after all record decisions.
                for item in local_items:
                    prepared.property_adapter(item.class_name, item.property_name).validate_python(
                        item.object, strict=True
                    )
            except (KeyError, ValueError) as error:
                diagnostics.append(RecordAssertionDiagnostic(*key, str(error)))
                continue
            for item in local_items:
                pending_bindings.append((*key, item.property_name, reading, item.item))
            for role, set_id, anchor_id, evidence_id in local_support:
                support.append(
                    RecordAssertionSupport(
                        report["origin_task_id"],
                        *key,
                        role,
                        set_id,
                        anchor_id,
                        evidence_id,
                        occurrence_key(
                            prepared.release_id,
                            realization_id,
                            report["source"],
                            reading + "/" + role,
                        ),
                    )
                )
            items.extend(local_items)
    batch = assemble(prepared, realization_id, batch_id, tuple(items))
    occurrences = {occ.item: occ for occ in batch.occurrence}
    bindings = tuple(
        RecordAssertionBinding(
            record_id,
            interpretation_id,
            role,
            reading,
            occurrences[item].fact_id,
            occurrences[item].occurrence_id,
        )
        for record_id, interpretation_id, role, reading, item in pending_bindings
    )
    return RecordAssertionLowering(batch, bindings, tuple(support), tuple(diagnostics))

"""Actual raw-to-resolved whole-report correspondence for rich CPU consumers."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .data_operation_identity import semantic_value
from .data_operation_json import json_bytes
from .identity import canonical_bytes
from .rich_knowledge_contracts import DdoRichSelectedMember

def _episode_key(reference):
    from .rich_knowledge_contracts import rich_support_records
    support = sorted({canonical_bytes({key: value for key, value in item.items() if key != "admission_use_id"}) for item in rich_support_records(reference.support_references)})
    import json
    return canonical_bytes([reference.product_id, reference.member_id, reference.kind_contract, [json.loads(value) for value in support]])


def _original_reference(inputs, role, population):
    current = inputs.reference(role)
    matches = tuple(value for value in population if _episode_key(value) == _episode_key(current))
    if len(matches) != 1:
        raise ValueError("rich admission input differs from its exact original consolidation population")
    return matches[0]


def _member(reference, packet):
    return reference.model_copy(update={"member_id": packet["member_id"], "kind_contract": packet["kind_contract"]})



@dataclass(frozen=True)
class RichReadingSelection:
    original: DdoRichSelectedMember
    raw: dict
    raw_report: dict
    resolution: DdoRichSelectedMember | None
    resolved: DdoRichSelectedMember | None
    row: dict | None
    events: tuple[dict,...]
    event: dict | None


def select_rich_readings(prepared, inputs, *, original_population=None):
    from .reading_resolution_products import RECIPE, resolved_reading_events
    readings=[]
    reference=lambda role: inputs.reference(role) if original_population is None else _original_reference(inputs,role,original_population)
    for role in inputs.selected("readings"):
        report=prepared.validate_json("DdoResolvedReadingReport",json_bytes(role.body)).model_dump(mode="python",exclude_unset=True)
        readings.append((reference(role),report,resolved_reading_events(report)))
    selected=[]
    for role in inputs.selected("records"):
        report=prepared.validate_json("DdoCandidateInspectionReport",json_bytes(role.body)).model_dump(mode="python",exclude_unset=True)
        parent=reference(role)
        for packet in report["members"]:
            if packet["body"]["candidate_type"]!="record":
                continue
            raw={key:value for key,value in packet["body"].items() if key!="candidate_type"}
            original=_member(parent,packet)
            matches=[]
            for resolution,resolved_report,events in readings:
                if resolved_report["source_pin"]!=report["source_pin"]:
                    continue
                for resolved_packet in resolved_report["members"]:
                    value=resolved_packet["body"]
                    if value["candidate_type"]!="record" or value["record_id"]!=raw["record_id"]:
                        continue
                    resolved={key:child for key,child in value.items() if key!="candidate_type"}
                    if {key:child for key,child in resolved.items() if key not in {"interpretation_id","computation_dependencies"}}!={key:child for key,child in raw.items() if key not in {"interpretation_id","computation_dependencies"}}:
                        continue
                    event=tuple(item for item in events if (item.get("record_id"),item.get("interpretation_id"))==(resolved["record_id"],resolved["interpretation_id"]))
                    if len(event)!=1:
                        raise ValueError("rich resolution lacks one genuine complete per-reading event")
                    expected={*raw.get("computation_dependencies", ()),"reading-recipe:"+RECIPE,
                              "raw-candidate-result:"+sha256(canonical_bytes(semantic_value(role.body))).hexdigest()}
                    instance=event[0].get("feature_instance_digest")
                    if instance is not None:
                        expected.add("record-feature-instance:"+instance)
                    if set(resolved["computation_dependencies"])!=expected:
                        continue
                    matches.append((resolution,_member(resolution,resolved_packet),resolved,events,event[0]))
            if len(matches)>1:
                raise ValueError("rich raw reading has multiple unresolved resolution alternatives")
            resolution,resolved,row,events,event=matches[0] if matches else (None,None,None,(),None)
            selected.append(RichReadingSelection(original,raw,report,resolution,resolved,row,events,event))
    return tuple(selected)

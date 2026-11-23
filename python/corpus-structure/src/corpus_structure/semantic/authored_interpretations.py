"""Checked private judgments over exact selected readings; authorship is not computation."""

from __future__ import annotations

from .data_operation_json import json_bytes, json_loads
from .grouped_record_interpretations import RetainedAuthoredJudgment
from .interpretations import validate_interpretation_payload

JUDGMENT_KINDS = {
    "DdoAuthoredMeasurementJudgment": "measurement.interpretation",
    "DdoAuthoredTerminologyJudgment": "terminology.interpretation",
}
JUDGMENT_KIND_IRIS = frozenset(
    f"https://corpus-structure.dev/domains/statistics/terminology/{kind}"
    for kind in JUDGMENT_KINDS
)


def checked_judgment(prepared, nominal, body):
    definition = next((item for item in prepared.definitions if item.iri == nominal), None)
    if definition is None or definition.name not in JUDGMENT_KINDS:
        raise ValueError("authored interpretation lacks its exact captured judgment kind")
    checked = prepared.validate_json(definition.name, json_bytes(body)).model_dump(
        mode="python", exclude_unset=True
    )
    if json_bytes(checked) != json_bytes(body):
        raise ValueError("authored judgment differs from its captured kind")
    validate_interpretation_payload(prepared, JUDGMENT_KINDS[definition.name], checked)
    return checked


def judgment_reading(body, groups, source_cut):
    """Check occurrence, field evidence and source context without merging alternatives."""
    source = body["source_record"]
    if json_bytes(json_loads(source["read_scope_json"])) != json_bytes(source_cut.record["scope"]):
        raise ValueError("authored judgment differs from its pinned source read scope")
    if (
        any(
            source[name] != source_cut.record[name]
            for name in ("project_id", "demand_id", "read_id", "release_id", "runtime_id")
        )
        or source["cut_id"] != source_cut.identity
    ):
        raise ValueError("authored judgment differs from its exact pinned source cut")
    matches = [
        (group, reading)
        for group in groups
        if group.candidate_universe.product_id == source["product_id"]
        and group.family_contract == source["family_contract"]
        and group.record_id == source["record_id"]
        for reading in group.readings
        if reading.reference.member_id == source["member_id"]
        and reading.reference.kind_contract == source["kind_contract"]
        and reading.interpretation_id == source["interpretation_id"]
    ]
    if len(matches) != 1:
        raise ValueError("authored judgment does not identify one actual selected reading")
    group, reading = matches[0]
    if json_bytes(source["source_pin"]) != json_bytes(reading.body["pin"]):
        raise ValueError("authored judgment differs from the complete selected source context")
    if body["judgment_type"] == "measurement.interpretation" and group.family != "measurement":
        raise ValueError("measurement judgment requires a measurement occurrence")
    focuses = (
        (body["focus"],)
        if body["judgment_type"] == "measurement.interpretation"
        else tuple(decision["focus"] for decision in body["decisions"])
    )
    fields = {field["role"]: field for field in reading.body["fields"]}
    evidence = {item["set_id"]: item for item in reading.body["evidence_sets"]}
    anchors = {anchor["anchor_id"]: anchor for anchor in reading.body["anchors"]}
    for focus in focuses:
        field = fields.get(focus["role"])
        if field is None or field["state"] != "present":
            raise ValueError("judgment focus is not a present selected reading field")
        allowed = {
            anchor_id
            for set_id in field["evidence_sets"]
            for anchor_id in evidence[set_id]["anchors"]
        }
        anchor = anchors.get(focus["anchor_id"])
        if (
            focus["anchor_id"] not in allowed
            or anchor is None
            or anchor["precision"] != "exact"
            or not anchor["start"] <= focus["start"] < focus["end"] <= anchor["end"]
            or anchor["source_piece"][
                focus["start"] - anchor["start"] : focus["end"] - anchor["start"]
            ]
            != focus["source_piece"]
        ):
            raise ValueError("judgment focus differs from exact selected field source evidence")
    return group, reading


def attach_authored_judgment(groups, body, *, reference, author, selection_id, source_reference):
    """Attach an authenticated judgment to one selected occurrence, retaining its own body."""
    source = body["source_record"]
    matches = [
        group
        for group in groups
        if group.candidate_universe.product_id == source["product_id"]
        and group.family_contract == source["family_contract"]
        and group.record_id == source["record_id"]
        and any(
            reading.reference.member_id == source["member_id"]
            and reading.reference.kind_contract == source["kind_contract"]
            and reading.interpretation_id == source["interpretation_id"]
            and json_bytes(reading.body["pin"]) == json_bytes(source["source_pin"])
            for reading in group.readings
        )
    ]
    if len(matches) != 1:
        raise ValueError("authored judgment is outside the selected exact occurrence groups")
    target = matches[0]
    for previous in target.authored_judgments:
        if previous.source_reference == source_reference:
            if (
                previous.author != author
                or previous.selection_id != selection_id
                or previous.reference.product_id != reference.product_id
                or json_bytes(previous.body) != json_bytes(body)
            ):
                raise ValueError("one authored source reference has conflicting judgment values")
            return tuple(groups)
    judgment = RetainedAuthoredJudgment(
        reference=reference,
        author=author,
        selection_id=selection_id,
        source_reference=source_reference,
        body=body,
    )
    return tuple(
        group.model_copy(update={"authored_judgments": (*group.authored_judgments, judgment)})
        if group.identity == target.identity
        else group
        for group in groups
    )

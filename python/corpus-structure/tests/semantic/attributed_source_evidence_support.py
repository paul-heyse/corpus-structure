"""Shared controlled inputs and builders for attributed source evidence support."""

import json
from copy import deepcopy
from typing import Any

from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)
from semantic.record_contracts_support import PIN, release_inputs, table_record

BINDING = dict(version=2, relationship="selected_context", policy="attributed-selected-source-2")


def replace_note(record, anchor):
    previous = next(a for a in record["anchors"] if a["pointer"] == "#/texts/4")
    anchor["anchor_id"] = anchor_identity(anchor)
    record["anchors"] = tuple(anchor if a is previous else a for a in record["anchors"])
    sets = []
    replacements = {}
    for evidence in record["evidence_sets"]:
        changed: dict[str, Any] = dict(
            evidence,
            anchors=tuple(
                anchor["anchor_id"] if key == previous["anchor_id"] else key
                for key in evidence["anchors"]
            ),
        )
        changed["set_id"] = evidence_set_identity(changed)
        replacements[evidence["set_id"]] = changed["set_id"]
        sets.append(changed)
    record["evidence_sets"] = tuple(sets)
    for field in record["fields"]:
        field["evidence_sets"] = tuple(replacements[key] for key in field["evidence_sets"])
    record["record_id"] = record_identity(release_inputs()[2].release_id, record)
    record["interpretation_id"] = interpretation_identity(record)
    return record


def captured_note():
    record, contexts = table_record()
    note = deepcopy(next(a for a in record["anchors"] if a["pointer"] == "#/texts/4"))
    provider = dict(
        occurrence_id="provider:7",
        kind="text",
        precision="coarse",
        address_space="submitted_pixels",
        text="hypothetical",
        region=dict(precision="coarse", left=0, right=80),
    )
    address = dict(
        selected_occurrence_id="selected:4",
        task_id=12,
        product_key="recognition",
        content_digest="e" * 64,
        occurrence_id="provider:7",
        relation_id="decision:4",
        endpoint_role="evidence",
        relation_kind="decision",
        relation_outcome="selected",
        provider_occurrence_json=json.dumps(provider),
        observation_json=json.dumps(
            dict(image=dict(precision="unknown"), raw_response_digest="f" * 64)
        ),
    )
    note.update(
        binding=dict(BINDING, relationship="primary"),
        space="captured_recognition",
        recognition=address,
    )
    replace_note(record, note)
    coordinate = dict(
        pin=PIN,
        space="captured_recognition",
        pointer="#/texts/4",
        recognition=address,
        text="hypothetical",
    )
    return record, (*contexts, coordinate), provider

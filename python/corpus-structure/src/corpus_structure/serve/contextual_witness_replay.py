"""Replay exact contextual witness nominations without executing a provider."""

import json
import re
from dataclasses import asdict

from corpus_structure.methods.contextual_candidates import explicit_definition_section
from corpus_structure.methods.contextual_embeddings import EncodedVector
from corpus_structure.semantic.contextual_registry import ExtractedComponentTarget
from corpus_structure.semantic.contextual_retrieval import (
    ChannelHit,
    FrozenInventory,
    SemanticTargetGroup,
    TargetRepresentation,
    fuse_candidates,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.structural_products import StructuralProductReport


def _reports(body):
    if body.get("operation_version") == "6":
        for op in body.get("contribution_operations", ()):
            if "contextual_enrichment" in op:
                yield op["contextual_enrichment"]


def _supports_witnesses(configuration):
    return any(
        "defined-by" in question["relation_kinds"]
        for question in configuration.get("relationship_constraints", ())
    )


def _possible_carriers(body):
    for row in body.get("contributions", ()):
        if row.get("semantic_type") != "contextual.located_mention":
            continue
        value = source_python(row["value"])
        producer = value["producer_semantic_type"]
        named_section = producer == "structural.located_participant" and any(
            anchor.get("source_piece", "").startswith("Section ") for anchor in row["anchors"]
        )
        if producer == "definition.term" or named_section:
            yield row


def witness_origin_ids(body, configuration):
    if not _supports_witnesses(configuration) or not any(_possible_carriers(body)):
        return set()
    return {
        target["reference"]["origin_task_id"]
        for report in _reports(body)
        if report.get("candidate_lists")
        for target in report["component_targets"]
    }


def _term_binding(target, reports, sources):
    ref = target.reference
    origin = reports[ref.origin_task_id]
    body = origin["body"]
    report = StructuralProductReport.model_validate(body["structural_product"])
    if (
        report.product_id != ref.product_id
        or origin["project_id"] != ref.project_id
        or origin["runtime_fingerprint"] != ref.runtime_fingerprint
        or origin["method"] != ref.operation_id
        or body["release_id"] != ref.release_id
        or body["operation_version"] != ref.operation_version
        or report.inputs.dependencies != ref.dependencies
        or report.definition_components is None
    ):
        raise ValueError("contextual witness target lacks exact retained component custody")
    (component,) = [
        c for c in report.definition_components.components if c.component_id == ref.component_id
    ]
    if (
        component.term.text != target.label
        or component.content.text != target.description
        or component.scope != target.scope
        or component.effective_version != target.effective_version
    ):
        raise ValueError("contextual witness target changes retained component meaning")
    term = component.term
    (passage,) = [p for p in report.inputs.passages if p.passage_id == term.passage_id]
    (physical,) = [p for p in report.inputs.sources if p.identity == passage.source_ref]
    source = sources[physical.source_view_id]
    native = source["ref"]["native_product"]
    if (
        native["task_id"] != physical.native_task_id
        or native["product_key"] != physical.native_product_key
        or native["content_digest"] != physical.native_content_digest
        or source["ref"]["projection_digest"] != physical.projection_digest
        or source["ref"]["recipe_digest"] != physical.recipe_digest
        or source["text"][term.start : term.end] != term.text
    ):
        raise ValueError("contextual witness target differs from original native source")
    return physical, term, source


def _section(source, term):
    items = {i["self_ref"]: i for i in source["context"]["items"]}
    pieces = [
        p
        for p in source["context"]["pieces"]
        if p["kind"] == "native_text"
        and "cell_index" not in p
        and p.get("source_field", "text") == "text"
    ]
    selected = [p for p in pieces if p["start"] <= term.start < term.end <= p["end"]]
    if len(selected) != 1:
        return None
    (piece,) = selected
    original = items[piece["item_ref"]]
    if original.get("content_layer") != "body" or not original.get("parent"):
        return None
    headers = [
        (p["end"], items[p["item_ref"]]["text"])
        for p in pieces
        if p["end"] <= piece["start"]
        and (
            (node := items[p["item_ref"]]).get("label") == "section_header"
            and node.get("content_layer") == "body"
            and node.get("parent") == original["parent"]
        )
    ]
    if not headers:
        return None
    match = re.match(r"^(?:Section )?([0-9]+(?:\.[0-9]+)+)(?:\s|$)", max(headers)[1])
    return match[1] if match else None


def verify_contextual_witness_closure(root, manifest):
    from .review_bundle import _detached_relation

    if "reports" not in manifest["relations"]:
        return
    reports = {r["origin_task_id"]: r for r in _detached_relation(root, manifest, "reports")}
    relevant = [
        r
        for r in reports.values()
        if r.get("method") == "retrieve.contextual"
        and witness_origin_ids(r.get("body") or {}, r.get("configuration") or {})
    ]
    if not relevant:
        return
    sources = {s["source_view_id"]: s for s in _detached_relation(root, manifest, "sources")}
    for retained in relevant:
        body = retained["body"]
        if retained["method"] != "retrieve.contextual":
            raise ValueError("contextual witness channel belongs to another producer")
        source = sources[retained["origin_unit_id"]]
        nodes = {i["self_ref"]: i for i in source["context"]["items"]}
        carriers = tuple(_possible_carriers(body))
        for report in _reports(body):
            targets = {
                t.reference.component_id: (t, _term_binding(t, reports, sources))
                for row in report["component_targets"]
                for t in (ExtractedComponentTarget.model_validate(row),)
            }
            for candidate in report["candidate_lists"]:
                channels = {
                    ch["channel"]: tuple(
                        ChannelHit(h["target_id"], float(h["score"]), tuple(h.get("evidence", ())))
                        for h in ch.get("hits", ())
                    )
                    for ch in candidate["channel_results"]
                }
                (inventory,) = [
                    i
                    for i in report["inventories"]
                    if i["inventory_id"] == candidate["inventory_id"]
                ]
                eligible = {t["target_id"] for t in inventory["targets"]}
                expected = {}
                for row in carriers:
                    if row["occurrence_id"] != candidate["occurrence_id"]:
                        continue
                    value = source_python(row["value"])
                    proposal = source_python(value["producer_value"])
                    code = explicit_definition_section(row, nodes)
                    for target_id in eligible:
                        target, (physical, term, original) = targets[target_id]
                        if code is not None:
                            valid = (
                                physical.native_content_digest
                                == source["ref"]["native_product"]["content_digest"]
                                and _section(original, term) == code
                            )
                        else:
                            valid = (
                                value["producer_semantic_type"] == "definition.term"
                                and proposal.get("role") == "defined_term"
                                and proposal.get("component_reference")
                                == target.reference.model_dump(mode="json")
                            )
                        if valid:
                            expected.setdefault(target_id, set()).add(row["contribution_id"])
                exact = tuple(
                    ChannelHit(target_id, 1.0, tuple(sorted(expected[target_id])))
                    for target_id in sorted(expected)
                )
                if channels.get("witness", ()) != exact:
                    raise ValueError(
                        "contextual witness channel differs from its complete source population"
                    )
                if not exact:
                    continue
                vector_id = candidate.get("query_vector_id")
                vector = next((v for v in report["vectors"] if v["vector_id"] == vector_id), None)
                if (vector is None) != (vector_id is None):
                    raise ValueError("contextual nomination lacks its declared query vector")
                frozen = FrozenInventory(
                    **(
                        inventory
                        | {
                            "effective_version": inventory.get("effective_version"),
                            "targets": tuple(
                                TargetRepresentation(
                                    **(target | {"aliases": tuple(target.get("aliases", ()))})
                                )
                                for target in inventory["targets"]
                            ),
                            "semantic_groups": tuple(
                                SemanticTargetGroup(**g) for g in inventory["semantic_groups"]
                            ),
                        }
                    )
                )
                replay = fuse_candidates(
                    occurrence_id=candidate["occurrence_id"],
                    query=EncodedVector(**vector) if vector else None,
                    inventory=frozen,
                    channels=channels,
                    budget=candidate["unique_target_budget"],
                    channel_budget=candidate["channel_budget"],
                    lexical_query=candidate["lexical_query"],
                )
                # Release projection omits empty optional evidence arrays.
                replay_rows = json.loads(canonical_bytes(asdict(replay)))["candidates"]
                for row in replay_rows:
                    for evidence in row["channels"]:
                        if not evidence["evidence"]:
                            evidence.pop("evidence")
                stored_rows = json.loads(canonical_bytes(candidate["candidates"]))
                for row in stored_rows:
                    for evidence in row["channels"]:
                        if not evidence.get("evidence"):
                            evidence.pop("evidence", None)
                if (
                    replay.list_id != candidate["list_id"]
                    or replay_rows != stored_rows
                    or replay.profile_id != candidate.get("profile_id")
                    or replay.policy_id != candidate["policy_id"]
                ):
                    raise ValueError("contextual witness rank differs from retained channels")

"""Replay exact contextual witness nominations without executing a provider."""

import base64
import json
import re
from collections import defaultdict
from dataclasses import asdict
from hashlib import sha256

from corpus_structure.core.evidence import config_key
from corpus_structure.methods.contextual_candidates import (
    SECTION_CONSTRAINT,
    ContextualCandidateConfig,
    explicit_definition_section,
    explicit_definition_subject,
    explicit_section_citation,
    relationship_contributions,
    retained_occurrences,
    section_citation_witnesses,
    section_definition_subject_witnesses,
)
from corpus_structure.methods.contextual_embeddings import EncodedVector, identity
from corpus_structure.semantic.contextual_links import RelationshipWitness, select_relationships
from corpus_structure.semantic.contextual_registry import (
    ExtractedComponentTarget,
    SectionHeadingTarget,
    section_target_input,
)
from corpus_structure.semantic.contextual_retrieval import (
    ChannelHit,
    FrozenInventory,
    SemanticTargetGroup,
    TargetRepresentation,
    freeze_inventory,
    fuse_candidates,
)
from corpus_structure.semantic.contributions import operation_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.structural_products import StructuralProductReport


def _reports(body):
    if body.get("operation_version") in {"6", "7", "8", "9"}:
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
        original = source_python(value["producer_value"])
        marker = original.get("named_cue")
        named_section = producer == "structural.located_participant" and (
            (isinstance(marker, dict) and marker.get("kind") == "definition_reference")
            or (
                marker is None
                and any(
                    re.fullmatch(
                        r"Section\s+[0-9]+(?:\.[0-9]+)+", anchor.get("source_piece", ""), re.I
                    )
                    for anchor in row["anchors"]
                )
            )
        )
        if producer == "definition.term" or named_section:
            yield row


def witness_origin_ids(body, configuration):
    if configuration.get("section_sources"):
        return {report["section_source_origin_task_id"] for report in _reports(body)}
    if not _supports_witnesses(configuration) or not any(_possible_carriers(body)):
        return set()
    return {
        target["reference"]["origin_task_id"]
        for report in _reports(body)
        if report.get("candidate_lists")
        for target in report["component_targets"]
    }


def _packet_mapping(contract):
    from .review_bundle import SECTION_PACKET_INPUT

    retained = contract["section_packets"]
    manifest = base64.b64decode(retained["manifest_base64"], validate=True)
    if "release:" + sha256(manifest).hexdigest() != contract["release_id"]:
        raise ValueError("section packet mapping has a foreign release manifest")
    content = base64.b64decode(retained["input_base64"], validate=True)
    if sha256(content).hexdigest() != dict(json.loads(manifest)["dependencies"]).get(
        SECTION_PACKET_INPUT
    ):
        raise ValueError("section packet mapping differs from release input")
    packet = json.loads(content)
    if packet["version"] != 1:
        raise ValueError("unsupported section packet mapping")
    return packet


def _heading_inventory(config, source_view_id, sources, documents, packet):
    """Reconstruct selected headings from retained native pieces and work authority."""
    entries = []
    for ref in config.section_sources:
        view = sources[ref.source_view_id]
        content_hash = documents[view["ref"]["document_id"]]["content_hash"]
        parent = (
            packet["packets"].get(content_hash)
            if packet["native_products"].get(ref.native_content_digest) == content_hash
            else None
        )
        entries.append((ref, view, parent))
    (cue,) = [entry for entry in entries if entry[0].source_view_id == source_view_id]
    cue_digest, cue_parent = cue[0].native_content_digest, cue[2]
    work_id = "parent-pdf:" + cue_parent if cue_parent else "native-packet:" + cue_digest
    grouped = defaultdict(list)
    complete = True
    for ref, view, parent in entries:
        if ref.native_content_digest != cue_digest:
            complete &= parent is not None and cue_parent is not None
            if parent is None or parent != cue_parent:
                continue
        pointers = {
            piece["item_ref"]
            for piece in view["context"]["pieces"]
            if piece["kind"] == "native_text"
            and "cell_index" not in piece
            and piece.get("source_field", "text") == "text"
        }
        for item in view["context"]["items"]:
            if (
                item.get("label") != "section_header"
                or item.get("content_layer") != "body"
                or item["self_ref"] not in pointers
            ):
                continue
            label, pointer = item["text"], item["self_ref"]
            match = re.match(r"^(?:Section )?([0-9]+(?:\.[0-9]+)+)(?:\s|$)", label)
            if match:
                target = identity(
                    "section-heading",
                    [ref.native_content_digest, ref.native_product_key, pointer, 0, len(label)],
                )
                grouped[target, pointer, label, match[1]].append(ref)
    targets = tuple(
        SectionHeadingTarget(
            target_id=target,
            pointer=pointer,
            label=label,
            designator=code,
            work_id=work_id,
            scope=config.scope,
            effective_version=config.effective_version,
            citations=tuple(sorted(citations, key=lambda ref: ref.identity)),
        )
        for (target, pointer, label, code), citations in sorted(grouped.items())
    )
    registry, representations, meanings = section_target_input(config.section_sources, targets)
    inventory = freeze_inventory(
        representations,
        source_selection=registry,
        scope=config.scope,
        effective_version=config.effective_version,
        reliable_type="section-heading",
        semantic_targets=meanings,
    )
    return targets, inventory, complete


def _wire(value):
    """Compare report values modulo the release's omission of empty optional fields."""
    if isinstance(value, dict):
        return {
            key: _wire(member)
            for key, member in value.items()
            if member is not None and member != [] and member != ()
        }
    if isinstance(value, (list, tuple)):
        return [_wire(member) for member in value]
    return value


def _verify_section_report(retained, reports, sources, documents, contract):
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import record_source_pin

    from .review_bundle import _retained_review_source_view

    body, configuration = retained["body"], retained["configuration"]
    version = body["operation_version"]
    if version not in {"7", "8", "9"} or body["configuration_hash"] != config_key(
        "retrieve.contextual", version, configuration
    ):
        raise ValueError("section citation differs from exact retained configuration")
    config = ContextualCandidateConfig.model_validate(configuration)
    source_view_id = retained["origin_unit_id"]
    source = sources[source_view_id]
    mapping = _packet_mapping(contract)
    targets, inventory, complete = _heading_inventory(
        config, source_view_id, sources, documents, mapping
    )
    (report,) = tuple(_reports(body))
    if (
        _wire(report.get("section_sources", ()))
        != _wire([ref.model_dump(mode="json") for ref in config.section_sources])
        or _wire(report.get("section_catalog_sources", ()))
        != _wire([ref.model_dump(mode="json") for ref in config.section_catalog_sources])
        or _wire(report.get("section_targets", ()))
        != _wire(tuple(target.model_dump(mode="json") for target in targets))
        or _wire(report["inventories"]) != _wire([asdict(inventory)])
    ):
        raise ValueError("section heading inventory differs from complete selected native sources")
    outside = frozenset()
    if config.section_catalog_sources:
        broader = config.model_copy(
            update={"section_sources": (*config.section_sources, *config.section_catalog_sources)}
        )
        broader_targets, _, broader_complete = _heading_inventory(
            broader, source_view_id, sources, documents, mapping
        )
        if broader_complete:
            outside = frozenset(target.designator for target in broader_targets)

    scoped = reports[report["section_source_origin_task_id"]]
    upstream = scoped["body"]
    if (
        scoped["method"] != config.source_dependency_method
        or scoped["origin_unit_id"] != source_view_id
        or scoped["project_id"] != retained["project_id"]
        or upstream["source"] != body["source"]
        or upstream["release_id"] != body["release_id"]
        or upstream["operation_version"] not in {"7", "8", "9"}
    ):
        raise ValueError("section citation lacks its exact scoped source report")
    frame = native_source_frame(_retained_review_source_view(source), ())
    pin = record_source_pin(frame)
    nodes = {item["self_ref"]: item for item in source["context"]["items"]}
    for pointer, node in tuple(nodes.items()):
        for index, cell in enumerate(node.get("data", {}).get("table_cells", ())):
            nodes[f"{pointer}/data/table_cells/{index}"] = cell
    key = operation_identity("retrieve.contextual", version, config.model_dump(mode="json"), pin)
    products, contexts, _ = retained_occurrences(
        upstream, nodes, pin, key, config.semantic_types, canonical_producer=True
    )
    carriers = defaultdict(list)
    for product in products:
        marker = explicit_section_citation(product, nodes)
        if marker is not None:
            carriers[product["occurrence_id"]].append((product, marker))
    published = {
        product["contribution_id"]: _wire(product)
        for product in body.get("contributions", ())
        if product["semantic_type"] == "contextual.located_mention"
    }
    if published != {
        product["contribution_id"]: _wire(product)
        for population in carriers.values()
        for product, _ in population
    }:
        raise ValueError("section citation carrier population differs from scoped producer")

    heading_ids = defaultdict(list)
    for target in targets:
        if target.target_id in inventory.target_ids:
            heading_ids[target.designator].append(target.target_id)
    vectors = {v["vector_id"]: EncodedVector(**v) for v in report.get("vectors", ())}
    listed = report.get("candidate_lists", ())
    decided = report.get("relationship_decisions", ())
    lists = {row["occurrence_id"]: row for row in listed}
    decisions = {row["occurrence_id"]: row for row in decided}
    if (
        set(lists) != set(carriers)
        or set(decisions) != set(carriers)
        or len(listed) != len(lists)
        or len(decided) != len(decisions)
    ):
        raise ValueError("section citation list and decision population differs from scoped cues")
    resolutions = []
    expected_proposals = {}
    for occurrence, population in sorted(carriers.items()):
        resolution, witnesses = section_citation_witnesses(
            population,
            heading_ids,
            source_binding=frame.unit_ref,
            scope=config.scope,
            effective_version=config.effective_version,
            complete=complete,
            budget=config.unique_target_budget,
            outside=outside,
        )
        resolutions.append(resolution)
        evidence = defaultdict(set)
        for witness in witnesses:
            evidence[witness.target_id].update(witness.evidence_ids)
        candidate = lists[occurrence]
        channels = {
            ch["channel"]: tuple(
                ChannelHit(h["target_id"], float(h["score"]), tuple(h.get("evidence", ())))
                for h in ch.get("hits", ())
            )
            for ch in candidate["channel_results"]
        }
        if channels.get("witness") != tuple(
            ChannelHit(target, 1.0, tuple(sorted(ids))) for target, ids in sorted(evidence.items())
        ):
            raise ValueError("section citation lacks the complete eligible witness channel")
        vector = vectors[candidate["query_vector_id"]] if candidate.get("query_vector_id") else None
        fused = fuse_candidates(
            occurrence_id=occurrence,
            query=vector,
            inventory=inventory,
            channels=channels,
            budget=config.unique_target_budget,
            channel_budget=config.channel_budget,
            lexical_query=contexts[occurrence][3],
        )
        selected = select_relationships(
            candidates=fused,
            inventory=inventory,
            source_binding=frame.unit_ref,
            scope=config.scope,
            effective_version=config.effective_version,
            constraints=(SECTION_CONSTRAINT,),
            witnesses=witnesses,
            insufficient_reason=resolution["outcome"].replace("_", " "),
        )
        if _wire(candidate) != _wire(asdict(fused)) or _wire(decisions[occurrence]) != _wire(
            asdict(selected)
        ):
            raise ValueError(
                "section citation differs from its exact ranking or directed selection"
            )
        selection_key = operation_identity(
            "contextual-phase-2", "relationship selection", occurrence, (fused.list_id,)
        )
        for row in relationship_contributions(
            selected, [product for product, _ in population], inventory, selection_key
        ):
            expected_proposals[row["contribution_id"]] = _wire(row)
    if _wire(report.get("section_resolutions", ())) != _wire(resolutions):
        raise ValueError("section citation coverage differs from complete inspected population")
    actual_proposals = {
        row["contribution_id"]: _wire(row)
        for row in body.get("contributions", ())
        if row["semantic_type"] == "contextual.relationship"
    }
    if actual_proposals != expected_proposals:
        raise ValueError("section citation proposals differ from the exact selected relationships")


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
    from .contextual_navigation import verify_detached_neighborhood

    for retained in reports.values():
        body = retained.get("body") or {}
        version = body.get("operation_version")
        if retained.get("method") == "retrieve.contextual" and version in ("8", "9"):
            (report,) = tuple(_reports(body))
            verify_detached_neighborhood(report, native_ranks=version == "9")
    relevant = [
        r
        for r in reports.values()
        if r.get("method") == "retrieve.contextual"
        and r.get("body")
        and (
            (r.get("configuration") or {}).get("section_sources")
            or witness_origin_ids(r.get("body") or {}, r.get("configuration") or {})
        )
    ]
    if not relevant:
        return
    sources = {s["source_view_id"]: s for s in _detached_relation(root, manifest, "sources")}
    documents, contracts = {}, {}
    if any(row["configuration"].get("section_sources") for row in relevant):
        documents = {row["id"]: row for row in _detached_relation(root, manifest, "documents")}
        contracts = {
            row["release_id"]: row for row in _detached_relation(root, manifest, "contracts")
        }
    for retained in relevant:
        body = retained["body"]
        if retained["configuration"].get("section_sources"):
            _verify_section_report(
                retained, reports, sources, documents, contracts[body["release_id"]]
            )
            continue
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
                    code = explicit_definition_section(
                        row,
                        nodes,
                        scope=inventory["scope"],
                        effective_version=inventory.get("effective_version"),
                    )
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
                if body.get("operation_version") != "9":
                    continue
                scope, version = inventory["scope"], inventory.get("effective_version")
                section_carriers = [
                    row
                    for row in carriers
                    if row["occurrence_id"] == candidate["occurrence_id"]
                    and explicit_definition_section(
                        row, nodes, scope=scope, effective_version=version
                    )
                    is not None
                ]
                if not section_carriers:
                    continue
                (decision,) = [
                    row
                    for row in report["relationship_decisions"]
                    if row["occurrence_id"] == candidate["occurrence_id"]
                ]
                original_binding = body["source"]
                section_ids = {row["contribution_id"] for row in section_carriers}
                exact_subject_witnesses = []
                for row in section_carriers:
                    subject = explicit_definition_subject(
                        row, nodes, scope=scope, effective_version=version
                    )
                    if subject is None:
                        continue
                    code, _ = subject
                    matching_section = []
                    for target_id in eligible:
                        target, (physical, term, original) = targets[target_id]
                        if (
                            physical.native_content_digest
                            == source["ref"]["native_product"]["content_digest"]
                            and _section(original, term) == code
                        ):
                            matching_section.append((target.reference, term.text))
                    exact_subject_witnesses.extend(
                        section_definition_subject_witnesses(
                            (row,),
                            nodes,
                            matching_section,
                            source_binding=original_binding,
                            scope=scope,
                            effective_version=version,
                        )
                    )
                retained_other_witnesses = []
                for witness in decision.get("witnesses", ()):
                    if witness["relation"] == "defined-by" and (
                        witness["witness_id"].startswith(
                            ("section-definition:", "section-term-definition:")
                        )
                        or section_ids.intersection(witness.get("evidence_ids", ()))
                    ):
                        continue
                    retained_other_witnesses.append(
                        RelationshipWitness(**({"effective_version": None} | witness))
                    )
                config = ContextualCandidateConfig.model_validate(retained["configuration"])
                selected = select_relationships(
                    candidates=replay,
                    inventory=frozen,
                    source_binding=original_binding,
                    scope=scope,
                    effective_version=version,
                    constraints=config.relationship_constraints,
                    witnesses=(*exact_subject_witnesses, *retained_other_witnesses),
                    insufficient_reason="no source-grounded relationship witness",
                )
                if _wire(asdict(selected)) != _wire(decision):
                    raise ValueError("section definition differs from exact source-bound selection")
                selection_key = operation_identity(
                    "contextual-phase-2",
                    "relationship selection",
                    candidate["occurrence_id"],
                    (replay.list_id,),
                )
                actual = {
                    row["contribution_id"]: _wire(row)
                    for row in body["contributions"]
                    if row["semantic_type"] == "contextual.relationship"
                    and row["occurrence_id"] == candidate["occurrence_id"]
                }
                projected = {
                    row["contribution_id"]: _wire(row)
                    for row in relationship_contributions(selected, carriers, frozen, selection_key)
                }
                if projected != actual:
                    raise ValueError(
                        "section definition projection differs from exact retained decision"
                    )

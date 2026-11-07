"""Compare fixed source opportunities with retained and freshly derived products."""

from collections import Counter
from dataclasses import asdict
from hashlib import file_digest
import json
from pathlib import Path

from corpus_structure.methods.contextual_candidates import retained_occurrences
from corpus_structure.methods.scoped_relations import discover_relations
from corpus_structure.semantic.contextual_links import (
    RelationshipConstraint,
    RelationshipWitness,
    select_relationships,
)
from corpus_structure.semantic.contextual_retrieval import (
    Candidate,
    CandidateList,
    ChannelEvidence,
    ChannelHit,
    ChannelResult,
    TargetRepresentation,
    freeze_inventory,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import NativeFrameSource
from corpus_structure.semantic.source_contexts import record_source_pin

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
GS = HERE.parents[1] / "2026-11-06_wce-gs120"
REF = HERE.parent / "source-references/source-reference.json"
INPUTS = {}


def pin(path):
    name = str(path.relative_to(ROOT))
    if name not in INPUTS:
        with path.open("rb") as stream:
            INPUTS[name] = file_digest(stream, "sha256").hexdigest()
    return INPUTS[name]


def load(path):
    pin(path)
    return json.loads(path.read_bytes())


def raw_reports(path, methods, sources):
    pin(path)
    found = {}
    with path.open("rb") as stream:
        for line in stream:
            row = json.loads(line)
            raw = json.loads(row["payload_json"])
            key = (raw.get("method"), raw.get("origin_unit_id"))
            if key[0] in methods and key[1] in sources:
                if key in found:
                    assert found[key] == raw, key
                found[key] = raw
    return found


def frame(source_case, unit_ref):
    packet = ROOT / source_case["packet"]
    pin(packet)
    data = json.loads(packet.read_bytes())
    view = next(v for v in data["views"] if v["passage"]["passage_id"] == source_case["passage_id"])
    source, native = view["source"], view["native_view"]
    assert source == source_case["source"]
    return NativeFrameSource(
        unit_ref=unit_ref,
        text=view["passage"]["text"],
        sentences=(),
        source_view_id=source["source_view_id"],
        native_product=ProductReference(
            task_id=source["native_task_id"],
            product_key=source["native_product_key"],
            content_digest=source["native_content_digest"],
        ),
        section_pointer=native["section_pointer"],
        membership=native["membership"],
        projection_digest=source["projection_digest"],
        recipe_digest=source["recipe_digest"],
        native_context=canonical_bytes(view["native_context"]).decode(),
        version=source["coordinate_version"],
    )


def candidate_list(raw):
    return CandidateList(
        **{
            **raw,
            "candidates": tuple(
                Candidate(
                    **{**c, "channels": tuple(
                        ChannelEvidence(**{**e, "evidence": tuple(e["evidence"])})
                        for e in c["channels"]
                    )}
                )
                for c in raw["candidates"]
            ),
            "channel_results": tuple(
                ChannelResult(
                    r["channel"],
                    tuple(ChannelHit(**{**h, "evidence": tuple(h["evidence"])}) for h in r["hits"]),
                )
                for r in raw["channel_results"]
            ),
        }
    )


def replay_contextual(report):
    body = report["body"]
    results = []
    for op in body["contribution_operations"]:
        if not (raw := op.get("contextual_enrichment")):
            continue
        inventories = {}
        for inventory in raw["inventories"]:
            rebuilt = freeze_inventory(
                tuple(TargetRepresentation(**{**t, "aliases": tuple(t["aliases"])})
                      for t in inventory["targets"]),
                source_selection=inventory["source_selection"],
                scope=inventory["scope"],
                effective_version=inventory.get("effective_version"),
                reliable_type=inventory.get("reliable_type"),
                parent=inventory.get("parent"),
                semantic_targets={
                    member: group["meaning"] for group in inventory["semantic_groups"]
                    for member in group["member_target_ids"]
                },
            )
            assert rebuilt.inventory_id == inventory["inventory_id"]
            inventories[rebuilt.inventory_id] = rebuilt
        lists = {c["list_id"]: candidate_list(c) for c in raw["candidate_lists"]}
        for decision in raw["relationship_decisions"]:
            candidates = lists[decision["candidate_list_id"]]
            witnesses = tuple(
                RelationshipWitness(**{
                    "effective_version": None, **w, "evidence_ids": tuple(w["evidence_ids"]),
                })
                for w in decision["witnesses"]
            )
            assert all(w.basis == "producer_group" for w in witnesses)
            constraints = tuple(
                RelationshipConstraint(**{**c, "relation_kinds": tuple(c["relation_kinds"])})
                for c in decision["constraints"]
            )
            arms = {}
            for name, supplied in (("A", witnesses), ("B", ()), ("A+B", witnesses)):
                result = select_relationships(
                    candidates=candidates,
                    inventory=inventories[candidates.inventory_id],
                    source_binding=decision["source_binding"],
                    scope=decision["scope"],
                    effective_version=decision.get("effective_version"),
                    constraints=constraints,
                    witnesses=supplied,
                    exclusions=frozenset((e["left"], e["right"]) for e in decision["exclusions"]),
                    exclusion_snapshot=decision["exclusion_snapshot"],
                    policy_id=decision["policy_id"],
                    insufficient_reason=decision.get("reason") or "retrieval alone supplies no witness",
                )
                if name == "A+B":
                    assert result.decision_id == decision["decision_id"]
                arms[name] = asdict(result)
            results.append({"candidate_list": asdict(candidates), "arms": arms})
    return results


def contextual(ref):
    folder = GS / "current-contextual-journey/contextual001"
    actual = []
    for path in sorted(folder.glob("source-*/review/reports.jsonl")):
        source_id = int(path.parent.parent.name.split("-")[-1])
        report = raw_reports(path, {"retrieve.contextual"}, {source_id})[
            ("retrieve.contextual", source_id)
        ]
        replay = replay_contextual(report)
        actual.append({
            "source_view_id": source_id,
            "original_run_id": report["origin_run_id"],
            "original_task_id": report["origin_task_id"],
            "fixed_endpoint_replays": replay,
        })
    frame_ref = ref["anchors"]["normal-transform-use"]
    model_raw = raw_reports(
        GS / "current-model-delivery/delivery001/review-sources-002/reports.jsonl",
        {"extract.m1_candidates"}, {117},
    )[("extract.m1_candidates", 117)]
    body = model_raw["body"]
    source = frame(frame_ref, body["unit_key"])
    nodes = {n["self_ref"]: n for n in json.loads(source.native_context)["items"]}
    old = load(folder / "source-117/result.json")
    adjacent_mentions = [
        c for c in body["contributions"]
        if c["semantic_type"] == "source_occurrence" and any(
            a["pointer"] == frame_ref["native_pointer"]
            and a["source_piece"] in {"Z", "standard normal random variable Z"}
            for a in c.get("anchors", ())
        )
    ]
    formula_mentions = [
        c for c in adjacent_mentions if any(
            frame_ref["native_span"][0] <= a["start"] < a["end"] <= frame_ref["native_span"][1]
            for a in c["anchors"]
        )
    ]
    assert adjacent_mentions and not formula_mentions and old["outcome"] == "not_run"
    mentions, _, _ = retained_occurrences(
        {"contributions": adjacent_mentions}, nodes, record_source_pin(source),
        "gs120-r15-offline-retained-mention-control", ("source_occurrence",),
    )
    targets = load(folder / "inventory.json")["target_components"]
    assert not any("standard normal" in t["label"].casefold() for t in targets)
    model_path = GS / "assessment/run161-final-model001/task-1069.json"
    model = load(model_path)["body"]["structural_product"]["definition_components"]["components"]
    assert not any("standard normal" in c["term"]["text"].casefold() for c in model)
    replays = [entry for view in actual for entry in view["fixed_endpoint_replays"]]
    return {
        "fixed_endpoint_arm_inputs": {
            "A": "retained located producer-group witness on unchanged native candidate list",
            "B": "retained retrieval/target candidate evidence only, supplying no qualifying witness",
            "A+B": "both evidence channels on the same candidate membership",
        },
        "fixed_results": actual,
        "fixed_arm_counts": {
            name: dict(Counter(r["arms"][name]["outcome"] for r in replays))
            for name in ("A", "B", "A+B")
        },
        "independent_normal_usage_opportunity": {
            "case_id": "GS120-WCE-R15-NORMAL-USE",
            "independent_target": "normal-z-definition",
            "actual_source_run": model_raw["origin_run_id"],
            "actual_source_task": model_raw["origin_task_id"],
            "actual_adjacent_source_occurrences": adjacent_mentions,
            "exact_formula_source_occurrences": formula_mentions,
            "offline_current_mention_products": mentions,
            "fixed_endpoint_arm_outcomes": {k: "not_run_target_unrepresented" for k in ("A", "B", "A+B")},
            "retained_discovery": old,
            "assessment": "missed target inventory and exact formula use; adjacent non-self mentions located",
        },
    }


def edges(rows):
    participants = {
        row["contribution_id"]: (source_python(row["value"]), row)
        for row in rows if row["semantic_type"] == "structural.located_participant"
    }
    by_endpoints = []
    for row in rows:
        if row["semantic_type"] != "structural.scoped_attachment":
            continue
        value = source_python(row["value"])
        left, left_row = participants[value["subject_id"]]
        right, right_row = participants[value["target_id"]]
        by_endpoints.append({
            "id": row["contribution_id"], "relation": value["relation"],
            "basis": value["basis"],
            "left": left, "right": right,
            "left_occurrence": left_row["occurrence_id"],
            "right_occurrence": right_row["occurrence_id"],
        })
    return by_endpoints

def anchored(participant, source_anchor):
    return (
        participant["source_pointer"] == source_anchor["native_pointer"]
        and [participant["start"], participant["end"]] == source_anchor["projected_span"]
    )

def discovered(case, negative, actual, anchors):
    """Inspect every discovered edge for the source cell, including off-frame endpoints."""
    expected = case["expected"]
    known_wrong = {
        negative["expected"]["excluded_sample_size_header"],
        negative["expected"]["excluded_measure_header"],
    }
    required = {
        ("row_label", expected["row_label"]),
        ("header", expected["sample_size_header"]),
        ("header", expected["measure_header"]),
        ("value_role", expected["measure_header"]),
    }
    judged = []
    for edge in actual:
        if not anchored(edge["left"], anchors[expected["value"]]):
            continue
        targets = [
            name for name in (*case["anchors"], *sorted(known_wrong))
            if anchored(edge["right"], anchors[name])
        ]
        found = {(edge["relation"], name) for name in targets}
        judgment = (
            "supported" if found & required
            else "unsupported" if set(targets) & known_wrong
            else "unassessed"
        )
        judged.append({"judgment": judgment, "source_anchor_ids": targets, **edge})
    found = {
        (edge["relation"], name) for edge in judged if edge["judgment"] == "supported"
        for name in edge["source_anchor_ids"]
    }
    return {
        "counts": dict(Counter(edge["judgment"] for edge in judged)),
        "missing_edges": sorted(required - found),
        "edges": judged,
    }

def typed(ref):
    previous = raw_reports(
        GS / "current-structural-journey/sources002/review-independent/reports.jsonl",
        {"structure.scoped_relations"}, {124, 117, 143},
    )
    results = {}
    anchors = ref["anchors"]
    for view_id, sample in ((124, "dice-cell-8"), (117, "bibliographic-note"), (143, "normal-x-z-bridge")):
        raw = previous[("structure.scoped_relations", view_id)]
        source = frame(anchors[sample], raw["body"]["unit_key"])
        fresh = discover_relations(source, source_work=None)
        results[view_id] = (raw, fresh)

    def match(case, actual, bases):
        expected = case["expected"]
        selected = []
        for e in actual:
            if e["basis"] not in bases or not anchored(e["left"], anchors[case["anchors"][0]]):
                continue
            for name in case["anchors"][1:]:
                if name not in anchors or not anchored(e["right"], anchors[name]):
                    continue
                selected.append({"relation": e["relation"], "target": name, "edge_id": e["id"]})
        if case["judgment"] == "unsupported":
            wrong = {expected["excluded_sample_size_header"], expected["excluded_measure_header"]}
            return {"outcome": "spurious" if any(e["target"] in wrong for e in selected)
                    else "excluded", "exact_edges": selected}
        required = {
            ("row_label", expected["row_label"]),
            ("header", expected["sample_size_header"]),
            ("header", expected["measure_header"]),
            ("value_role", expected["measure_header"]),
        }
        found = {(e["relation"], e["target"]) for e in selected}
        return {
            "outcome": "supported_chain" if required <= found else "partial" if found else "missed",
            "missing_edges": sorted(required - found),
            "exact_edges": selected,
        }

    old, fresh = results[124]
    old_edges = edges(old["body"]["contributions"])
    new_edges = edges(fresh["contributions"])
    dice = []
    discover = []
    cases = {case["id"]: case for case in ref["cases"]}
    for case in ref["cases"]:
        if case["family"] != "scoped_table_composition":
            continue
        arms = {
            "A": match(case, new_edges, {"native_geometry"}),
            "B": match(case, new_edges, {"matched_cue"}),
            "A+B": match(case, new_edges, {"native_geometry", "matched_cue"}),
        }
        prior = match(case, old_edges, {"native_geometry", "matched_cue"})
        dice.append({
            "case_id": case["id"],
            "fixed_endpoints": case["anchors"],
            "independent_judgment": case["judgment"],
            "old_native_discovery": prior,
            "fixed_arms": arms,
        })
        if case["judgment"] == "supported":
            negative_id = f"GS120-WCE-R15-DICE-CROSS-{case['id'].rsplit('-', 1)[-1]}"
            discover.append({
                "case_id": case["id"],
                "old_native_discovery": discovered(case, cases[negative_id], old_edges, anchors),
                "current_offline_discovery": discovered(case, cases[negative_id], new_edges, anchors),
            })
    notes = edges(results[117][1]["contributions"])
    formulas = edges(results[143][1]["contributions"])
    return {
        "fixed_endpoint_arm_inputs": {
            "A": "native layout and literal source edges from current real discovery",
            "B": "matched scoped-role cue edges from same real discovery; share candidate geometry",
            "A+B": "union of exact layout and role-cue evidence, with memberships frozen by source case",
        },
        "dice": dice,
        "unfiltered_dice_discovery": discover,
        "per_source_discovery": {
            str(view): {
                "original_run": raw["origin_run_id"], "original_task": raw["origin_task_id"],
                "original_rows": len(raw["body"]["contributions"]),
                "current_rows": len(fresh["contributions"]), "current_operation": fresh["operation"],
                "formula_diagnostics": fresh["formula_diagnostics"],
            }
            for view, (raw, fresh) in results.items()
        },
        "bibliographic_note": {
            "case_id": "GS120-WCE-R03-BIB-NOTE",
            "note_edges": [
                e["id"] for e in notes if e["relation"] == "note"
                and e["right"]["source_pointer"] == "#/texts/25"
            ],
            "assessment": "bibliographic relationship not emitted; no false table applicability",
        },
        "normal_parameter_chain": {
            "case_id": "GS120-WCE-R03-NORMAL-LOCATION-SCALE",
            "local_declaration_edges": [e for e in formulas if e["relation"] == "declares"],
            "assessment": "selected source synthesis is a source reference; no typed mean/variance proof claimed",
        },
    }


def main():
    ref = load(REF)
    for path, expected in ref["inputs"].items():
        assert pin(ROOT / path) == expected["sha256"], path
    modules = [
        ROOT / "python/corpus-structure/src/corpus_structure" / suffix for suffix in (
        "methods/contextual_candidates.py",
        "semantic/contextual_links.py",
        "semantic/contextual_retrieval.py",
        "methods/scoped_relations.py",
        )
    ]
    baseline = {path: pin(path) for path in modules}
    wce05, wce06 = contextual(ref), typed(ref)
    for path, expected in baseline.items():
        with path.open("rb") as stream:
            assert file_digest(stream, "sha256").hexdigest() == expected, path
    print(json.dumps({
        "protocol": "wce-r15-fixed-endpoint-evidence-1",
        "wce05": wce05,
        "wce06": wce06,
        "sha256_inputs": INPUTS,
        "verification_scope": "offline selected source/candidate replay only",
    }, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

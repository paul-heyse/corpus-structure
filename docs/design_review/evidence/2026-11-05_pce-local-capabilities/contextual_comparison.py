"""Assess immutable registered-producer products against source-first C judgments.

References are read only here, after production. Every mechanism has the same
eligible inventory and final unique K10; retained hybrid channel overfetch stays30.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
MECHANISMS = ("exact_alias", "lexical_baseline", "dense", "hybrid")
BUDGET = 10


def read(path):
    return json.loads(path.read_bytes())


def unique_top(ids, eligible, budget=BUDGET):
    selected = []
    for target_id in ids:
        if target_id not in eligible:
            raise ValueError("retained candidate outside the fixed eligible inventory")
        if target_id not in selected:
            selected.append(target_id)
        if len(selected) == budget:
            break
    return selected


def retrieval_assessment(ids, permitted, eligible, *, produced):
    matches = sorted(set(ids) & permitted)
    if not permitted:
        state = "reference_has_no_permissible_target"
    elif not permitted & eligible:
        state = "inventory_gap"
    elif not produced:
        state = "retrieval_not_produced"
    elif matches:
        state = "hit"
    else:
        state = "miss_with_eligible_permissible_target"
    return dict(target_ids=ids, unique_target_count=len(ids), permissible_hits=matches,
                permissible_ranks={key: ids.index(key) + 1 for key in matches}, outcome=state)


def selector_assessment(decision, permitted, phase):
    if decision is None:
        return dict(outcome="not_produced", operation=phase)
    targets = sorted({w["target_id"] for w in decision["alternatives"] if w["relation"] == "denotes"})
    if decision["outcome"] == "selected":
        state = "correct_selected" if targets and set(targets) <= permitted else "wrong_selected"
    elif decision["outcome"] == "ambiguous":
        state = "ambiguous_with_permissible" if set(targets) & permitted else "ambiguous_without_permissible"
    elif decision["outcome"] == "insufficient_evidence":
        state = "abstained"
    else:
        state = "other_declared_outcome"
    return dict(outcome=state, typed_outcome=decision["outcome"], target_ids=targets,
                decision=decision, operation=phase)


def compare_profile(rows, packet, reference, profile_name):
    if len(rows) != 1:
        raise ValueError("comparison requires exactly one registered contextual task per profile")
    body = rows[0]["body"]
    if body["method"] != "retrieve.contextual":
        raise ValueError("products did not originate from the declared registered method")
    reports = [op["contextual_enrichment"] for op in body["contribution_operations"]
               if "contextual_enrichment" in op]
    if len(reports) != 1:
        raise ValueError("expected exactly one typed contextual report")
    report = reports[0]
    if len(report["profiles"]) != 1:
        raise ValueError("one actual encoder profile is required per run")
    model = report["profiles"][0]["model"]
    if (profile_name == "e5" and "e5" not in model.lower()) or (
        profile_name == "qwen" and "qwen" not in model.lower()
    ):
        raise ValueError("profile label differs from retained encoder model")
    inventory = {inv["inventory_id"]: inv for inv in report["inventories"]}
    if len(inventory) != 1:
        raise ValueError("cohort comparison expects one shared frozen inventory")
    contributions = {c["item_key"]: c for c in body["contributions"]
                     if c["semantic_type"] == "contextual.supplied_mention"}
    lists = {row["occurrence_id"]: row for row in report["candidate_lists"]}
    decisions = {row["occurrence_id"]: row for row in report["relationship_decisions"]}
    if len(lists) != len(report["candidate_lists"]) or len(decisions) != len(report["relationship_decisions"]):
        raise ValueError("more than one list or decision was retained for the same declared occurrence")
    vectors = {row["object_id"]: row for row in report["vectors"]}
    references = {case["case_id"]: case for case in reference["cases"]}
    expected_cases = {case["case_id"] for case in packet["cases"]}
    if set(references) != expected_cases or set(contributions) != expected_cases:
        raise ValueError("reference/product selected-case population differs from the source packet")
    output = []
    for case in packet["cases"]:
        cid = case["case_id"]
        product = contributions[cid]
        anchors = product["anchors"]
        if len(anchors) != 1 or any(anchors[0].get(key) != case[key]
            for key in ("pointer", "start", "end")) or anchors[0]["source_piece"] != case["mention"]:
            raise ValueError("product occurrence differs from the independently declared source case")
        ref = references[cid]
        if ref["source_pointer"] != case["pointer"] or any(
            ref[key] != case[key] for key in ("start", "end", "mention")
        ):
            raise ValueError("reference source occurrence differs from selected input")
        if any(product["pin"][key] != packet["physical_pin"][key]
               for key in ("product_key", "product_digest", "projection_digest")):
            raise ValueError("actual product physical source differs from independent reference input")
        permitted = set(ref["permissible_target_ids"])
        occurrence = product["occurrence_id"]
        candidate_list = lists.get(occurrence)
        inv = inventory[candidate_list["inventory_id"]] if candidate_list else next(iter(inventory.values()))
        eligible = {target["target_id"] for target in inv["targets"]}
        if eligible != {target["target_id"] for target in packet["inventory"]}:
            raise ValueError("baseline eligible inventory differs from the declared20-target source input")
        channels = {row["channel"]: row["hits"] for row in candidate_list["channel_results"]} if candidate_list else {}
        query_vector = vectors.get(occurrence, {})
        phases = [op for op in body["contribution_operations"] if "contextual_enrichment" not in op
                  and (query_vector.get("vector_id") in op.get("computation_dependencies", ()) or
                       (candidate_list and candidate_list["list_id"] in op.get("computation_dependencies", ())))]
        selection = next((op for op in phases if op["question"] ==
                          "contextual denotation selection for supplied occurrence"), None)
        if candidate_list and (candidate_list["unique_target_budget"] != BUDGET or
                               candidate_list["channel_budget"] != 30 or
                               candidate_list["eligible_target_count"] != len(eligible)):
            raise ValueError("retained retrieval budgets or eligible population differ from the experiment")
        alias = [hit["target_id"] for hit in channels.get("alias", ())]
        lexical = [hit["target_id"] for hit in channels.get("lexical", ())]
        dense = [hit["target_id"] for hit in channels.get("dense", ())]
        hybrid = [candidate["target_id"] for candidate in candidate_list["candidates"]] if candidate_list else []
        ids = dict(exact_alias=unique_top(alias, eligible),
                   lexical_baseline=unique_top((*alias, *lexical), eligible),
                   dense=unique_top(dense, eligible), hybrid=unique_top(hybrid, eligible))
        if len(hybrid) != len(ids["hybrid"]) or len(hybrid) > BUDGET:
            raise ValueError("retained hybrid is not a unique bounded list")
        output.append(dict(case_id=cid, source=dict(pointer=case["pointer"], start=case["start"],
            end=case["end"], mention=case["mention"], contribution_id=product["contribution_id"],
            occurrence_id=occurrence), permissible_target_ids=sorted(permitted),
            inventory=dict(inventory_id=inv["inventory_id"], eligible_target_ids=sorted(eligible),
                permissible_present=sorted(permitted & eligible),
                permissible_missing=sorted(permitted - eligible),
                coverage="none" if not permitted & eligible else "full" if permitted <= eligible else "partial"),
            mechanisms={name: retrieval_assessment(value, permitted, eligible,
                          produced=candidate_list is not None) for name, value in ids.items()},
            selector=selector_assessment(decisions.get(occurrence), permitted, selection),
            retained_candidate_list=candidate_list, raw_channel_results=channels,
            operation_phases=phases,
            reference_limits=ref.get("insufficient_context_reasons", ())))
    return dict(selected_task_id=rows[0]["id"], release_id=body["release_id"],
                profile=report["profiles"][0], registry_id=report["curated_registry_id"],
                cases=output,
                mechanism_counts={name: dict(Counter(case["mechanisms"][name]["outcome"]
                    for case in output)) for name in MECHANISMS},
                selector_counts=dict(Counter(case["selector"]["outcome"] for case in output)))


def paired_baseline_cases(profile):
    result = {}
    for mechanism in ("dense", "hybrid"):
        cases = {}
        for case in profile["cases"]:
            baseline = case["mechanisms"]["lexical_baseline"]["outcome"]
            alternative = case["mechanisms"][mechanism]["outcome"]
            if baseline == "inventory_gap" or alternative == "inventory_gap":
                group = "inventory_gap"
            elif baseline == "retrieval_not_produced" or alternative == "retrieval_not_produced":
                group = "retrieval_not_produced"
            else:
                group = ("lexical_hit" if baseline == "hit" else "lexical_miss") + "__" + (
                    "alternative_hit" if alternative == "hit" else "alternative_miss")
            cases.setdefault(group, []).append(case["case_id"])
        result[mechanism] = {key: dict(count=len(value), case_ids=value) for key, value in cases.items()}
    return result


def main(args):
    packet, reference = read(args.packet), read(args.reference)
    if len(packet["cases"]) != 17 or len(packet["inventory"]) != 20:
        raise ValueError("comparison is limited to the declared17-case/20-target development cohort")
    packet_digest = sha256(args.packet.read_bytes()).hexdigest()
    if reference["packet_sha256"] != packet_digest:
        raise ValueError("independent C is not bound to the exact selected source packet")
    profiles = {name: compare_profile(read(path), packet, reference, name)
                for name, path in (("e5", args.e5), ("qwen", args.qwen))}
    if profiles["e5"]["registry_id"] != profiles["qwen"]["registry_id"]:
        raise ValueError("baseline profiles consumed different curated registries")
    if profiles["e5"]["release_id"] != profiles["qwen"]["release_id"]:
        raise ValueError("profile comparison consumed different released contracts")
    for left, right in zip(profiles["e5"]["cases"], profiles["qwen"]["cases"], strict=True):
        if left["case_id"] != right["case_id"] or left["inventory"] != right["inventory"]:
            raise ValueError("profile comparison changed the case or eligible inventory")
    result = dict(protocol="contextual-equal-budget-comparison-1", scope="17 selected supplied mentions only",
        final_unique_budget=BUDGET, hybrid_retained_per_channel_budget=30,
        lexical_baseline_policy="Exact-alias native rank first; then lexical native rank; stable deduplication; first10 unique eligible targets.",
        score_standing="Raw native channel scores and RRF ranks; no calibrated probability.",
        authority="Private retrieval/selector assessment; no canonical identity or source-truth admission.",
        population_inference=False, source_discovery_assessed=False,
        input_sha256={str(path): sha256(path.read_bytes()).hexdigest()
                      for path in (args.packet, args.reference, args.e5, args.qwen)},
        script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(), profiles=profiles,
        paired_lexical_baseline={name: paired_baseline_cases(value) for name, value in profiles.items()})
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(dict(outcome="passed", artifact=str(args.output),
                         selected_cases=len(packet["cases"]),
                         mechanism_counts={key: value["mechanism_counts"] for key, value in profiles.items()},
                         selector_counts={key: value["selector_counts"] for key, value in profiles.items()})))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, default=HERE / "raw/contextual-source-author-packet-001.json")
    parser.add_argument("--reference", type=Path, default=HERE / "raw/contextual-author-C-001.json")
    for name in ("e5", "qwen", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    main(parser.parse_args())

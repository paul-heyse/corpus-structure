"""Classify the finalized DDO census using metadata and owning source contracts only.

No database connection, artifact body, reference answer, provider import or prior
evidence write. New output is exclusive so another observation cannot replace it.
"""

from __future__ import annotations

import hashlib
import json
import stat
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SOURCE = "python/corpus-structure/src/corpus_structure/"
EVIDENCE = "docs/design_review/evidence/"


def state(path: Path) -> dict:
    try:
        value = path.lstat()
    except FileNotFoundError:
        return {"state": "missing"}
    return {
        "state": "symlink_unresolved" if stat.S_ISLNK(value.st_mode) else "present",
        "bytes": value.st_size,
        "kind": "directory" if stat.S_ISDIR(value.st_mode) else "file",
    }


def member(base: Path, name: str, role: str, digest=None) -> dict:
    path = base / name
    return {"path": str(path), "role": role, "declared_sha256": digest, **state(path)}


def classify(path: Path, value: dict) -> tuple[str, str, list[dict]]:
    """Use identified owner schemas; do not search arbitrary JSON for path-like strings."""
    members = []
    if value.get("version") == "contribution-selection-export-1":
        members.append(member(path.parent, value["file"], "bounded selected items", value["sha256"]))
        return "bounded_contribution_export", SOURCE + "serve/contributions.py:486", members
    if "semantic_release" in value or set(value) == {"source", "source_release"}:
        if isinstance(value.get("artifacts"), str):
            artifact = member(ROOT, value["artifacts"], "declared provider model artifact directory")
            if "archive_study" in value and "recipe" not in value:
                artifact["required_for_retained_reader"] = False
                artifact["role"] = "inactive provider-model location hint in archive-overlay manifest"
                artifact["reason"] = (
                    "freeze_book_shadow.py:253-260 skips ChandraRuntime in archive-overlay mode; "
                    "group_shadow_compare.py retained comparison does not consume artifacts field. "
                    "Missing provider-model directory is not missing source/archive custody."
                )
            members.append(artifact)
        campaign_owner = ROOT / EVIDENCE / "2026-11-08_chandra-execution"
        cohort = value.get("mixed_cohort", {})
        for key in ("definition", "receipt"):
            if isinstance(cohort.get(key), str):
                members.append(member(campaign_owner, cohort[key], "mixed cohort " + key,
                                      cohort.get(key + "_sha256")))
        return "visual_campaign_custody", EVIDENCE + "2026-11-08_chandra-execution/group_shadow_compare.py:378", members
    if value.get("protocol") == "gs120-native-output-capture-1":
        for task in value.get("tasks", []):
            if isinstance(task.get("raw_file"), str):
                members.append(member(path.parent, task["raw_file"], "retained task envelope",
                                      task.get("raw_sha256")))
        return "native_output_capture_account", EVIDENCE + "2026-11-06_wce-gs120/assessment/characterize_outputs.py:244", members
    if {"dependencies", "libraries", "ontology_sources", "sources"} <= value.keys():
        return "prepared_release_manifest", SOURCE + "semantic/prepare.py:886", members
    if "execution_compiler_version" in value and "implementation_inputs" in value:
        return "archived_runtime_manifest", SOURCE + "semantic/runtime_bindings.py:144", members
    if {"entry", "schema_digest", "release_manifest_digest"} <= value.keys():
        members.append(member(path.parent, value["entry"], "portable schema", value["schema_digest"]))
        return "portable_interpretation_contract", SOURCE + "semantic/portable_interpretation.py:15", members
    if "frame_owner" in value and "input_digests" in value:
        for name, digest in value["input_digests"].items():
            members.append(member(path.parent, name, "frozen author input", digest))
        return "source_only_author_packet", EVIDENCE + "2026-11-01_pdf-current-consumers/author_source_references.py:313", members
    if "2026-11-04_m1-independent-references" in path.parts:
        owner = ROOT / EVIDENCE / "2026-11-04_m1-independent-references"
        if path.parent.name == "author-A-v3":
            input_root = owner / "freeze-002"
        else:
            input_root = owner
        for direction, base in (("inputs", input_root), ("outputs", path.parent)):
            items = value.get(direction)
            if isinstance(items, dict):
                for name, digest in items.items():
                    members.append(member(base, name, "declared author " + direction, digest))
        for artifact in value.get("artifacts", []):
            if isinstance(artifact, dict) and isinstance(artifact.get("path"), str):
                members.append(member(path.parent, artifact["path"], "frozen contract artifact",
                                      artifact.get("sha256")))
        if "sets" in value:
            for entry in value["sets"]:
                if isinstance(entry.get("directory"), str):
                    members.append(member(path.parent, entry["directory"], "frozen origin packet directory"))
        return "independent_reference_custody", EVIDENCE + "2026-11-04_m1-independent-references/register_passes.py:25", members
    if "2026-11-11_text-characterization-assessment" in path.parts or "2026-11-12_bep-tc-qualification" in path.parts:
        for key in ("private_material_root", "protected_payload_location"):
            if isinstance(value.get(key), str):
                members.append(member(ROOT, value[key], "declared protected custody directory"))
        return "protected_panel_custody", EVIDENCE + "2026-11-12_bep-tc-qualification/helpers/prepare_choice_supplement.py", members
    if {"parent_sha256", "pages", "sources"} == value.keys():
        for name in ("pages.jsonl", "comparison.jsonl"):
            members.append(member(path.parent, name, "whole-book review account"))
        return "whole_book_review_account", EVIDENCE + "2026-11-08_nce-full-book/review_packets.py:173", members
    if "2026-10-31_pdf-child-ocr" in path.parts:
        return "retained_source_fixture_manifest", EVIDENCE + "2026-10-31_pdf-child-ocr/prepare_sources.py", members
    if "2026-11-03_m1-population" in path.parts:
        return "source_population_account", EVIDENCE + "2026-11-03_m1-population/inventory.py", members
    return "retained_evidence_metadata", str(path.parent), members


def main() -> None:
    inventory_path = HERE / "raw/inventory.json"
    summary_path = HERE / "raw/summary.json"
    inventory = json.loads(inventory_path.read_bytes())
    summary = json.loads(summary_path.read_bytes())
    all_manifests = {item["path"]: item for item in inventory["external"]["manifests"]}
    selected = [item for item in all_manifests.values()
                if item["classification"] == "sealed_pending_consumer"]
    dispositions = []
    for prior in selected:
        path = ROOT / prior["path"]
        raw = path.read_bytes()
        if len(raw) > 16_777_216:
            raise RuntimeError("metadata bound exceeded")
        value = json.loads(raw)
        digest = hashlib.sha256(raw).hexdigest()
        kind, reader, members = classify(path, value)
        own_state = state(path.parent)
        dispositions.append({
            "manifest": prior["path"], "prior_metadata_sha256": prior["metadata"].get("sha256"),
            "current_metadata_sha256": digest,
            "unchanged_since_census": digest == prior["metadata"].get("sha256"),
            "classification": "preserve_sealed", "kind": kind, "reader_or_custodian": reader,
            "custody_root": str(path.parent), "custody_root_state": own_state,
            "action": "Retain whole original directory, manifest and declared outbound custody; no rewrite, regeneration or disposal.",
            "declared_members": members,
            "scope": "Original declared selected/campaign/evidence scope; no upgrade to detached replay or scientific completeness.",
        })
    historical = []
    for reference in summary["external_or_historical_identity_references"]:
        prior = all_manifests[reference["manifest"]]
        path = ROOT / reference["manifest"]
        if prior["kind"] == "export":
            reason = "Archived captured tabular binding provenance; ordinary file inspection consumes declared relation files and schemas, not active database membership."
            authority = SOURCE + "serve/export.py:33"
        elif prior["kind"] == "review":
            reason = "Historical selected-source-closure run selection in a retained review bundle; original declared relations remain its custody. No live run import is required to retain the bundle."
            authority = SOURCE + "serve/review_bundle.py:3240"
        else:
            reason = "Source-only frozen author-packet release provenance; native export was already captured into declared immutable input members. Retain that original packet interpretation."
            authority = EVIDENCE + "2026-11-01_pdf-current-consumers/author_source_references.py:313"
        historical.append({**reference, "classification": "preserve_sealed_historical",
                           "missing_required_source_or_archive": "not_established_by_absent_active_id",
                           "reason": reason, "authority": authority,
                           "custody_root": str(path.parent), "custody_root_state": state(path.parent)})
    missing = [{"manifest": item["manifest"], **entry} for item in dispositions
               for entry in item["declared_members"] if entry["state"] != "present"]
    result = {
        "observed_at": datetime.now(UTC).isoformat(),
        "baseline_record": "2026-11-12_ddo-preservation-closure/ddo.preservation-root-inventory",
        "inputs": {str(path.relative_to(HERE)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in (inventory_path, summary_path)},
        "method": "Read only finalized census metadata, selected manifest metadata and owning source contracts; lstat declared members/outbound directories, never source/answer/result/contract bodies.",
        "manifest_dispositions": dispositions, "historical_identifier_dispositions": historical,
        "counts": {"pending_manifests": len(dispositions), "kinds": dict(Counter(item["kind"] for item in dispositions)),
                   "historical_reference_occurrences": len(historical),
                   "historical_manifests": len({item["manifest"] for item in historical}),
                   "declared_member_checks": sum(len(item["declared_members"]) for item in dispositions),
                   "metadata_changed_since_census": sum(not item["unchanged_since_census"] for item in dispositions)},
        "missing_or_symlink_declared_members": missing,
        "DDO00": {"scope": "Exact acquired database plus configured local manifest/evidence owners and recognized declared outbound custody, using conservative preserve-sealed disposition.",
                  "remaining_blockers": [],
                  "completion_basis": "All selected roots have a preservation action; unknown or obsolete interpretation stays sealed. Incomplete workspace recovery intent does not require a disposal decision: retain/quarantine all. Historical IDs are provenance, not automatically live database prerequisites."},
        "DDO11": {"follow_up": [
            "Reacquire/freeze actual target/source and fence writers before effects; this census is a dated observation.",
            "Prepare original/archive/evidence recovery material and verify required bytes/readers at the frozen predecessor.",
            "Preserve incomplete workspaces and unsettled 0a78c71ce1a949e38e906c9c5392c1f3; settle only with established authority/evidence.",
            "Choose reviewed correspondence only if actual addresses change; preserve original protected questions/answers.",
            "If adoption requires replay/import of a historical scope, establish that exact legacy reader/interpretation; no guarantee is inferred from file existence."]},
        "limits": "No arbitrary unrecorded filesystem negative proof; unrecorded external deliveries lie outside declared-owner inventory. No body/hash/replay verification. An unknown metadata field is not interpreted as an inferred reference. Concrete subsequently declared required custody joins the adoption freeze.",
    }
    required_missing = [item for item in missing if item.get("required_for_retained_reader", True)]
    if required_missing:
        result["DDO00"]["remaining_blockers"] = required_missing
    result["supersedes_interpretation"] = (
        "raw/classification-followup.json recorded two absent artifacts paths before "
        "checking their archive-overlay reader branch. That earlier observation remains intact."
    )
    output = HERE / "raw/classification-reconciled.json"
    with output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({**result["counts"], "missing_or_symlink_declared_members": len(missing),
                      "missing_required_declared_members": len(required_missing)}))


if __name__ == "__main__":
    main()

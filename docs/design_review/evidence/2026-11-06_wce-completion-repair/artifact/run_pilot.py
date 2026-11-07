"""Evaluate a current artifact file-page on the frozen source-authored pair frame."""

import argparse
from collections import Counter
from hashlib import sha256
from importlib.metadata import version
import json
from pathlib import Path

from corpus_structure.evaluate.artifact_pilot import ArtifactPairJudgment, evaluate_artifact_pilot
from corpus_structure.methods.artifact_identity import ArtifactIdentityConfig, ArtifactIdentityMethod
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.structural_products import ExternalSourceRef, StructuralProductReport

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
DEFAULT_FRAME = HERE.parent / "source-references/source-reference.json"


def frozen_json(path):
    raw = path.read_bytes()
    return json.loads(raw), sha256(raw).hexdigest()


def artifact_nomination_refs(scoped, verified_bundle):
    """Select the actual independently produced relation refs from ordinary scoped receipts."""
    completed, _ = frozen_json(scoped / "completed.json")
    raw_refs, _ = frozen_json(scoped / "contribution-predecessors.json")
    refs = {
        reference.contribution_id: reference
        for raw in raw_refs
        for reference in (RetainedContributionRef.model_validate(raw),)
    }
    if len(refs) != len(raw_refs):
        raise ValueError("retained scoped contribution references repeat")
    selected = set()
    with (verified_bundle / "reports.jsonl").open("rb") as stream:
        for line in stream:
            raw = json.loads(json.loads(line)["payload_json"])
            body = raw.get("body") or {}
            if body.get("method") != "structure.scoped_relations":
                continue
            for row in body.get("contributions", ()):
                if (
                    row["semantic_type"] == "structural.scoped_attachment"
                    and source_python(row["value"])["relation"] == "artifact_reference_target"
                ):
                    reference = refs[row["contribution_id"]]
                    if (
                        reference.origin_task_id != raw["origin_task_id"]
                        or reference.runtime_fingerprint != raw["runtime_fingerprint"]
                        or reference.release_id != body["release_id"]
                    ):
                        raise ValueError("nomination raw producer differs from exact scoped reference")
                    selected.add(row["contribution_id"])
    references = tuple(refs[key] for key in sorted(selected))
    if any(
        (ref.run_id, ref.cut_id, ref.release_id)
        != (completed["run_id"], completed["cut_id"], completed["release_id"])
        for ref in references
    ):
        raise ValueError("nomination reference belongs to another selected cut")
    return references


def bind_anchor(report, packets, anchor, role):
    source = ExternalSourceRef.model_validate(anchor["source"])
    packet = packets[anchor["packet"]]
    view = next(
        v for v in packet["views"]
        if v["passage"]["passage_id"] == anchor["passage_id"]
        and v["source"] == anchor["source"]
    )
    node = next(
        item for item in view["native_context"]["items"]
        if item["self_ref"] == anchor["native_pointer"]
    )
    lo, hi = anchor["native_span"]
    if node[anchor["native_field"]][lo:hi] != anchor["quote"]:
        raise ValueError("source-first artifact anchor no longer matches pinned native literal")
    span = anchor["projected_span"]
    if span is None:
        return None, "native_only_source_opportunity"
    if source not in report.inputs.sources:
        return None, "source_outside_producer_selection"
    start, end = span
    if view["passage"]["text"][start:end] != anchor["quote"]:
        raise ValueError("source-first artifact anchor no longer matches pinned projection")
    product = report.artifact_identity
    assert product is not None
    found = {
        record.contribution_id
        for record in product.records
        if record.artifact.occurrence_role == role
        and any(
            citation.source_ref == source.identity
            and citation.passage_id == anchor["passage_id"]
            and citation.source_pointer == anchor["native_pointer"]
            and citation.start == start
            and citation.end <= end
            and anchor["quote"].startswith(citation.text)
            for citation in record.citations
        )
    }
    if len(found) > 1:
        raise ValueError("independent artifact anchor ambiguously binds emitted records")
    if found:
        return next(iter(found)), "captured"
    return None, "projected_source_opportunity_not_captured"


def evaluate(reference, artifact_page, configuration):
    frame, frame_sha = frozen_json(reference)
    page, page_sha = frozen_json(artifact_page)
    config_raw, config_sha = frozen_json(configuration)
    if frame["protocol"] != "wce-gs120-audit-repair-source-reference-1":
        raise ValueError("expected the frozen source-first WCE repair frame")
    if (
        config_raw["method"] != ArtifactIdentityMethod.name
        or config_raw["version"] != ArtifactIdentityMethod.version
    ):
        raise ValueError("expected an actual current registered artifact producer receipt")
    cfg = ArtifactIdentityConfig.model_validate(config_raw["config"])
    if len(page["reports"]) != 1 or len(page["task_ids"]) != 1:
        raise ValueError("expected one exact actual artifact report and producing task")
    report = StructuralProductReport.model_validate(page["reports"][0])
    product = report.artifact_identity
    if product is None or report.inputs != cfg.inputs or product.policy != cfg.policy:
        raise ValueError("artifact report does not match its declared producing configuration")

    packets = {}
    pages = set()
    for rel_path, pin in frame["inputs"].items():
        packet, digest = frozen_json(ROOT / rel_path)
        if digest != pin["sha256"] or packet["parent_pdf_sha256"] != pin["parent_sha256"]:
            raise ValueError(f"source-authored input changed: {rel_path}")
        packets[rel_path] = packet
        pages.update(packet["parent_physical_pages"])
    if pages != set(range(191, 311)):
        raise ValueError("artifact assessment requires the pinned GS120 page frame")

    bindings = {}
    captured = []
    opportunities = []
    for case in frame["artifact_lineage_pairs"]:
        endpoint_ids, capture = [], []
        for role in ("reference", "caption"):
            anchor_id = case[f"{role}_anchor"]
            key = (anchor_id, role)
            if key not in bindings:
                bindings[key] = bind_anchor(report, packets, frame["anchors"][anchor_id], role)
            identity, state = bindings[key]
            endpoint_ids.append(identity)
            capture.append({"anchor": anchor_id, "role": role, "record_id": identity, "state": state})
        if all(endpoint_ids):
            left, right = sorted(endpoint_ids)
            captured.append(
                ArtifactPairJudgment(
                    case_id=case["id"], judgment=case["judgment"], left=left, right=right
                )
            )
        opportunities.append({**case, "capture": capture})
    result = evaluate_artifact_pilot(
        product, tuple(captured), exclusions=cfg.exclusions, title_threshold=cfg.title_threshold
    )
    return {
        "protocol": "wce-gs120-artifact-pilot-repair-1",
        "source_reference": {"path": str(reference), "sha256": frame_sha},
        "artifact_page": {"path": str(artifact_page), "sha256": page_sha},
        "configuration": {"path": str(configuration), "sha256": config_sha},
        "provider": {"splink": version("splink"), "duckdb": version("duckdb")},
        "producing_page": {k: page[k] for k in ("run_id", "cut_id", "task_ids", "release_id")},
        "records": len(product.records),
        "independent_judgments": dict(Counter(x["judgment"] for x in opportunities)),
        "captured_judgments": dict(Counter(x.judgment for x in captured)),
        "opportunities": opportunities,
        "evaluation": result,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=DEFAULT_FRAME)
    parser.add_argument("--artifact-page", type=Path, required=True)
    parser.add_argument("--configuration", type=Path, required=True)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=False)
    try:
        result = evaluate(args.reference, args.artifact_page, args.configuration)
        (args.destination / "result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        )
    except Exception as exc:
        (args.destination / "failure.json").write_text(
            json.dumps({"error": type(exc).__name__, "message": str(exc)}, indent=2) + "\n"
        )
        raise
    print(json.dumps({k: result[k] for k in ("records", "independent_judgments", "captured_judgments")}))


if __name__ == "__main__":
    main()

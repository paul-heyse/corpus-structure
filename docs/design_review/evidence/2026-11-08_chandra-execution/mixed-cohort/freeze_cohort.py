"""Freeze exact managed source selections for all mixed-cohort arms."""

import argparse
import json
import subprocess
from pathlib import Path

from corpus_structure.semantic.visual_routing import VisualRouteReport
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin


def _ci(*args):
    return json.loads(subprocess.check_output(["uv", "run", "ci", *args, "--json"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=int)
    parser.add_argument("semantic_release")
    parser.add_argument("realization")
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    expected = json.loads((Path(__file__).parent / "cohort.json").read_bytes())
    by_digest = {row["input_sha256"]: row for row in expected["inputs"]}
    catalog = _ci("source", "native-products", str(args.run))
    products = {}
    for row in catalog:
        if row["product_key"] != "integrated":
            continue
        if row["release_id"] != args.semantic_release:
            raise ValueError("a cohort product was published by another release")
        scope = (
            str(args.run),
            "--producing-task",
            str(row["task_id"]),
            "--product",
            row["product_key"],
            "--native-digest",
            row["content_digest"],
        )
        header = _ci("source", "inspect", *scope, "--native-view", "products")
        if header["outcome"] != "source_ready" or len(header["rows"]) != 1:
            raise ValueError("a cohort product has no qualified source header")
        artifact = header["rows"][0]["artifact_digest"]
        if artifact not in by_digest or artifact in products:
            raise ValueError("duplicate or out-of-cohort input digest")
        products[artifact] = scope
    if missing := by_digest.keys() - products.keys():
        raise ValueError(f"cohort missing integrated inputs {[by_digest[p]['input'] for p in missing]}")

    args.output.mkdir(exist_ok=False)
    for artifact, row in by_digest.items():
        scope = products[artifact]
        report = VisualRouteReport.model_validate(
            _ci("source", "visual-route", *scope, "--limit", str(len(row["physical_page_map"])))
        )
        source = VisualEvidencePin(
            run_id=args.run, task_id=int(scope[2]), product_key=scope[4], content_digest=scope[6]
        )
        expected_pages = list(map(int, row["physical_page_map"]))
        if (
            report.source != source
            or report.page_count != len(expected_pages)
            or [page.page_no for page in report.pages] != expected_pages
        ):
            raise ValueError(f"cohort route report differs from frozen pages for {row['input']}")
        all_page = [{"page_no": page} for page in expected_pages]
        requests = {}
        for page in report.pages:
            if page.action != "recognize":
                continue
            for reason in page.reasons:
                if reason.code in {"incumbent_structure", "unassessed"}:
                    continue
                crop = reason.crop
                request = {"page_no": page.page_no, **(crop.model_dump() if crop else {})}
                requests[json.dumps(request, sort_keys=True)] = request
        selections = {
            json.dumps(request, sort_keys=True): request
            for request in [*all_page, *requests.values()]
        }
        manifest = {
            "source": source.model_dump(),
            "semantic_release": args.semantic_release,
            "realization": args.realization,
            "artifacts": str(args.artifacts),
            "cohort": row,
            "routing": report.model_dump(),
            "arms": {
                "incumbent_only": [],
                "explicit": all_page if row["role"] == "development" else [],
                "selective": list(requests.values()),
                "all_page_shadow": all_page,
            },
            "selections": list(selections.values()),
        }
        output = args.output / (Path(row["input"]).stem + ".json")
        output.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()

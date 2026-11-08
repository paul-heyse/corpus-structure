"""Freeze exact managed source selections for all mixed-cohort arms."""

import argparse
import json
import subprocess
from pathlib import Path

from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.visual_routing import read_visual_routes
from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin
from corpus_structure.settings import Settings


def _ci(*args):
    return json.loads(subprocess.check_output(["uv", "run", "ci", *args, "--json"]))


def _cohort_products(conn, catalog, by_digest, *, run, release):
    products = {}
    for row in catalog:
        if row["product_key"] != "integrated":
            continue
        if row["release_id"] != release:
            raise ValueError("a cohort product was published by another release")
        source = VisualEvidencePin(
            run_id=run, task_id=row["task_id"],
            product_key=row["product_key"], content_digest=row["content_digest"]
        )
        header = inspect_native_source(
            conn, NativeSourceRequest(**source.model_dump(), view="products")
        )
        if header.outcome != "source_ready" or len(header.rows) != 1:
            raise ValueError("a cohort product has no qualified source header")
        artifact = header.rows[0]["artifact_digest"]
        if artifact not in by_digest or artifact in products:
            raise ValueError("duplicate or out-of-cohort input digest")
        products[artifact] = source
    if missing := by_digest.keys() - products.keys():
        raise ValueError(f"cohort missing integrated inputs {[by_digest[p]['input'] for p in missing]}")
    return products


def _cohort_manifests(conn, products, by_digest, args):
    for artifact, row in by_digest.items():
        source = products[artifact]
        expected_pages = list(map(int, row["physical_page_map"]))
        report = read_visual_routes(conn, source, first=1, limit=len(expected_pages))
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
        yield Path(row["input"]).stem, manifest


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
    # Reuse the CLI owners with one read engine and one immutable snapshot.
    with (
        open_runtime_engine(Settings(), "chandra-cohort-freeze", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        products = _cohort_products(
            conn, catalog, by_digest, run=args.run, release=args.semantic_release
        )
        manifests = dict(_cohort_manifests(conn, products, by_digest, args))
    args.output.mkdir(exist_ok=False)
    for name, manifest in manifests.items():
        (args.output / f"{name}.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()

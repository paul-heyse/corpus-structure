"""Resume only read/export of completed native candidate runs; no provider work."""

import argparse
import json
from pathlib import Path

from sqlalchemy import text

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.contributions import ContributionRequest, export_contribution_selection, serve_contributions
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("candidate_directory")
args = parser.parse_args()
root = HERE / args.candidate_directory
reports = []
for run_path in root.glob("*/run.json"):
    directory = run_path.parent
    run = json.loads(run_path.read_bytes())
    with open_runtime_engine(Settings(), "wce-resume-candidate-capture", purpose="read") as engine, read_snapshot(engine) as conn:
        status = conn.scalar(text("SELECT status FROM ops.run WHERE id=:run"), {"run": run["run_id"]})
        if status != "finished":
            raise ValueError("capture requires completed run; do not silently finalize or rerun production")
        correspondence = tuple(dict(row) for row in conn.execute(text("SELECT v.id,v.projection_digest,v.native_content_digest FROM kb.source_view v JOIN ops.run_source_view m ON m.source_view_id=v.id WHERE m.run_id=:run ORDER BY v.id"), {"run": run["run_id"]}).mappings())
        request = ContributionRequest(run_id=run["run_id"], method="extract.wce_named_candidates", include_details=True, limit=1000, max_bytes=128_000_000, page_bytes=32_000_000)
        page = serve_contributions(conn, request)
        pages = [page.model_dump(mode="json")]
        while page.next_cursor is not None:
            page = serve_contributions(conn, request.model_copy(update={"cursor": page.next_cursor}))
            pages.append(page.model_dump(mode="json"))
        combined = {**pages[0], "items": [item for value in pages for item in value["items"]], "next_cursor": None, "population_paging_complete": True}
        manifest = export_contribution_selection(conn, ContributionRequest(run_id=run["run_id"], method="extract.wce_named_candidates", max_bytes=128_000_000, page_bytes=32_000_000), directory / "export")
    for name, value in (("source-correspondence.json", correspondence), ("inspection-pages.json", pages), ("inspection.json", combined), ("export-receipt.json", manifest)):
        path = directory / name
        if path.exists():
            if canonical_bytes(json.loads(path.read_bytes())) != canonical_bytes(value):
                raise ValueError("existing capture differs; preserve original and use a new receipt")
        else:
            with path.open("xb") as stream:
                stream.write(canonical_bytes(value) + b"\n")
    reports.append({"project_id": directory.name, "run_id": run["run_id"], "cut_id": page.cut_id, "inventory_counts": page.inventory_counts})
if not reports:
    raise ValueError("no exact retained source-ready execution receipts")
with (root / "result.json").open("xb") as stream:
    stream.write(canonical_bytes({"outcome": "passed", "runs": reports, "scope": "actual finite named-candidate composition/native/read/selected export; not full M1 GLiNER qualification", "read_capture_resumed_without_provider_rerun": True, "original_failed_driver_receipt_retained": (root / "failure.json").exists()}) + b"\n")
print(json.dumps({"outcome": "passed", "runs": reports}))

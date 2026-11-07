"""Regenerate the selected GS120 artifact cohort and compare exact delivery routes."""

import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from sqlalchemy import text

from corpus_structure.methods.artifact_identity import ArtifactIdentityConfig, ArtifactIdentityMethod
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.serve.structural_products import StructuralExportRequest
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent / "2026-11-06_wce-gs120"
REFERENCE = HERE.parent / "2026-11-06_wce-completion-repair/source-references/source-reference.json"
sys.path.insert(0, str(BASELINE / "current-structural-journey"))
sys.path.insert(0, str(HERE.parent / "2026-11-07_nce-source-linguistics"))

from journey_support import completed_metadata, retain, run_method, task_custody  # noqa: E402
from replay import match_anchor, pair_controls  # noqa: E402
from run_journey import inspect_artifact, prepared_release  # noqa: E402


def old_inputs(conn):
    run = completed_metadata(conn, 210)
    assert run["cut_id"] == 293
    cfg, old = conn.execute(
        text("""
         SELECT mc.params,res.body->'structural_product'->'artifact_identity'
         FROM ops.task t JOIN ops.task_result res ON res.task_id=t.id
         JOIN ops.method_config mc ON mc.id=t.method_config_id WHERE t.run_id=210
        """)
    ).one()
    assert {r["source_view_id"] for r in cfg["inputs"]["sources"]} == {157, 158, 159}
    assert not cfg["external_nomination_refs"]
    return ArtifactIdentityConfig.model_validate(cfg), old


def reference_custody(conn):
    run = completed_metadata(conn, 253)
    assert run["cut_id"] == 350
    task, raw = conn.execute(
        text("""
         SELECT t.id,r.body FROM ops.task t JOIN ops.task_result r ON t.id=r.task_id
         WHERE t.run_id=253 AND t.unit_id=159
        """)
    ).one()
    by_id = {row["contribution_id"]: row for row in raw["contributions"]}
    refs = []
    codes = []
    for row in by_id.values():
        if row["semantic_type"] != "structural.scoped_attachment":
            continue
        if source_python(row["value"])["relation"] != "artifact_reference_target":
            continue
        cues = [
            by_id[e["contribution_id"]]["anchors"][0]["source_piece"]
            for e in row["endpoints"]
        ]
        assert cues[0] == cues[1]
        codes.append(cues[0])
        refs.append(RetainedContributionRef(
            contribution_id=row["contribution_id"],
            project_id=run["project_id"],
            run_id=run["run_id"],
            cut_id=run["cut_id"],
            release_id=run["release_id"],
            result_revision=run["result_revision"],
            **task_custody(conn, run)[task],
        ))
    assert sorted(codes) == ["Table 6.1", "Table 6.2", "Table 6.3"]
    return tuple(sorted(refs, key=lambda ref: ref.contribution_id))


def independent_controls(conn, report):
    frame = json.loads(REFERENCE.read_bytes())
    inputs, product = report["inputs"], report["artifact_identity"]
    # Source roles and endpoints were frozen before these products. Caption recoveries
    # came from the archived source preparation, not from the nomination producer.
    new_view = {118: 157, 119: 158, 124: 159}
    from corpus_structure.semantic.structural_products import ExternalSourceRef

    refs = {
        source.source_view_id: source
        for data in inputs["sources"]
        for source in (ExternalSourceRef.model_validate(data),)
    }
    views = {i: load_source_view(conn, i, analysis=False) for i in refs}
    pairs = {(p["left"], p["right"]): p for p in product["pairs"]}
    results = []
    for case in pair_controls(frame):
        matches = []
        for role in ("reference", "caption"):
            anchor = frame["anchors"][case[f"{role}_anchor"]]
            view_id = new_view[anchor["source"]["source_view_id"]]
            matches.append(match_anchor(
                anchor, views[view_id], refs[view_id].identity, product["records"], role
            ))
        pair = pairs[tuple(sorted(match["record"] for match in matches))]
        assert "unscoped_code" in pair["candidate_routes"]
        assert pair["score_status"] == "reference_only" and pair["model_probability"] is None
        results.append(dict(
            case_id=case["id"], reference=matches[0], caption=matches[1],
            routes=pair["candidate_routes"], score_status=pair["score_status"],
        ))
    assert len(results) == 3
    assert any(r["case_id"].endswith("6.1") and "external_pairs" in r["routes"] for r in results)
    return results, opportunity_census(frame, new_view, refs, views, product)


def opportunity_census(frame, view_map, refs, views, product):
    pairs = {(p["left"], p["right"]): p for p in product["pairs"]}
    cases = []
    for case in frame["artifact_lineage_pairs"]:
        endpoints = []
        for role in ("reference", "caption"):
            anchor = frame["anchors"][case[f"{role}_anchor"]]
            view_id = view_map.get(anchor["source"]["source_view_id"])
            if view_id is None:
                endpoints.append(None)
                continue
            piece = next((
                p for p in views[view_id].pieces
                if p.get("item_ref") == anchor["native_pointer"]
                and p.get("cell_index") is None
                and p.get("source_field") == anchor["native_field"]
            ), None)
            if piece is None:
                endpoints.append(None)
                continue
            endpoints.append(
                match_anchor(anchor, views[view_id], refs[view_id].identity,
                             product["records"], role)["record"]
            )
        pair = pairs.get(tuple(sorted(endpoints))) if all(endpoints) else None
        cases.append(dict(
            case_id=case["id"], judgment=case["judgment"], endpoints=endpoints,
            candidate_routes=pair["candidate_routes"] if pair else [],
        ))
    return dict(
        cases=cases,
        compared=sum(all(c["endpoints"]) for c in cases),
        out_of_selected_capture=sum(not all(c["endpoints"]) for c in cases),
        supported_nominated=sum(
            c["judgment"] == "supported" and bool(c["candidate_routes"]) for c in cases
        ),
        unsupported_nominated=sum(
            c["judgment"] == "unsupported" and bool(c["candidate_routes"]) for c in cases
        ),
        supported_witnessed=sum(
            c["judgment"] == "supported" and "external_pairs" in c["candidate_routes"]
            for c in cases
        ),
    )


async def mcp_page(run):
    transport = StdioTransport(
        command="ci", args=["mcp", "serve", "--semantic-run", str(run["run_id"])],
        cwd=str(Path.cwd()),
    )
    async with Client(transport, timeout=120) as client:
        result = await client.call_tool("structural_products", {"request": {
            "run_id": run["run_id"], "cut_id": run["cut_id"], "kind": "artifact_identity",
            "max_bytes": 8_000_000,
        }})
    if result.is_error or not isinstance(result.structured_content, dict):
        raise ValueError("fresh MCP did not deliver an artifact product")
    return result.structured_content


def ci_json(args, stdin=None):
    completed = subprocess.run(
        ("ci", *args), input=stdin, capture_output=True, text=True, check=False
    )
    if completed.returncode != 0:
        raise ValueError(completed.stderr or completed.stdout)
    return json.loads(completed.stdout)


def replay(release_id: str, output: Path):
    settings = Settings()
    output.mkdir(parents=True, exist_ok=True)
    prepared = prepared_release(settings, output, release_id)
    with open_runtime_engine(settings, "nce07-artifact-frozen-inputs", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            cfg, old = old_inputs(conn)
            refs = reference_custody(conn)
    inputs = cfg.inputs
    assert inputs is not None
    inputs = inputs.model_copy(update={
        "dependencies": (*inputs.dependencies, *(r.contribution_id for r in refs)),
    })
    cfg = cfg.model_copy(update={
        "inputs": inputs, "structural_input_digest": inputs.identity, "external_nomination_refs": refs,
    })
    artifact_dir = output / "artifact"
    run = run_method(
        settings, prepared, ArtifactIdentityMethod(), cfg.model_dump(mode="json"), inputs,
        artifact_dir, "witnessed-artifact-nominations", output.name,
    )
    _, inspection = inspect_artifact(settings, run, artifact_dir)
    cli = ci_json([
        "structure", "list", "--run", str(run["run_id"]), "--cut", str(run["cut_id"]),
        "--kind", "artifact_identity", "--max-bytes", "8000000", "--json",
    ])
    reader = json.loads((artifact_dir / "interactive-page.json").read_bytes())
    assert cli == reader == anyio.run(mcp_page, run)
    (report,) = cli["reports"]
    product = report["artifact_identity"]
    assert len(product["external_nominations"]) == len(refs)
    assert not product["explicit_references"]
    request = ReviewSelection(structural_selections=(
        StructuralExportRequest(run_id=run["run_id"], cut_id=run["cut_id"], kind="artifact_identity"),
    ))
    bundle = output / "bundle"
    if not bundle.exists():
        ci_json(
            ["review", "export", "--exact-closure", "--json", "-", str(bundle)],
            request.model_dump_json(),
        )
    detached = ci_json(["review", "verify", str(bundle), "--json"])
    with open_runtime_engine(settings, "nce07-artifact-source-opportunities", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            controls, census = independent_controls(conn, report)
    previous = {(p["left"], p["right"]) for p in old["pairs"]}
    actual = {(p["left"], p["right"]) for p in product["pairs"]}
    before_records = {r["occurrence_id"] for r in old["records"]}
    after_records = {r["occurrence_id"] for r in product["records"]}
    result = dict(
        outcome="passed",
        selected=run,
        baseline=dict(run_id=210, cut_id=293, records=len(before_records), pairs=len(previous)),
        inspection=inspection,
        route_counts=product["route_counts"],
        score_status_counts=Counter(pair["score_status"] for pair in product["pairs"]),
        new_physical_occurrences=len(after_records - before_records),
        new_pair_keys=len(actual - previous),
        removed_pair_keys=len(previous - actual),
        newly_represented_reference_pairs=sum(
            not {c["reference"]["record"], c["caption"]["record"]} <= {
                r["contribution_id"] for r in old["records"]
            }
            for c in controls
        ),
        independent_controls=controls,
        reference_opportunity_census=census,
        delivery=dict(reader_cli_mcp_equal=True, detached=detached),
    )
    retain(output / "result.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(replay(args.release, args.output), ensure_ascii=False))

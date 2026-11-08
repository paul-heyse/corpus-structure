"""Read each settled cohort observation and original-source search through released owners."""

import argparse
import base64
import json
from hashlib import sha256
from pathlib import Path

from corpus_structure.semantic.query import ReadLimit, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source
from corpus_structure.serve.source_search import SourceSearchRequest, search_source
from corpus_structure.settings import Settings


def _members(root, manifest):
    for receipt in sorted(root.glob("group-*.result.json")):
        result = json.loads(receipt.read_bytes())
        if result["source"] != manifest["source"]:
            raise ValueError(f"shadow result belongs to another source {receipt}")
        yield from result["members"]


def _raw_bytes(conn, scope, evidence, digest):
    cursor = None
    payload = bytearray()
    while True:
        raw = inspect_native_source(
            conn,
            NativeSourceRequest.model_validate({
                **scope, "evidence": evidence, "artifact_digest": digest, "cursor": cursor
            }),
        )
        row = raw.rows[0]
        if row["offset"] != len(payload) or row["artifact_digest"] != digest:
            raise ValueError("cohort raw response is discontinuous or outside its retained pin")
        payload.extend(base64.b64decode(row["data"], validate=True))
        if (cursor := raw.next_cursor) is None:
            break
    if sha256(payload).hexdigest() != digest:
        raise ValueError("cohort raw response differs from the retained digest")
    return payload


def _read_member(conn, member, manifest, output):
    selection = {key: value for key, value in member["selection"].items() if value is not None}
    if member["status"] != "source_ready":
        return {"selection": selection, "status": member["status"], "error": member["error"]}
    scope = {
        **manifest["source"],
        **{key: selection[key] for key in ("page_no", "pointer", "region_index") if key in selection},
        "view": "visual_evidence",
        "evidence": member["mapped"] or member["raw"],
        "max_bytes": 8 * 1024 * 1024,
        "limit": 1000,
    }
    response = inspect_native_source(conn, NativeSourceRequest.model_validate(scope))
    visual = response.visual_evidence
    if (
        visual is None
        or visual.original_artifact_digest != manifest["cohort"]["input_sha256"]
        or visual.page_no != selection["page_no"]
    ):
        raise ValueError("cohort visual read differs from its source or physical page")
    if digest := visual.observation.get("raw_response_digest"):
        payload = _raw_bytes(conn, scope, member["raw"], digest)
        stem = output / f"page-{visual.page_no:03d}-{member['task_id']}"
        stem.with_suffix(".html").write_bytes(payload)
    selected_tables = {}
    if {"table", "raster_form"} & set(manifest["cohort"]["capabilities"]):
        for row in response.rows:
            if row.get("label") != "table":
                continue
            pointer = row["pointer"]
            try:
                native = inspect_native_source(
                    conn,
                    NativeSourceRequest.model_validate({
                        **manifest["source"], "view": "item", "pointer": pointer,
                        "max_bytes": 8 * 1024 * 1024,
                    }),
                )
                selected_tables[pointer] = native.model_dump(mode="json")
            except ReadLimit as error:
                selected_tables[pointer] = {"outcome": "unavailable", "reason": str(error)}
    return {
        "selection": selection,
        "status": member["status"],
        "raw": member["raw"],
        "mapped": member["mapped"],
        "reader": response.model_dump(mode="json"),
        "selected_tables": selected_tables,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", type=Path)
    parser.add_argument("shadow", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    baseline_runs = set()
    with (
        open_runtime_engine(Settings(), "chandra-cohort-read", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        for path in sorted(args.manifests.glob("*.json")):
            manifest = json.loads(path.read_bytes())
            baseline_runs.add(manifest["source"]["run_id"])
            destination = args.output / path.stem
            destination.mkdir()
            members = [
                _read_member(conn, member, manifest, destination)
                for member in _members(args.shadow / path.stem, manifest)
            ]
            (destination / "reader.json").write_text(json.dumps(members, ensure_ascii=False, indent=2))
        for run in sorted(baseline_runs):
            search = search_source(conn, SourceSearchRequest(run_id=run, text="إفصاح الراكب"))
            (args.output / f"search-arabic-{run}.json").write_text(search.model_dump_json())


if __name__ == "__main__":
    main()

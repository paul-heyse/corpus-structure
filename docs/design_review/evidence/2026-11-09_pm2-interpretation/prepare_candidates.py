"""Build private candidate-centered requests from exact same-release parser results."""
import argparse
import json
from pathlib import Path

from sqlalchemy import select

from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

FOLDER = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("parser_result", type=Path)
    args = parser.parse_args()
    settled = json.loads(args.parser_result.read_bytes())
    request = json.loads((FOLDER/"raw/development-source-request.json").read_bytes())
    source_request = json.loads((FOLDER/"raw/development-parser-request.json").read_bytes())
    sources = {s["source"]["source_view_id"]: s for s in source_request["scopes"]}
    run, cut = settled["run_id"], settled["cut_id"]
    with open_runtime_engine(Settings(), "pm2-candidate-controls", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            session = bind_completed_result(conn, run)
            jobs = table("ops.run")
            runtime = conn.scalar(select(jobs.c.runtime_id).where(jobs.c.id == run))
            def rows(view):
                return read_source_contributions(
                    conn, prepared=session.prepared, run_id=run, cut_id=cut,
                    source_view_id=view, include_details=True, limit=1000,
                ).contributions
            fair, gambler = rows(389), rows(405)

    def ref(row):
        return {
            "contribution_id": row["contribution_id"], "project_id": request["project"],
            "run_id": run, "cut_id": cut, "release_id": request["release"],
            "result_revision": session.binding.data_revision,
            "selected_task_id": row["selected_task_id"], "origin_task_id": row["origin_task_id"],
            "runtime_fingerprint": runtime,
        }
    def text_at(row, rows, location):
        return tuple(a["source_piece"] for item in rows if item["item_key"] == location
                     and item["contribution_id"] in row["members"] for a in item.get("anchors", ()))
    def scope(view, family, focus, alternatives=()):
        selected = sources[view]
        return dict(source=selected["source"], extent=selected["extent"], family=family,
                    profile=request["scopes"][0]["profile"], focus=ref(focus),
                    candidates=[ref(row) for row in alternatives])
    frames = [row for row in fair if row["semantic_type"] == "linguistic.predicate_frame"]
    (condition,) = (row for row in fair if row["semantic_type"] == "linguistic.qualifier_cue"
                    and source_python(row["value"])["kind"] == "condition")
    (host,) = (row for row in frames if "assign" in
               text_at(row, fair, source_python(row["value"])["predicate"]))
    other_frames = [row for row in frames if row != host]
    mentions = [row for row in gambler if row["semantic_type"] == "maverick.mention"]
    locations = {row["contribution_id"]: tuple(
        literal for key in source_python(row["value"])["location_keys"]
        for literal in text_at(row, gambler, key)
    ) for row in mentions}
    (she,) = (row for row in mentions if locations[row["contribution_id"]] == ("She",))
    alternatives = [row for row in mentions if locations[row["contribution_id"]] == ("A gambler",)]
    request["scopes"] = [
        scope(389, "qualification_scope_v1", condition, frames),
        scope(389, "frame_interpretation_v1", host),
        scope(389, "relation_interpretation_v1", host, other_frames[:1]),
        scope(405, "local_referent_choice_v1", she, alternatives[:12]),
    ]
    print(json.dumps(request))


if __name__ == "__main__":
    main()

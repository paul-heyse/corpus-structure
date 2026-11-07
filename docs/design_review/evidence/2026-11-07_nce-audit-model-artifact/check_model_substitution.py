"""Exercise native and detached admission on resealed current provider envelopes."""

import argparse
import json
import os
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path

from pydantic import TypeAdapter
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.methods.gliner import GlinerInput, GlinerProfile
from corpus_structure.methods.model_observation import (
    observation_digest,
    released_pack,
    request_digest,
)
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralProductReport
from corpus_structure.serve.model_observation_replay import _policy, _verify_definition_roles
from corpus_structure.serve.review_bundle import _detached_relation
from corpus_structure.settings import Settings


def reseal(detail, configuration, release, policy, window, passage):
    alternate = deepcopy(detail)
    pack = released_pack(release, policy, config=configuration)
    profile = TypeAdapter(GlinerProfile).validate_python(configuration["profile"])
    request = GlinerInput(
        "definition-target:" + window.identity,
        window.identity,
        window.text,
        "structure.definition_components/9",
    )
    overlap = configuration["evaluation_overlap"]
    key = request_digest(
        pack,
        asdict(profile),
        (request,),
        configuration["threshold"],
        overlap or "flat",
        overlap is not None,
        policy["inference"],
    )
    alternate.update(
        schema_declaration=pack.declaration_json,
        pack_fingerprint=pack.fingerprint,
        overlap_policy=overlap or "flat",
    )
    alternate["window_outcomes"][0].update(start=window.start, end=window.end, request_digest=key)
    entry = alternate["raw_reports"][0]
    entry.update(
        passage_id=passage.passage_id,
        window_start=window.start,
        window_end=window.end,
        request_digest=key,
        computation=key,
        context_id=request.context_id,
        context_digest=request.context_digest,
        pack=pack.fingerprint,
        observation_digest=observation_digest(
            key, entry["raw_json"], entry["effective_profile_json"]
        ),
    )
    entry["preparation"]["consumed_text"] = window.text + entry["preparation"]["synthetic_suffix"]
    return alternate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--run", type=int, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.bundle / "manifest.json").read_bytes())
    descriptor = os.open(args.bundle, os.O_RDONLY | os.O_DIRECTORY)
    try:
        (origin,) = [
            row
            for row in _detached_relation(descriptor, manifest, "reports")
            if row.get("origin_run_id") == args.run
            and (row.get("body") or {}).get("method") == "structure.definition_components"
        ]
        contracts = {
            row["release_id"]: row for row in _detached_relation(descriptor, manifest, "contracts")
        }
    finally:
        os.close(descriptor)
    body = origin["body"]
    release = body["release_id"]
    config = origin["configuration"]
    policy = _policy(contracts[release])
    report = StructuralProductReport.model_validate(body["structural_product"])
    detail = source_python(body["parse_detail"])
    passages = {passage.passage_id: passage for passage in report.inputs.passages}
    selected = detail["window_outcomes"][0]
    passage = passages[selected["passage_id"]]
    if (selected["start"], selected["end"]) != (passage.start, passage.end):
        raise ValueError("the selected first request requires a complete single passage")
    shortened = passage.model_copy(update={"end": passage.end - 1, "text": passage.text[:-1]})
    controls = {
        "ordered_schema": ({**config, "term_entity": "substituted role"}, passage),
        "evaluation_overlap": ({**config, "evaluation_overlap": "allow"}, passage),
        "threshold": ({**config, "threshold": "0.6"}, passage),
        "same_passage_window": (config, shortened),
    }
    query = text("""
        SELECT ops.validate_definition_window_requests(
            :release, CAST(:detail AS jsonb), CAST(:config AS jsonb), CAST(:passages AS jsonb)
        )
    """)
    parameters = {
        "release": release,
        "config": json.dumps(config),
        "passages": json.dumps({key: row.model_dump(mode="json") for key, row in passages.items()}),
    }
    settings = Settings()
    results = {}
    with (
        open_runtime_engine(settings, "nce-model-substitution", purpose="maintenance") as engine,
        read_snapshot(engine) as conn,
    ):
        conn.execute(query, {**parameters, "detail": json.dumps(detail)})
        _verify_definition_roles(report, config, detail, release, policy)
        for name, (alternate, window) in controls.items():
            forged = reseal(detail, alternate, release, policy, window, passage)
            try:
                with conn.begin_nested():
                    conn.execute(query, {**parameters, "detail": json.dumps(forged)})
            except DBAPIError as failure:
                if getattr(failure.orig, "sqlstate", None) != "23514":
                    raise
                native = str(failure.orig).splitlines()[0]
            else:
                raise ValueError(f"native accepted the resealed {name}")
            try:
                _verify_definition_roles(report, config, forged, release, policy)
            except ValueError as failure:
                detached = str(failure)
            else:
                raise ValueError(f"detached accepted the resealed {name}")
            results[name] = {"native": native, "detached": detached}
    print(
        json.dumps(
            {"outcome": "passed", "run": args.run, "release_id": release, "controls": results}
        )
    )


if __name__ == "__main__":
    main()

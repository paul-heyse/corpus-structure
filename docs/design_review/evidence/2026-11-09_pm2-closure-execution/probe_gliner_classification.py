"""Exercise the new GLiNER request, real CPU worker and projection without database writes."""

import json
from contextlib import closing
from pathlib import Path

import yaml
from corpus_structure.methods.pm2_gliner_classification import (
    FAMILY,
    ClassificationProfile,
    ClassificationWorker,
    classification_mapping,
    classification_product,
    classification_request,
)
from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.methods.model_observation import released_policy
from corpus_structure.orchestrate.pm2_stage import InterpretationScope
from corpus_structure.semantic.interpretation_questions import declared_families
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_contexts import PreparedNativeSources
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
RETAINED = HERE.parent / "2026-11-09_pm2-interpretation-pair/raw/revised-request.json"
METHODS = HERE.parents[3] / "domains/statistics/m1-methods.yaml"


def probe() -> dict:
    retained = json.loads(RETAINED.read_bytes())
    (choice,) = (row for row in retained["scopes"] if row["family"] == FAMILY)
    scope = InterpretationScope.model_validate(choice)
    (question_key,) = scope.questions
    if scope.focus or scope.candidates or scope.retrieval:
        raise ValueError("the retained question is not source-only")
    defaults = yaml.safe_load(METHODS.read_bytes())["configs"]["extract.m1_candidates"]["default"]
    profile = ClassificationProfile.model_validate(
        {
            "provider": "gliner",
            "device": "cpu",
            "profile": {
                key: defaults[key]
                for key in ("snapshot", "checkpoint", "revision", "artifact_hashes")
            },
        }
    )
    with (
        open_runtime_engine(Settings(), "pm2-gliner-worker-control", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        prepared = open_release(conn, retained["release"])
        conn.execute(
            select(
                func.ops.validate_structural_source(
                    literal(scope.source.model_dump(mode="json"), JSONB)
                )
            )
        )
        view = load_source_view(conn, scope.source.source_view_id, analysis=False)
        frame = native_source_frame(view, ())
        family = declared_families(prepared.registry_rows)[FAMILY]
        inference = released_policy(prepared)["inference"]
    mapping = classification_mapping(frame, scope.extent, PreparedNativeSources((frame,)))
    profile.verify()
    request = classification_request(
        retained["release"], family, question_key, mapping, profile, inference
    )
    with closing(ClassificationWorker(profile)) as worker:
        reply = worker.infer(request, check_active=lambda: None)
    if reply["outcome"] != "succeeded":
        raise ValueError(reply["reason"])
    value = classification_product(request, reply["gliner"], profile).value
    if value["selected_keys"] != ("definition",):
        raise ValueError("the isolated native control did not preserve the definition choice")
    return {
        "outcome": "passed",
        "scope": scope.source.model_dump(mode="json"),
        "extent": scope.extent,
        "question": question_key,
        "provider": reply["gliner"],
        "product": value,
        "managed_settlement": "not_run",
        "protected_grade": "not_run",
    }


if __name__ == "__main__":
    print(json.dumps(probe(), indent=2))

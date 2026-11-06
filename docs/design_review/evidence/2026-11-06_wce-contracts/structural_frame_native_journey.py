"""Actual native frame-v2 checks over original authenticated statistics sources.

The evaluator transaction always rolls back. No labels are authored, inspected or
exported; original source groups/partitions remain unchanged. This is enforcement
coverage, not a held-out semantic quality or multi-origin independence claim.
"""
from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.review_assessments import record_review_exposure
from corpus_structure.evaluate.structural_assessment import (
    StructuralEvaluationFrameV2,
    create_structural_reference_set,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
PACKET = HERE.parent / "2026-11-06_wce-candidate-foundation/raw/source-opportunities-001.json"
PROJECT = "pce-statistics-structural"
RELEASE = "release:bf5e216e03f9cfab2946a8cddac13443d909c40c35ef33f64c83ba4d0c42eb91"


def retain(name, value):
    with (HERE / name).open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")


def frame_for(packet, views, groups):
    sources = [v for v in packet["sources"] if v["source_view_id"] in views]
    refs = {sha256(canonical_bytes(v)).hexdigest() for v in sources}
    passages = [p for p in packet["passages"] if p["source_ref"] in refs]
    return StructuralEvaluationFrameV2.model_validate(dict(
        protocol="structural-evaluation-frame-2",
        inputs=dict(question="Mechanism control: authenticate selected original source groups; no semantic efficacy claim", scope=packet["scope"], inventory_id="wce-native-frame-control-001", policy_id="native-group-membership-control-1", sources=sources, passages=passages, dependencies=("original-source-packet:" + sha256(PACKET.read_bytes()).hexdigest(),), coverage_limits=("Enforcement-only control over exposed statistics sources; not fresh held-out semantic evidence.",)),
        operation="qualified_comparison", direction="source_first", rubric_version="wce-native-mechanism-control-1", rubric_text="Verify original custody and partition enforcement only; do not author or expose semantic reference answers.", product_ids=(), partition="final_assessment",
        source_groups=[dict(source_ref=sha256(canonical_bytes(s)).hexdigest(), origin_group=groups[s["source_view_id"]]["origin_group"]) for s in sources],
        opportunities=[dict(opportunity_id="source-scope:" + p["passage_id"], passage_id=p["passage_id"], facet="source_support", source_state="uninspected") for p in passages],
        inspected_scope="Native custody/origin control; semantic facets remain uninspected", exposure_history=(),
    ))


def main():
    packet = json.loads(PACKET.read_bytes())
    results = []
    settings = Settings()
    with open_runtime_engine(settings, "wce-frame2-native-control", purpose="evaluate") as engine:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                principal = conn.scalar(text("SELECT current_user"))
                assert principal == "corpus_sem_evaluator"
                rows = conn.execute(text("""
                    SELECT v.id,member.origin_group,origin.partition FROM kb.source_view v
                    JOIN kb.document d ON d.id=v.document_id
                    JOIN eval.reference_origin_source member ON member.project_id=d.project_id AND member.source_uri=d.source_uri
                    JOIN eval.reference_origin_group origin ON origin.project_id=member.project_id AND origin.origin_group=member.origin_group
                    WHERE v.id IN (26,31,32) ORDER BY v.id
                """)).mappings().all()
                groups = {r["id"]: dict(r) for r in rows}
                before = conn.scalar(text("SELECT count(*) FROM eval.structural_reference_set WHERE project_id=:p"), {"p": PROJECT})
                frozen = frame_for(packet, {31,32}, groups)
                identifier = create_structural_reference_set(conn, project_id=PROJECT, release_id=RELEASE, frame=frozen)
                actual = conn.execute(text("SELECT frame,frame_digest FROM eval.structural_reference_set WHERE id=:id"), {"id": identifier}).mappings().one()
                assert actual["frame_digest"] == frozen.identity
                assert actual["frame"]["source_groups"] == frozen.model_dump(mode="json")["source_groups"]
                results.append(dict(control="positive_two_original_source_references", outcome="passed", source_views=[31,32], source_origin_groups=["nist-ehandbook"], partition="final_assessment", frame_digest=frozen.identity))
                forged = frozen.model_dump(mode="json")
                forged["source_groups"][0]["origin_group"] = "forged-origin"
                for label, raw, expected in (
                    ("forged_origin_refusal", forged, "invalid structural source opportunity/group/partition"),
                    ("mixed_partition_refusal", frame_for(packet, {26,31}, groups).model_dump(mode="json"), "invalid structural source opportunity/group/partition"),
                ):
                    try:
                        with conn.begin_nested():
                            create_structural_reference_set(conn, project_id=PROJECT, release_id=RELEASE, frame=StructuralEvaluationFrameV2.model_validate(raw))
                    except DBAPIError as error:
                        assert getattr(error.orig, "sqlstate", None) == "23514" and expected in str(error.orig)
                        results.append(dict(control=label, outcome="passed", sqlstate="23514"))
                    else:
                        raise AssertionError(label + " accepted invalid source group")
                try:
                    with conn.begin_nested():
                        record_review_exposure(conn, project_id=PROJECT, set_id=identifier, purpose="native-mechanism-control", recipient_class="test-runner", group=True)
                except DBAPIError as error:
                    assert getattr(error.orig, "sqlstate", None) == "23514" and "protected structural partitions" in str(error.orig)
                    results.append(dict(control="heldout_development_exposure_refusal", outcome="passed", sqlstate="23514"))
                else:
                    raise AssertionError("sealed group permitted development exposure")
                retain("structural-frame-native-input-001.json", frozen.model_dump(mode="json"))
            finally:
                transaction.rollback()
            after = conn.scalar(text("SELECT count(*) FROM eval.structural_reference_set WHERE project_id=:p"), {"p": PROJECT})
            assert before == after
    with open_runtime_engine(settings, "wce-frame2-reader-denial", purpose="read") as engine, engine.connect() as conn:
        try:
            conn.execute(text("SELECT eval.create_structural_reference_set(:p,:r,CAST(:f AS jsonb))"), {"p": PROJECT, "r": RELEASE, "f": canonical_bytes(frozen.model_dump(mode="json")).decode()})
        except DBAPIError as error:
            assert getattr(error.orig, "sqlstate", None) == "42501"
            results.append(dict(control="ordinary_reader_cannot_author_frame", outcome="passed", sqlstate="42501"))
        else:
            raise AssertionError("ordinary reader authored a protected group frame")
        finally:
            conn.rollback()
    receipt = dict(protocol="wce-structural-frame-native-control-1", date="2026-11-06", outcome="passed", principal=principal, source_packet_sha256=sha256(PACKET.read_bytes()).hexdigest(), controls=results, effects="evaluator transaction rolled back; no reference labels authored/exposed; original origin assignments unchanged", quality_claim="native_enforcement_only; two source references from one family, not independent origins or held-out efficacy", script_sha256=sha256(Path(__file__).read_bytes()).hexdigest())
    retain("structural-frame-native-receipt-001.json", receipt)
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()

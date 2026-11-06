"""Bind authentic source-first normal references to native frame2/A/B/C custody.

Original source questions and author bytes predate candidate production. This
late binding authenticates the same physical source under the candidate release's
source-view IDs; it does not select cases from surviving predictions.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select, text

from corpus_structure.evaluate.operation_assessment import (
    PROTOCOL, OperationCase, OperationEvaluationFrameV2, OperationSourceOpportunity,
    create_reference_set, record_pass,
)
from corpus_structure.evaluate.record_references import assign_origin, source_binding, source_units
from corpus_structure.evaluate.semantic import split_documents
from corpus_structure.evaluate.split import SplitConfig
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_contexts import NativeSourceContext, SourceInterval, SourceSlice, evidence_anchor, record_source_pin
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
PROJECT = "wce-statistics-normal-20261106"
RUN = 113


def write_new(path, value):
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")


def main():
    output = HERE / "normal-native-references003"
    output.mkdir(exist_ok=False)
    source_packet = json.loads((RAW / "source-opportunities-002.json").read_bytes())
    author_raw = {kind: json.loads((RAW / f"source-author-{kind}-002.json").read_bytes()) for kind in ("A", "B", "C")}
    source_cut = json.loads((HERE / "normal-excerpt002/source-cut-001.json").read_bytes())
    settings = Settings()
    try:
        with open_runtime_engine(settings, "wce-featurefit-reference-source", purpose="evaluate") as engine, read_snapshot(engine) as conn:
            run = dict(conn.execute(text("SELECT r.*,c.cut_id FROM ops.run r JOIN ops.completed_result c ON c.run_id=r.id WHERE r.id=:run"), {"run": RUN}).mappings().one())
            units = source_units(conn, RUN)
            selected = next(unit for unit in units if unit["projection_digest"] == source_packet["sources"][0]["projection_digest"])
            view = load_source_view(conn, selected["source_view_id"], analysis=False)
            logical = source_binding(conn, source_run_id=RUN, source_view_id=view.ref.id, source_cut_id=run["cut_id"])
            source = native_source_frame(view, ())
            if source.unit_ref != logical or view.text != source_packet["passages"][0]["text"]:
                raise ValueError("candidate source differs from independently frozen original source")
            document = dict(conn.execute(select(table("kb.document")).where(table("kb.document").c.id == selected["document_id"])).mappings().one())
        if document["content_hash"] != source_cut["excerpt_sha256"]:
            raise ValueError("current source document differs from exact parent-page cut")
        context = NativeSourceContext(source, (), (SourceSlice(source.source_view_id, 0, len(view.text)),),
            "independent source quotation reference", "wce-source-quotation-rubric-1", "complete selected normal source view",
            max_chars=len(view.text), max_pieces=max(1, len(view.pieces)))
        anchors = {}
        fragmentation = []

        def expected_span(span):
            if span["text"] != view.text[span["start"]:span["end"]]:
                raise ValueError("author expected span differs from frozen source")
            selected_anchors = []
            gaps = []
            for interval in context.intervals:
                left, right = max(span["start"], interval.model_start), min(span["end"], interval.model_end)
                if left >= right:
                    continue
                if not isinstance(interval, SourceInterval):
                    gaps.append({"start": left, "end": right, "reason": "projection separator is not native source quotation"})
                    continue
                for piece in context.map_span(left, right, literal=context.text[left:right], allow_multiple=True):
                    anchor, _ = evidence_anchor(context, piece, native=True)
                    anchors[anchor["anchor_id"]] = anchor
                    selected_anchors.append(anchor)
            if gaps:
                fragmentation.append({"start": span["start"], "end": span["end"], "native_piece_count": len(selected_anchors), "excluded_synthetic_gaps": gaps})
            return tuple(a["anchor_id"] for a in selected_anchors), {"source_pieces": [a["source_piece"] for a in selected_anchors]}

        cases_by_author = {}
        for kind in ("A", "B"):
            cases = []
            for proposed in author_raw[kind]["opportunities"]:
                identifier = proposed.get("id", proposed.get("opportunity_id"))
                spans = [proposed["content_location"]] if kind == "A" else proposed["content_spans"]
                valid = [span for span in spans if span and span["end"] > span["start"]]
                if not valid:
                    continue
                ids, alternatives = [], []
                for span in valid:
                    span_ids, fields = expected_span(span)
                    ids.extend(span_ids)
                    alternatives.append(fields)
                cases.append(OperationCase(case_id=identifier, facet="source_quotation", anchor_ids=tuple(dict.fromkeys(ids)),
                    inspected_scope="complete selected source; author-specific proposed content fragment(s)", source_state="stated", judgment="supported",
                    alternatives=tuple(alternatives), explanation="Retain this author's exact independently proposed source content. Multiple fragments are alternatives for this location-only event; this does not adjudicate their combined attachment.",
                    assessor_provenance={"raw_author": kind, "raw_file_sha256": sha256((RAW / f"source-author-{kind}-002.json").read_bytes()).hexdigest(), "raw_case_id": identifier, "normalized_claim": "source quotation only; semantic role/attachment not elevated"}))
            cases_by_author[kind] = cases
        cases = []
        for selected_case in author_raw["C"]["cases"]:
            ids, fields = expected_span(selected_case)
            cases.append(OperationCase(case_id=selected_case["opportunity_id"], facet=selected_case["facet"], anchor_ids=ids,
                inspected_scope="independently frozen exact normal-source quotation opportunity", source_state="stated", judgment="supported",
                alternatives=(fields,), explanation=selected_case["reason"] + " Native scoring is source-quotation location only, not scientific validity or public component support.",
                assessor_provenance={"raw_author": "C", "raw_file_sha256": sha256((RAW / "source-author-C-002.json").read_bytes()).hexdigest(), "raw_case_id": selected_case["case_id"], "source_opportunity_id": selected_case["opportunity_id"], "claim": "source quotation location only"}))
        cases_by_author["C"] = cases
        frame = OperationEvaluationFrameV2(unit=selected["unit_key"], release_id=run["release_id"], guideline_version="wce-statistics-source-quotation-1",
            rubric_version="wce-source-quotation-rubric-1", context_policy="native-source-only-1",
            operation_question="propose_named_source_roles_from_retained_annotations", operation_version="retained-annotation-rules-2",
            domain="statistics", direction="source_first", pin=record_source_pin(source), anchor_ids=tuple(anchors),
            anchor_scopes=tuple({k: value for k, value in a.items() if k in {"pin", "space", "pointer", "precision", "start", "end", "recognition"}} for a in anchors.values()),
            source_group="grinstead-snell", partition="feature_fit", inspected_scope="full authenticated normal-source projection selected by frozen source digest",
            opportunities=tuple(OperationSourceOpportunity(o["opportunity_id"], source.source_view_id, o["start"], o["end"], o["facet"], "stated") for o in source_packet["opportunities"]),
            exposure_history=("operator-authorized already exposed same statistics source-family refinement; not final calibration/assessment",))
        payloads = {}
        for kind, authored_cases in cases_by_author.items():
            payloads[kind] = {"protocol": PROTOCOL, "release_id": frame.release_id, "unit_ref": frame.unit,
                "guideline": frame.guideline_version, "rubric_version": frame.rubric_version, "context_policy": frame.context_policy,
                "operation_question": frame.operation_question, "operation_version": frame.operation_version, "domain": frame.domain,
                "direction": frame.direction, "reason": "Exact source-only authored bytes retained and normalized into quotation-location cases; original author populations preserved.",
                "cases": [asdict(case) for case in authored_cases], "adjudication_passes": []}
        with open_runtime_engine(settings, "wce-featurefit-reference-write", purpose="evaluate") as engine, engine.begin() as conn:
            assign_origin(conn, project_id=PROJECT, origin_group="grinstead-snell", partition="feature_fit", source_uris=(document["source_uri"],),
                provenance={"parent_sha256": source_cut["parent_sha256"], "source_cut_sha256": sha256((HERE / "normal-excerpt002/source-cut-001.json").read_bytes()).hexdigest(), "same_origin": "new excerpt of existing Grinstead source family; no fresh origin or repartition"})
            split_documents(conn, PROJECT, SplitConfig(forced_dev={document["source_uri"]: "legacy development routing only; authoritative origin remains feature_fit"}), release_id=frame.release_id)
            created = create_reference_set(conn, project_id=PROJECT, source_run_id=RUN, source_cut_id=run["cut_id"], label="wce-normal-source-first-001", legacy_split="dev",
                guideline=frame.guideline_version, guideline_text="Independently selected source quotations and location questions only. Domain roles, attachment, applicability and scientific truth remain different events.", partition="feature_fit",
                sampling={"seed": 0, "strata": {frame.unit: "purposively_selected_normal_source"}, "inclusion_probabilities": {frame.unit: 1}, "provenance": {"source_opportunities_sha256": sha256((RAW / "source-opportunities-002.json").read_bytes()).hexdigest(), "selection": "source-opportunity census frozen before named production; native view-ID correspondence bound later"}, "cohort": "wce-normal-source-002"}, frames={frame.unit: frame})
            unit = conn.scalar(select(table("eval.reference_unit").c.id).where(table("eval.reference_unit").c.set_id == created["set_id"]))
            ids = {}
            for kind in ("A", "B", "C"):
                if kind == "C":
                    payloads[kind]["adjudication_passes"] = [ids["A"], ids["B"]]
                authored = canonical_bytes(payloads[kind])
                ids[kind] = record_pass(conn, unit_id=unit, pass_kind=kind, actor="wce-independent-source-" + kind + "2", authored=authored, frame=frame)
                write_new(output / f"native-author-{kind}.json", payloads[kind])
        write_new(output / "source-frame.json", asdict(frame))
        write_new(output / "source-fragmentation.json", fragmentation)
        write_new(output / "result.json", {"outcome": "passed", "set_id": created["set_id"], "unit_id": unit, "pass_ids": ids,
            "case_counts": {k: len(v) for k, v in cases_by_author.items()}, "source_opportunities": len(frame.opportunities), "source_run_id": RUN,
            "partition": "feature_fit", "original_origin_preserved": True, "native_frame_bound_after_actual_view_id_correspondence": True,
            "source_questions_and_independent_authors_frozen_before_predictions": True, "public_eligibility": False})
        print(json.dumps({"outcome": "passed", "set_id": created["set_id"], "unit_id": unit, "pass_ids": ids}))
    except BaseException as error:
        write_new(output / "failure.json", {"outcome": "failed", "type": type(error).__name__, "message": str(error)})
        raise


if __name__ == "__main__":
    main()

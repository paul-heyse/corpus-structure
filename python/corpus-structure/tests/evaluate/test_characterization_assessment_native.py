"""Actual V3 grade custody over sealed characterization products and source-only references."""

import json
from dataclasses import asdict, replace
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import pytest
from evaluate.test_operation_assessment_native import freeze
from semantic.conftest import semantic_db_engine as semantic_db_engine
from semantic.conftest import semantic_evaluator_engine as semantic_evaluator_engine
from semantic.conftest import semantic_writer_engine as semantic_writer_engine
from semantic.native_record_fixtures import private_source as private_source
from semantic.reference_scenarios import private_source_options as private_source_options
from semantic.reference_scenarios import reference_source as reference_source
from semantic.test_characterization_native import make_task
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.operation_assessment import (
    OperationCase,
    OperationEvaluationFrameV3,
    create_reference_set,
    inspect_evaluation,
    record_pass,
    reference_evaluate,
)
from corpus_structure.evaluate.record_references import reference_inputs
from corpus_structure.evaluate.semantic import ReferenceError
from corpus_structure.semantic.characterization import (
    characterization_inputs,
    occurrence_id,
    validate_layer,
    validate_view,
)
from corpus_structure.semantic.characterization_store import compose_view, publish_layer
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.operations import seal_cut
from corpus_structure.semantic.product_reference import ProductReference


def characterization_references(bundle):
    return reference_inputs(characterization_inputs(bundle))


def submit_abc(conn, unit, frame, payload, *, actor):
    authored = dict(payload)
    passes = []
    for kind in ("A", "B"):
        authored["adjudication_passes"] = []
        passes.append(
            record_pass(
                conn,
                unit_id=unit,
                pass_kind=kind,
                actor=f"{actor}-{kind}",
                authored=json.dumps(authored).encode(),
                frame=frame,
            )
        )
    authored["adjudication_passes"] = passes
    record_pass(
        conn,
        unit_id=unit,
        pass_kind="C",
        actor=f"{actor}-C",
        authored=json.dumps(authored).encode(),
        frame=frame,
    )


@pytest.mark.parametrize(
    "private_source",
    [dict(bundle_transform=characterization_references, additional_methods=("native-binding",))],
    indirect=True,
)
def test_native_v3_grading_preserves_source_output_and_empty_population(
    reference_source,
    semantic_evaluator_engine,
):
    case = reference_source
    row = case.view_row
    base = ProductReference(
        row["native_task_id"], row["native_product_key"], row["native_content_digest"]
    )
    piece = next(
        p
        for p in row["projection"]["pieces"]
        if p["kind"] == "native_text" and p["end"] > p["start"]
    )
    scope = dict(
        source_view_ids=[case.view],
        source_views=[
            dict(
                source_view_id=case.view,
                key=row["key"],
                base_document=base.values(),
                section_pointer=row["section_pointer"],
                membership=row["membership"],
                projection_digest=row["projection_digest"],
                recipe_digest=row["recipe_digest"],
            )
        ],
        selectors=[
            dict(projection=row["projection_digest"], start=piece["start"], end=piece["end"])
        ],
        profile="assessment-control",
    )
    with case.writer.begin() as conn:
        task_info = (
            conn.execute(
                text(
                    "SELECT t.*,r.runtime_id FROM ops.task t "
                    "JOIN ops.run r ON r.id=t.run_id WHERE t.id=:id"
                ),
                {"id": case.source_task},
            )
            .mappings()
            .one()
        )
        source = SimpleNamespace(
            base=base, prepared=case.prepared, task=dict(task_info), scope=scope
        )
        producing_task, claim, config = make_task(conn, source)
        extent = dict(
            projection=row["projection_digest"],
            source_view_id=case.view,
            native_pointer=piece["item_ref"],
            start=piece["start"],
            end=piece["end"],
            text=row["projection"]["text"][piece["start"] : piece["end"]],
            synthetic=False,
        )
        occurrence = dict(local_id=occurrence_id(base, [extent]), extents=[extent])
        coverage = [
            dict(
                family="syntax",
                operation="native-binding",
                eligible=scope["selectors"],
                examined=scope["selectors"],
                availability="available",
                outcome="complete",
                profile="assessment-control",
            )
        ]
        wire = dict(
            format="characterization-layer-v1",
            base_document=base.values(),
            release_id=case.prepared.release_id,
            operation=dict(
                key="native-binding",
                version="1",
                runtime=task_info["runtime_id"],
                model="native-retained",
                grammar="no-grammar",
                configuration=config,
                input="fixture-input",
                context="exact-source",
                produced_families=["syntax"],
                outcomes=["complete", "partial", "failed"],
                result_determinants=["retained-source"],
            ),
            source_scope=scope,
            outcome="complete",
            occurrences=[occurrence],
            annotations=[
                dict(
                    local_id="native-reading",
                    kind="native",
                    vocabulary="independent-source",
                    family="syntax",
                    occurrences=[occurrence["local_id"]],
                    status="native_evidence",
                )
            ],
            memberships=[],
            roles=[],
            terms=[],
            choices=[],
            coverage=coverage,
        )
        text_ = extent["text"]
        assert text_ == "12"  # Independent controlled source cell, not producer-authored gold.
        configuration = '[nlp]\nlang = "en"'
        wire["operation"]["produced_families"].extend(["spacy.tokens", "spacy.sentences"])
        for family in ("spacy.tokens", "spacy.sentences"):
            coverage.append(dict(coverage[0], family=family))
        wire["native_runs"] = [
            dict(
                local_id="spacy",
                provider="spacy",
                profile="controlled-retained-columns",
                model="no-inference",
                model_version="1",
                runtime_version="3.8.18",
                configuration=configuration,
                configuration_codec="spacy-config-v1",
                configuration_digest=sha256(configuration.encode()).hexdigest(),
                layout_recipe="controlled-original-source",
                layout_digest=scope["source_views"][0]["recipe_digest"],
                text_digest=sha256(text_.encode()).hexdigest(),
                components=[],
                availability=[],
                runtime_packages=[],
                artifacts=[],
                limits=[],
            )
        ]
        for identity, kind, family in (
            ("spacy-block", "native.block", "spacy.tokens"),
            ("spacy-sentence", "native.sentence", "spacy.sentences"),
            ("spacy-token", "native.token", "spacy.tokens"),
        ):
            annotation: dict[str, Any] = dict(
                local_id=identity,
                kind=kind,
                vocabulary="native",
                family=family,
                occurrences=[occurrence["local_id"]],
                status="native_evidence",
            )
            if kind == "native.token":
                annotation["native_token"] = dict(
                    index=0,
                    container="spacy-block",
                    native_run="spacy",
                    sentence="spacy-sentence",
                    text=text_,
                    space=False,
                    whitespace="",
                    source_role="prose",
                )
            wire["annotations"].append(annotation)
        layer = validate_layer(case.prepared, wire)
        layer_pin = publish_layer(
            conn,
            task_id=producing_task,
            attempt=claim.attempt,
            holder="characterization-fixture",
            layer=layer,
        )
        composing_task, compose_claim, _ = make_task(
            conn, source, compose=True, layers=(layer_pin,)
        )
        view = validate_view(
            case.prepared,
            dict(
                format="enriched-document-view-v1",
                base_document=base.values(),
                release_id=case.prepared.release_id,
                source_scope=scope,
                layers=[layer_pin.values()],
                active_layers=[layer_pin.values()],
                profile="selected_layers",
                coverage=coverage,
            ),
            {layer_pin: layer},
        )
        view_pin = compose_view(
            conn,
            task_id=composing_task,
            attempt=compose_claim.attempt,
            holder="characterization-fixture",
            view=view,
        )
    with semantic_evaluator_engine.begin() as conn:
        created, unit, frame, payload = freeze(conn, case, frame_version=3, label="v3-actual-grade")
        assert isinstance(frame, OperationEvaluationFrameV3)
        independent = OperationCase(
            case_id="native-occurrence",
            facet="value",
            anchor_ids=(),
            inspected_scope="first independently selected native source piece",
            source_state="stated",
            judgment="supported",
            alternatives=({"value": {"kind": "native", "status": "native_evidence"}},),
            explanation=(
                "The controlled native text has one retained native reading "
                "at this exact occurrence."
            ),
            assessor_provenance={"actor": "independent-source-control"},
            opportunity_id="cell-value",
            required_family="syntax",
            candidate_selector={"collection": "annotations", "value": {"family": "syntax"}},
        )
        native = OperationCase(
            case_id="native-sentence-structure",
            facet="value",
            anchor_ids=(),
            inspected_scope="independently selected native cell as one sentence",
            source_state="stated",
            judgment="supported",
            alternatives=(),
            explanation=(
                "The controlled two-character source has exactly one complete sentence boundary."
            ),
            assessor_provenance={"actor": "independent-source-control"},
            opportunity_id="cell-value",
            required_family="spacy.sentences",
            native_reference=dict(
                version="spacy-native-reference-v1",
                kind="spans",
                scheme="spacy",
                text="12",
                words=["12"],
                spaces=[False],
                span_key="sents",
                spans=[dict(start=0, end=2)],
                labeled=False,
            ),
        )
        payload["cases"] = [asdict(independent), asdict(native)]
        submit_abc(conn, unit, frame, payload, actor="native-v3-source")
        frozen_frame = conn.scalar(
            text("SELECT context->0 FROM eval.reference_unit WHERE id=:id"), {"id": unit}
        )
        invalid = json.loads(json.dumps(payload))
        invalid["adjudication_passes"] = []
        invalid["cases"][1]["native_reference"]["scheme"] = "UD"
        with pytest.raises(DBAPIError, match="invalid closed native scoring"), conn.begin_nested():
            conn.execute(
                text(
                    "SELECT eval.record_operation_reference_pass("
                    ":unit,'A','native-forged-author',:authored,CAST(:frame AS jsonb))"
                ),
                dict(
                    unit=unit, authored=json.dumps(invalid).encode(), frame=json.dumps(frozen_frame)
                ),
            )

        null_state = json.loads(json.dumps(payload))
        null_state["adjudication_passes"] = []
        null_state["cases"][1]["native_reference"]["spans"][0]["state"] = None
        with (
            pytest.raises(DBAPIError, match="invalid source coordinates or label"),
            conn.begin_nested(),
        ):
            conn.execute(
                text(
                    "SELECT eval.record_operation_reference_pass("
                    ":unit,'A','null-span-state',:authored,CAST(:frame AS jsonb))"
                ),
                dict(
                    unit=unit,
                    authored=json.dumps(null_state).encode(),
                    frame=json.dumps(frozen_frame),
                ),
            )

        output_frame = replace(
            frame,
            direction="output_first",
            characterization_view=view_pin.values(),
            selected_layers=(layer_pin.values(),),
            outputs=(),
        )
        sampling = dict(created["sampling"])
        for key in (
            "operation_protocol",
            "source_frame_abi",
            "source_cut_id",
            "guideline_text",
            "guideline_digest",
        ):
            sampling.pop(key, None)
        empty = create_reference_set(
            conn,
            project_id="private-records",
            source_run_id=case.run,
            source_cut_id=case.cut,
            label="v3-empty-output",
            legacy_split="dev",
            guideline=frame.guideline_version,
            guideline_text="Judge only this explicitly frozen output population.",
            partition="development",
            sampling=sampling,
            frames={frame.unit: output_frame},
        )
        empty_unit = empty["units"][0]["unit_id"]
        empty_payload = dict(payload, direction="output_first", cases=[])
        submit_abc(conn, empty_unit, output_frame, empty_payload, actor="native-v3-output")
        token_ref = dict(layer=layer_pin.values(), collection="annotations", local_id="spacy-token")
        token_frame = replace(output_frame, outputs=(token_ref,))
        token_set = create_reference_set(
            conn,
            project_id="private-records",
            source_run_id=case.run,
            source_cut_id=case.cut,
            label="v3-unrelated-native-output",
            legacy_split="dev",
            guideline=frame.guideline_version,
            guideline_text="An existing token cannot authorize a whole-block native sentence task.",
            partition="development",
            sampling=sampling,
            frames={frame.unit: token_frame},
        )
        token_native = replace(native, output_reference=token_ref)
        token_payload = dict(payload, direction="output_first", cases=[asdict(token_native)])
        with pytest.raises(DBAPIError, match="exact frozen native block"), conn.begin_nested():
            record_pass(
                conn,
                unit_id=token_set["units"][0]["unit_id"],
                pass_kind="A",
                actor="unrelated-native-token",
                authored=json.dumps(token_payload).encode(),
                frame=token_frame,
            )
        forged = replace(
            output_frame,
            outputs=(
                {
                    "layer": layer_pin.values(),
                    "collection": "annotations",
                    "local_id": "absent-output",
                },
            ),
        )
        with pytest.raises(DBAPIError, match="output is absent"), conn.begin_nested():
            create_reference_set(
                conn,
                project_id="private-records",
                source_run_id=case.run,
                source_cut_id=case.cut,
                label="v3-forged-output",
                legacy_split="dev",
                guideline=frame.guideline_version,
                guideline_text="Refuse nonexistent frozen output.",
                partition="development",
                sampling=sampling,
                frames={frame.unit: forged},
            )
    with case.writer.begin() as conn:
        final = seal_cut(conn, case.run, "characterization-assessment-final", final=True)
    consolidate_cut(case.writer, final, "characterization-assessment-output")
    with semantic_evaluator_engine.begin() as conn:
        grade = reference_evaluate(
            conn,
            project_id="private-records",
            run_id=case.run,
            set_id=created["set_id"],
            characterization_view=view_pin.values(),
        )
        graded_cases = {value["case_id"]: value for value in grade.result["units"][0]["cases"]}
        assert graded_cases["native-occurrence"]["judgment"] == "supported"
        native_grade = graded_cases["native-sentence-structure"]
        assert native_grade["judgment"] == "supported"
        assert native_grade["native_metrics"]["status"] == "scored"
        assert native_grade["native_metrics"]["scores"]["sents_f"] == 1.0
        assert native_grade["native_metrics"]["coverage"]["reference"]["scored"] == 1
        displayed = inspect_evaluation(
            conn, project_id="private-records", evaluation_id=grade.id, view="cases"
        )
        assert displayed["items"][0]["item"]["case_id"] == "native-occurrence"
        assert displayed["items"][0]["item"]["matched_references"][0]["layer"] == layer_pin.values()
        empty_grade = reference_evaluate(
            conn, project_id="private-records", run_id=case.run, set_id=empty["set_id"]
        )
        assert empty_grade.result["units"][0]["output_coverage"]["selected_count"] == 0
        assert empty_grade.result["units"][0]["cases"] == []
        with pytest.raises(ReferenceError, match="selected project"):
            reference_evaluate(
                conn,
                project_id="other-project",
                run_id=case.run,
                set_id=created["set_id"],
                characterization_view=view_pin.values(),
            )

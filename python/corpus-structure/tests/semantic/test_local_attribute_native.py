"""Protected native custody of label-only attributes; controlled decoder, no quality claim."""

import json
from dataclasses import replace

import pytest
from sqlalchemy import select

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.methods.contribution_adapter import LOCAL_ADAPTER_VERSION, adapt_report
from corpus_structure.methods.gliner import GlinerPack, GlinerPreparation, GlinerReport
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.source_contexts import NativeSourceContext, SourceSlice
from semantic.native_record_fixtures import RecordSourceRecipe
from semantic.native_record_fixtures import complete_contributions as complete
from semantic.native_record_fixtures import private_source as private_source


@pytest.mark.parametrize(
    "private_source", [RecordSourceRecipe()], indirect=True, ids=("record-base",)
)
def test_label_only_attribute_score_and_version_survive_actual_native_custody(private_source):
    case = private_source
    with case.writer.connect() as conn:
        view = BoundReader(conn, case.run, case.prepared, analysis=False).source_view(case.view)
        source = replace(native_source_frame(view, ()), unit_ref="private-unit")
        start = source.text.index("12")
        context = NativeSourceContext(
            source,
            (),
            (SourceSlice(case.view, start, start + 2),),
            "independent controlled source12",
            "native-test",
            "exact source literal",
        )
    pack = GlinerPack.from_declaration(
        case.prepared.release_id,
        dict(
            entities=["quantity"],
            entity_attributes={"role": dict(labels=["reported_value"], applies_to=["quantity"])},
        ),
        version="native-local-v1",
    )
    raw = dict(
        entities=dict(
            quantity=[
                dict(
                    text="12",
                    start=0,
                    end=2,
                    confidence=0.9,
                    role=dict(label="reported_value", confidence=0.7),
                )
            ]
        )
    )
    report = GlinerReport(
        context.dependency_digest,
        context.dependency_digest,
        "controlled-decoder",
        "controlled-profile",
        pack.fingerprint,
        GlinerPreparation("12", "", 1, 2, 2),
        json.dumps(raw),
        "{}",
        0,
        False,
    )
    batch = adapt_report(report, context, pack=pack, item_key="native-attribute")
    result = UnitResult(
        ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
        outcome=ObservationOutcome.PRODUCED,
        contribution_operations=batch.operations,
        contributions=batch.contributions,
        contribution_coordinate_texts=batch.coordinate_texts,
    )
    with case.writer.begin() as conn:
        complete(case, conn, result)
        body = conn.scalar(
            select(table("ops.task_result").c.body).where(
                table("ops.task_result").c.task_id == case.task
            )
        )
        attribute = next(
            row for row in body["contributions"] if row["semantic_type"] == "attribute.role"
        )
        operation = next(
            row
            for row in body["contribution_operations"]
            if row["operation_key"] == attribute["operation_key"]
        )
        assert operation["operation_version"] == LOCAL_ADAPTER_VERSION
        assert attribute["value"] == dict(kind="text", text="reported_value")
        assert attribute["score_state"] == "native"
        assert attribute["score"] == dict(kind="float", hexadecimal=(0.7).hex())
        assert attribute["standing"] == "retained_private"
